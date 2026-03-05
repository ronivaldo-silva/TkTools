import flet as ft
from controls.components import CardInfo, CardHardware, TabelaHardwares
from controls.bancos import FalconDB

falcon = FalconDB()
# Coleta de faciais do Solid Falcon
faciais_db = falcon._get_hardware(7)
# Ordenar por nome
faciais_db.sort(key=lambda x: x["Name"])

faciais_dict:list[dict] = [{"Nome":facial["Name"], "IP": facial["IP"]} for facial in faciais_db]

def main(page: ft.Page):
    page.window.width = 400
    page.window.height = 750

    page.data = {
        "online": 0,
        "offline": 0
    }

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


    list_hardware = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        controls=[ CardHardware(facial["Nome"], facial["IP"], pessoas=0) for facial in faciais_dict]
    )

    list_hardware = TabelaHardwares([ CardHardware(facial["Nome"], facial["IP"], pessoas=0) for facial in faciais_dict])

    card_info = CardInfo(valor_total=len(faciais_db), valor_online=page.data["online"], valor_offline=page.data["offline"])

    bt_sort_pessoas = ft.Button(
        content=ft.Text("Sort by Pessoas"),
        on_click=lambda e: list_hardware.sort_by_pessoas()
    )

    bt_sort_nome = ft.Button(
        content=ft.Text("Sort by Nome"),
        on_click=lambda e: list_hardware.sort_by_nome()
    )

    bt_sort_row = ft.Row(
        controls=[bt_sort_pessoas, bt_sort_nome]
    )

    search = ft.TextField(
        label="Search",
        on_change=lambda e: list_hardware.filter_search(e.control.value)
    )

    view_home = ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=ft.Column(
                    controls=[header, card_info, bt_sort_row, search, list_hardware]
                ),
                alignment=ft.Alignment.TOP_LEFT,
            ),
        )

    page.add(view_home)

if __name__ == "__main__":
    ft.run(main=main)
