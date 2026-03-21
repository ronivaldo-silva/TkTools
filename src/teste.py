import flet as ft

# Rows, Columns = Layouts
# Containers = Área e Preenchimento
# Controles = Elementos como Text, Icons, Buttons, etc


def main(page:ft.Page):
    page.window.width = 402
    page.title = 'meu teste'

    # Variaveis
    nome = "TK-Facial-Portaria"
    ip = "192.168.1.20"
    mac = "00:00:00:00:00"
    firmware = "V3.2.1 21031"
    modelo = "DS-HK-671"

    total_users = 3200
    total_faces = 3180
    users_comparition = 0.82

    # Controles / Elementos
    card_title = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        margin=ft.Margin.only(left=10, right=10),
        controls=[
            ft.Row(controls=[
                ft.Icon(ft.Icons.COMPUTER_OUTLINED, color=ft.Colors.BLUE_200, size=10),
                ft.Text(f"{nome}", size=10, color=ft.Colors.BLUE_200, weight=ft.FontWeight.BOLD, selectable=True),
            ]),
            ft.Text(f"{ip}", size=10, color=ft.Colors.BLUE_300, selectable=True),
        ],
    )

    info_device = ft.Column(
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text(f"● {mac}", size=10, color=ft.Colors.BLUE_200, weight=ft.FontWeight.BOLD, selectable=True),
            ft.Text(f"● {firmware}", size=10, color=ft.Colors.BLUE_300, selectable=True),
            ft.Text(f"● {modelo}", size=10, color=ft.Colors.BLUE_300, selectable=True),
        ],
    )

    info_users = ft.Column(
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Text(f"● {total_users}", size=10, color=ft.Colors.ORANGE_300, weight=ft.FontWeight.BOLD, selectable=True),
            ft.Text(f"● {total_faces}", size=10, color=ft.Colors.ORANGE_300, weight=ft.FontWeight.BOLD, selectable=True),
            ft.Text(f"● {users_comparition:.1%}", size=10, color=ft.Colors.ORANGE_300, weight=ft.FontWeight.BOLD, selectable=True),
        ],
    )

    # Layouts
    line_top = ft.Container(
        height=30,
        bgcolor=ft.Colors.BLACK_26,
        content=card_title
    )

    info_row = ft.Row(
        alignment=ft.MainAxisAlignment.START,
        spacing=30,
        margin=ft.Margin.only(left=10, right=10),
        controls=[
            info_device,
            info_users
        ],
    )

    line_mid = ft.Container(
        expand=True,
        bgcolor=ft.Colors.BLACK_26,
        content=info_row,
    )

    line_bot = ft.Row(
        height=35,
        alignment=ft.MainAxisAlignment.END,
        spacing=0,
        controls=[
            ft.IconButton(ft.Icons.ACCESS_TIME_OUTLINED, icon_size=16, icon_color=ft.Colors.BLUE_300),
            ft.IconButton(ft.Icons.RESTORE_OUTLINED, icon_size=16, icon_color=ft.Colors.ORANGE_300),
            ft.IconButton(ft.Icons.POWER_OFF_OUTLINED, icon_size=16, icon_color=ft.Colors.RED_300),
        ]
    )

    card_corpo = ft.Column(
        expand=True,
        spacing=0,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            line_top,
            ft.Divider(color=ft.Colors.BLUE_300, height=1, opacity=0.2),
            line_mid,
            line_bot
        ]
    )

    led_left = ft.Container(
        width=15,
        bgcolor=ft.Colors.RED_300,
        alignment=ft.Alignment.CENTER_LEFT,

    )

    card_layout = ft.Row(
        expand=True,
        spacing=0,
        alignment=ft.MainAxisAlignment.START,
        controls=[led_left, card_corpo]
    )

    # Finalização
    card = ft.Card(
        align=ft.Alignment.CENTER_LEFT,
        width=380,
        height=130,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS_WITH_SAVE_LAYER,
        show_border_on_foreground=True,
        shadow_color=ft.Colors.BLACK,
        elevation=5,
        content=card_layout
    )

    page.add(card)


ft.run(main=main)