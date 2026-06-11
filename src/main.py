import threading
import flet as ft
from controls.components import CardInfo, CardHardware, TabelaHardwares
from controls.log_control import LogElevatorControl, LogIntegrationControl

# Inicializa os serviços de log em background (sem bloquear)
monitor_elevators = LogElevatorControl()
monitor_integrations = LogIntegrationControl()

# monitor_elevators.iniciar()
# monitor_integrations.iniciar()


def main(page: ft.Page):
    page.window.width = 400
    page.window.height = 750
    page.theme_mode = ft.ThemeMode.DARK
    page.window.icon = "icon.png"

    page.on_close = lambda _: (monitor_elevators.parar(), monitor_integrations.parar())

    page.data = {}  # Limpando dados antigos não utilizados

    # --- Header ---
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

    # --- Estado de loading enquanto o banco não responde ---
    loading_indicator = ft.Container(
        visible=True,
        padding=ft.Padding.only(top=30, bottom=10),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.ProgressRing(color=ft.Colors.BLUE_300),
                ft.Text(
                    "Conectando ao banco de dados...",
                    size=12,
                    color=ft.Colors.GREY_400,
                )
            ]
        )
    )

    # --- Lista de hardwares (começa vazia) ---
    list_hardware = TabelaHardwares([])

    # --- Botões de ação ---
    bt_normalize_all = ft.IconButton(
        icon=ft.Icons.SETTINGS_BACKUP_RESTORE_OUTLINED,
        icon_color=ft.Colors.YELLOW_300,
        align=ft.Alignment.TOP_RIGHT,
        tooltip="Normalize as configurações em todos Faciais",
        on_click=list_hardware.set_confgs,
        disabled=True,
    )

    bt_update_rows = ft.IconButton(
        icon=ft.Icons.REFRESH_OUTLINED,
        icon_color=ft.Colors.BLUE_300,
        tooltip="Atualiza os status dos Hardwares",
        disabled=True,
    )

    bt_export_csv = ft.IconButton(
        icon=ft.Icons.DOWNLOAD_OUTLINED,
        icon_color=ft.Colors.GREEN_300,
        tooltip="Exportar itens visíveis para CSV",
        on_click=lambda e: list_hardware.export_hardwares_csv(),
        disabled=True,
    )

    card_info = CardInfo(
        valor_total=0,
        valor_online=0,
        valor_offline=0,
        actions=[
            bt_export_csv,
            bt_normalize_all,
            bt_update_rows,
        ]
    )

    # Vincula o card_info à tabela
    list_hardware.card_info = card_info

    # Agora que card_info existe, vincula o callback do bt_update_rows
    bt_update_rows.on_click = lambda e: list_hardware.update_status(card_info)

    subheader = ft.Row(
        controls=[card_info]
    )

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
                controls=[
                    header,
                    subheader,
                    sort_row,
                    search,
                    loading_indicator,
                    list_hardware,
                ]
            ),
            alignment=ft.Alignment.TOP_LEFT,
        ),
    )

    page.add(view_home)

    # --- Carga assíncrona dos dados do banco ---
    def _carregar_dados():
        """Conecta ao banco e popula a UI — roda em background para não bloquear a janela."""
        try:
            from controls.bancos import FalconDB, ThinkimDB

            falcon = FalconDB()
            thinkim = ThinkimDB()

            if falcon and falcon.is_connected:
                faciais_db = falcon._get_hardware(7)
                faciais_db = sorted(faciais_db, key=lambda x: x.Name)
                faciais_dict = [
                    {"Nome": f.Name, "IP": f.IP, "HardwareId": f.HardwareId}
                    for f in faciais_db
                ]
            else:
                faciais_db = []
                faciais_dict = []

            # Atualiza a UI na thread de background (Flet 0.82 aceita update() fora da main thread)
            cards = [
                CardHardware(f["Nome"], f["IP"], f.get("HardwareId"))
                for f in faciais_dict
            ]

            list_hardware.hardwares = cards
            list_hardware.controls = [
                list_hardware.empty_result,
                list_hardware.offline_result,
            ] + cards

            card_info.valor_total.value = f"Total: {len(faciais_db)}"

            # Habilita botões
            bt_normalize_all.disabled = False
            bt_update_rows.disabled = False
            bt_export_csv.disabled = False

        except Exception as ex:
            print(f"[INIT] Erro ao carregar dados do banco: {ex}")
        finally:
            # Esconde o loading independente de sucesso ou falha
            loading_indicator.visible = False
            try:
                page.update()
            except Exception:
                pass

    threading.Thread(target=_carregar_dados, daemon=True).start()


if __name__ == "__main__":
    ft.run(main=main, assets_dir="assets")

