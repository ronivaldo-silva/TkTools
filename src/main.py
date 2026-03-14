import flet as ft
from controls.components import CardInfo, CardHardware, TabelaHardwares
from controls.bancos import FalconDB, ThinkimDB 
from controls.log_control import LogElevatorControl, LogIntegrationControl

falcon = FalconDB()
thinkim = ThinkimDB()
# Coleta de faciais do Solid Falcon
if falcon.is_connected:
    faciais_db = falcon._get_hardware(7)
    # Ordenar por nome
    faciais_db.sort(key=lambda x: x["Name"])

    faciais_dict:list[dict] = [{"Nome":facial["Name"], "IP": facial["IP"]} for facial in faciais_db]
else:
    faciais_dict = []

# Inicializa os serviços de log em background
elevators_log_path = r"C:\Solid Falcon\Integrations\Elevators\Local\Logs\ElevatorsLog.txt"
integrations_log_path = r"C:\Solid Falcon\Local\Logs\IntegrationsLog.txt"

monitor_elevators = LogElevatorControl(elevators_log_path)
monitor_integrations = LogIntegrationControl(integrations_log_path)

monitor_elevators.iniciar()
monitor_integrations.iniciar()

def main(page: ft.Page):
    page.window.width = 400
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK
    
    page.on_close = lambda _: (monitor_elevators.parar(), monitor_integrations.parar())

    page.data = {} # Limpando dados antigos não utilizados

    header_text = ft.Container(
        content=ft.Text("Hardware Dashboard", size=16, weight=ft.FontWeight.BOLD),
        alignment=ft.Alignment.TOP_LEFT,
        padding=ft.Padding.only(left=10, top=10)
    )

    header_logo = ft.Container(
        width=40,
        content=ft.Image(src="rc_icon.jpg", 
            width=30,
            height=30,
            border_radius=ft.BorderRadius.all(15),
        ),
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

    bt_normalize_all = ft.IconButton(
        icon=ft.Icons.SETTINGS_BACKUP_RESTORE_OUTLINED,
        icon_color=ft.Colors.YELLOW_300,
        align=ft.Alignment.TOP_RIGHT,
        tooltip="Normalize as configurações em todos Faciais",
        on_click=lambda e: print(type(e.control.parent))
    )

    bt_update_rows = ft.IconButton(
        icon=ft.Icons.REFRESH_OUTLINED,
        icon_color=ft.Colors.BLUE_300,
        tooltip="Atualiza os status dos Hardwares",
        on_click=lambda e: list_hardware.update_status(card_info)
    )

    card_info = CardInfo(
        valor_total=len(faciais_db), 
        valor_online=0, 
        valor_offline=0,
        actions=[
            bt_normalize_all,
            bt_update_rows,
        ]
    )

    subheader = ft.Row(
        controls=[
            card_info,
        ]
    )

    # Vincula o card_info a tabela para que as atualizações automáticas funcionem
    list_hardware.card_info = card_info

    bt_sort_pessoas = ft.Button(
        content=ft.Text("Sort by Pessoas"),
        on_click=lambda e: list_hardware.sort_by_pessoas()
    )

    bt_sort_nome = ft.Button(
        content=ft.Text("Sort by Nome"),
        on_click=lambda e: list_hardware.sort_by_nome()
    )

    sort_row = ft.Row(
        controls=[
            bt_sort_pessoas, 
            bt_sort_nome,
        ]
    )

    search = ft.TextField(
        label="Search",
        width=300,
        height=40,
        text_size=12,
        on_change=lambda e: list_hardware.filter_search(e.control.value)
    )

    view_home = ft.SafeArea(
            expand=True,
            content=ft.Container(
                content=ft.Column(
                    controls=[header, subheader, sort_row, search, list_hardware]
                ),
                alignment=ft.Alignment.TOP_LEFT,
            ),
        )

    page.add(view_home)

if __name__ == "__main__":
    ft.run(main=main, assets_dir="assets")
