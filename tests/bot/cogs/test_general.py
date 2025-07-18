import unittest  # noqa: INP001
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from bot.cogs.general import General


class GeneralTests(unittest.IsolatedAsyncioTestCase):
    async def test_ping(self) -> None:
        mock_latency = PropertyMock(return_value=100)

        mock_warnet_bot = MagicMock()
        mock_warnet_bot.latency = mock_latency

        mock_context = AsyncMock()

        cmd = General(mock_warnet_bot)
        await cmd.ping(mock_warnet_bot, mock_context)

        mock_context.send.assert_called_once()

    async def test_nobar(self) -> None:
        mock_warnet_bot = MagicMock()

        mock_role = MagicMock()
        mock_role.name = "MOCK_ROLE_NAME"

        mock_guild = MagicMock()
        mock_guild.name = "MOCK_GUILD_NAME"
        mock_guild.get_role.return_value = mock_role

        mock_channel = AsyncMock()

        mock_context = AsyncMock()
        mock_context.guild = mock_guild
        mock_context.channel = mock_channel

        cmd = General(mock_warnet_bot)
        await cmd.nobar(mock_warnet_bot, mock_context)

        mock_guild.get_role.assert_called_once_with(1093508844551942144)
        mock_channel.send.assert_called_once_with(
            "Tata cara menjadi **HOST NOBAR** di server MOCK_GUILD_NAME:\n"
            "1. Silahkan ajukan tiket **Kontak Admin dan Mod** di <#1066618888462278657>.\n"
            "2. Tentukan **Judul Film**, **Tanggal**, dan **Jam** nobar. Minimal __satu hari sebelum nobar__, agar dapat diumumkan kepada role **MOCK_ROLE_NAME** terlebih dahulu.\n"
            "3. Pada saat waktu nobar, Admin/Mod akan memberikan kamu akses agar dapat stream pada channel <#1092630886127783957>."
        )
