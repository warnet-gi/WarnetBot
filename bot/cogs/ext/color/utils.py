"""Render the /warnet-color list as one PNG: numbered rows, name in its role color or gradient.

Runs off the event loop (cog awaits it via asyncio.to_thread) since emoji
lookups hit the network on a cache miss.
"""

import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont
from pilmoji.helpers import NodeType, to_nodes
from pilmoji.source import TwemojiEmojiSource

from bot.config import CustomRoleConfig

logger = logging.getLogger(__name__)

_LATIN_FONT = Path(CustomRoleConfig.FONT_NOTO)
_JP_FONT = Path(CustomRoleConfig.FONT_NOTO_JP)
_TC_FONT = Path(CustomRoleConfig.FONT_NOTO_CN)
# Tried in order when the block's font lacks a glyph (e.g. JP-only kana/kanji missing from TC).
_FALLBACK_FONTS = (_LATIN_FONT, _TC_FONT, _JP_FONT)
_NOTDEF_PROBE = chr(
    0x10FFFD
)  # private-use codepoint no font maps: renders the font's .notdef box

_FONT_SIZE = CustomRoleConfig.FONT_SIZE
_LINE_HEIGHT = _FONT_SIZE + 12

_BG_COLOR = (0, 0, 0, 0)  # transparent: a role color can never collide with the canvas
_NUMBER_COLOR = (148, 155, 164, 255)
_COLUMNS = 2
_PADDING = 28
_ROW_HEIGHT = _FONT_SIZE + 14
_COLUMN_GAP = 48
_MIN_COLUMN_WIDTH = 240
_NAME_MAX_LEN = 20
_NAME_TRUNCATE_AT = 17
_EMOJI_TIMEOUT = 5
_KANA = range(0x3040, 0x3100)
_HAN = (range(0x4E00, 0xA000), range(0x3400, 0x4DC0), range(0xF900, 0xFB00))


class _TimeoutTwemoji(TwemojiEmojiSource):
    """pilmoji's urllib fallback has no timeout; a stalled CDN would pin a worker thread forever."""

    def request(self, url: str) -> bytes:
        with urlopen(Request(url), timeout=_EMOJI_TIMEOUT) as response:  # noqa: S310
            return response.read()


_emoji_source = _TimeoutTwemoji()
_emoji_image_cache: dict[str, Image.Image | None] = {}


class RoleRow(NamedTuple):
    number: int
    name: str
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int] | None


class _Segment(NamedTuple):
    """One contiguous run drawn with a single font, or a single emoji glyph."""

    text: str
    font_path: Path | None  # None means "emoji": draw via _emoji_image()


class _Laid(NamedTuple):
    """A row measured once: prefix width, name segments with their x offsets, total name width."""

    row: RoleRow
    prefix: str
    prefix_width: float
    segments: list[_Segment]
    offsets: list[float]
    name_width: float


@lru_cache(maxsize=16)
def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


@lru_cache(maxsize=16)
def _notdef_mask(path: Path) -> bytes:
    return bytes(_font(path, _FONT_SIZE).getmask(_NOTDEF_PROBE))  # pyright: ignore[reportArgumentType]


@lru_cache(maxsize=4096)
def _has_glyph(path: Path, ch: str) -> bool:
    """Pillow exposes no cmap lookup; a missing glyph renders exactly like the font's .notdef box."""
    return bytes(_font(path, _FONT_SIZE).getmask(ch)) != _notdef_mask(path)  # pyright: ignore[reportArgumentType]


def _block_font_for(ch: str) -> Path:
    """Pick the narrowest font whose Unicode block covers ch (emoji is handled upstream, by to_nodes)."""
    cp = ord(ch)
    if cp in _KANA:
        return _JP_FONT
    if any(cp in block for block in _HAN):
        return _TC_FONT
    return _LATIN_FONT


def _font_path_for(ch: str) -> Path:
    """Block-preferred font if it has the glyph, else the first fallback that does (else tofu in the preferred)."""
    preferred = _block_font_for(ch)
    if _has_glyph(preferred, ch):
        return preferred
    return next((path for path in _FALLBACK_FONTS if _has_glyph(path, ch)), preferred)


def _split_text_runs(text: str) -> list[_Segment]:
    """Group consecutive characters sharing a font."""
    runs: list[_Segment] = []
    for ch in text:
        path = _font_path_for(ch)
        if runs and runs[-1].font_path == path:
            runs[-1] = _Segment(runs[-1].text + ch, path)
        else:
            runs.append(_Segment(ch, path))
    return runs


def _truncate(name: str) -> str:
    """Cap displayed name length so one long role name can't stretch a column."""
    if len(name) <= _NAME_MAX_LEN:
        return name
    return name[:_NAME_TRUNCATE_AT] + "..."


def _segments_for(name: str) -> list[_Segment]:
    """Split a role name into font runs and emoji glyphs, in display order."""
    segments: list[_Segment] = []
    for line in to_nodes(_truncate(name)):
        for node in line:
            if node.type is NodeType.text:
                segments.extend(_split_text_runs(node.content))
            else:
                # emoji or discord_emoji: draw each grapheme as its own glyph
                segments.append(_Segment(node.content, None))
    return segments


def _emoji_image(emoji: str) -> Image.Image | None:
    """Fetch (and cache) the Twemoji PNG for one emoji grapheme, scaled to the text line height.

    Network failures return None (glyph skipped) and are not cached, so a later render can retry.
    """
    if emoji in _emoji_image_cache:
        return _emoji_image_cache[emoji]
    try:
        stream = _emoji_source.get_emoji(emoji)
        image = None
        if stream is not None:
            image = (
                Image.open(stream)
                .convert("RGBA")
                .resize((_FONT_SIZE, _FONT_SIZE), Image.Resampling.LANCZOS)
            )
    except OSError:
        # urllib errors and Pillow decode errors are OSError; one bad emoji must not fail the whole list
        logger.warning("Emoji fetch failed", extra={"emoji": emoji}, exc_info=True)
        return None
    _emoji_image_cache[emoji] = image
    return image


def _segment_width(draw: ImageDraw.ImageDraw, segment: _Segment) -> float:
    if segment.font_path is None:
        image = _emoji_image(segment.text)
        return float(image.width) if image is not None else 0.0
    return draw.textlength(segment.text, font=_font(segment.font_path, _FONT_SIZE))


def _layout(draw: ImageDraw.ImageDraw, row: RoleRow) -> _Laid:
    prefix = f"{row.number}. "
    segments = _segments_for(row.name)
    offsets: list[float] = []
    cursor = 0.0
    for segment in segments:
        offsets.append(cursor)
        cursor += _segment_width(draw, segment)
    prefix_width = draw.textlength(prefix, font=_font(_LATIN_FONT, _FONT_SIZE))
    return _Laid(row, prefix, prefix_width, segments, offsets, cursor)


def _draw_gradient_name(
    canvas: Image.Image,
    x: int,
    y: int,
    laid: _Laid,
    secondary: tuple[int, int, int],
) -> None:
    """Paste a left-to-right primary->secondary gradient through a mask of the name's glyphs."""
    width = max(round(laid.name_width) + 2, 1)
    mask = Image.new("L", (width, _LINE_HEIGHT), 0)
    mask_draw = ImageDraw.Draw(mask)
    for offset, segment in zip(laid.offsets, laid.segments, strict=True):
        if segment.font_path is not None:
            mask_draw.text(
                (offset, 0),
                segment.text,
                font=_font(segment.font_path, _FONT_SIZE),
                fill=255,
            )
    primary = laid.row.primary
    gradient = Image.new("RGB", (width, 1))
    for px in range(width):
        t = px / max(width - 1, 1)
        gradient.putpixel(
            (px, 0),
            tuple(
                round(primary[i] + (secondary[i] - primary[i]) * t) for i in range(3)
            ),
        )
    canvas.paste(gradient.resize((width, _LINE_HEIGHT)), (x, y), mask)


def _draw_row(
    canvas: Image.Image, draw: ImageDraw.ImageDraw, x: float, y: int, laid: _Laid
) -> None:
    color = (*laid.row.primary, 255)
    draw.text((x, y), laid.prefix, font=_font(_LATIN_FONT, _FONT_SIZE), fill=color)
    name_x = x + laid.prefix_width

    if laid.row.secondary is not None:
        _draw_gradient_name(canvas, round(name_x), y, laid, laid.row.secondary)
    else:
        for offset, segment in zip(laid.offsets, laid.segments, strict=True):
            if segment.font_path is not None:
                draw.text(
                    (name_x + offset, y),
                    segment.text,
                    font=_font(segment.font_path, _FONT_SIZE),
                    fill=color,
                )

    for offset, segment in zip(laid.offsets, laid.segments, strict=True):
        if segment.font_path is None:
            image = _emoji_image(segment.text)
            if image is not None:
                canvas.alpha_composite(
                    image, (round(name_x + offset), y + int(_FONT_SIZE * 0.1))
                )


def render_role_list(rows: list[RoleRow]) -> io.BytesIO:
    """Build the numbered role-list PNG; empty rows still render a placeholder canvas.

    Column width follows the widest row, so long or wide-glyph names never overlap the next column.
    """
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    laid_rows = [_layout(measure, row) for row in rows]
    per_column = max(1, -(-len(rows) // _COLUMNS))
    widest = max(
        (laid.prefix_width + laid.name_width for laid in laid_rows),
        default=_MIN_COLUMN_WIDTH,
    )
    column_width = max(round(widest) + 2, _MIN_COLUMN_WIDTH)

    width = _PADDING * 2 + column_width * _COLUMNS + _COLUMN_GAP * (_COLUMNS - 1)
    height = _PADDING * 2 + per_column * _ROW_HEIGHT
    canvas = Image.new("RGBA", (width, height), _BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    if not rows:
        draw.text(
            (_PADDING, _PADDING),
            "No custom roles yet.",
            font=_font(_LATIN_FONT, _FONT_SIZE),
            fill=_NUMBER_COLOR,
        )
    for index, laid in enumerate(laid_rows):
        column, line = divmod(index, per_column)
        x = _PADDING + column * (column_width + _COLUMN_GAP)
        _draw_row(canvas, draw, x, _PADDING + line * _ROW_HEIGHT, laid)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer
