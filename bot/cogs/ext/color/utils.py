import io

from imagetext_py import Canvas, Color, FontDB, Paint, draw_text

from bot.config import CustomRoleConfig


def generate_image_color_list(
    roles: list[tuple[str, tuple[int, int, int]]],
) -> io.BytesIO:
    """
    Generate an image to show the available list of custom roles.
    `roles` is (name, rgb) in list-number order: row N is custom role number N.
    There are certain rows per column. Each column has 300px wide.
    """

    FontDB.LoadFromPath("Noto", CustomRoleConfig.FONT_NOTO)
    FontDB.LoadFromPath("Noto-jp", CustomRoleConfig.FONT_NOTO_JP)
    FontDB.LoadFromPath("Noto-cn", CustomRoleConfig.FONT_NOTO_CN)
    font = FontDB.Query("Noto Noto-jp Noto-cn")

    total_data = len(roles)
    column_px = 300
    if total_data <= 15 * 1:
        boundary = 5  # max item per column
        row_px = 200
    elif total_data <= 15 * 2:
        boundary = 10
        row_px = 400
    elif total_data <= 15 * 3:
        boundary = 15
        row_px = 600
    elif total_data <= 15 * 4:
        boundary = 20
        row_px = 800
    else:
        boundary = 25
        row_px = 1000

    background_color = Color(
        0, 0, 0, 0
    )  # RGBA format with alpha set to 0 for transparency
    column_need = max(total_data // boundary + (1 if total_data % boundary else 0), 1)
    width, height = column_px * column_need, row_px
    canvas = Canvas(width, height, background_color)

    number = 1
    max_role_len = 15
    for col in range(column_need):
        x_now = (col * column_px) + 10
        y_now = 1
        for role_name, rgb in roles[col * boundary : (col + 1) * boundary]:
            name = (
                role_name[:15] + "..." if len(role_name) > max_role_len else role_name
            )
            text = f"{number}. {name}"
            fill_color = Paint.Color(Color(*rgb))

            draw_text(
                canvas=canvas,
                text=text,
                x=x_now,
                y=y_now,
                size=CustomRoleConfig.FONT_SIZE,
                font=font,
                draw_emojis=True,
                fill=fill_color,
            )

            y_now += CustomRoleConfig.FONT_SIZE + 10
            number += 1

    image_bytes = io.BytesIO()
    image = canvas.to_image()
    image.save(image_bytes, format="PNG")

    return image_bytes
