from unicodedata import name
import flet as ft
from controls.components import CardInfo, CardHardware
from controls.bancos import FalconDB

falcon = FalconDB()
# Coleta de faciais do Solid Falcon
faciais = falcon._get_hardware(7)
# Ordenar por nome
faciais.sort(key=lambda x: x["Name"])

faciais_dict:list[dict] = [{"Nome":facial["Name"], "IP": facial["IP"]} for facial in faciais]


def main(page: ft.Page):
    page.window.width = 400
    page.window.height = 750

    header_text = ft.Container(
        content=ft.Text("Hardware Dashboard", size=20, weight=ft.FontWeight.BOLD),
        alignment=ft.Alignment.TOP_LEFT,
        padding=ft.Padding.only(left=10, top=10)
    )

    header_logo = ft.Container(
        content=ft.Image(src="rc_icon.jpg", width=50, height=50),
        alignment=ft.Alignment.TOP_RIGHT,
        padding=ft.Padding.only(right=10, top=10)
    )

    header = ft.Row(
        controls=[header_logo, header_text]
    )

    card_info = CardInfo(valor_total=len(faciais), valor_online=0, valor_offline=0)

    list_hardware = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[ CardHardware(facial["Nome"], facial["IP"], pessoas=0) for facial in faciais_dict ]
    )

    view_home = ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=ft.Column(
                    controls=[header, card_info, list_hardware]
                ),
                alignment=ft.Alignment.TOP_LEFT,
            ),
        )

    page.add(view_home)

if __name__ == "__main__":
    ft.run(main=main)
