import flet as ft
from controls.devices import Facial
from controls.bancos import FalconDB

import threading

class CardInfo(ft.Container):
    def __init__(self, valor_online, valor_offline, valor_total):
        super().__init__()
        self.alignment=ft.Alignment.TOP_LEFT
        self.padding=ft.Padding.only(left=10, top=10)
        self.valor_total = ft.Text(f"Total: {valor_total}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300)
        self.valor_online = ft.Text(f"On: {valor_online}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300)
        self.valor_offline = ft.Text(f"Off: {valor_offline}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_300)
        
        self.content = ft.Column(
            controls=[
                self.valor_total,
                ft.Row(
                    controls=[self.valor_online, self.valor_offline]
                )
            ]
        )

class CardHardware(ft.Container):
    def __init__(self, nome, ip, pessoas:int = 0):
        super().__init__()
        
        self.facial = Facial(nome, ip)

        self.popup = ft.AlertDialog(
            title=ft.Text(f'Alerta !'),
            content=ft.Text(f'Deseja reiniciar {nome} ?'),
            actions=[
                ft.TextButton("Sim", on_click=lambda e: self._reboot_device(e) ),
                ft.TextButton("Não", on_click=lambda e: self.__close_popup(e, self.popup))
            ],
        )

        atributos:dict = {'Nome':'nome_db', 'IP':'ip', 'Modelo':'modelo', 'Firmware':'firmware', 'MAC':'mac_address'}
        self.popup_copy = ft.AlertDialog(
            title=ft.Text(f'Copie dados de {self.facial.nome_db}', size=14),
            actions=[
                ft.TextButton("Fechar", on_click=lambda e: self.__close_popup(e, self.popup_copy))
            ],
            content=ft.ResponsiveRow(
                controls=[
                    ft.Container(
                        content=ft.Button(atrr[0], on_click=self._copy_device, data=atrr[1]),
                        col=6
                    )
                for atrr in atributos.items()
                ]
            )

        )

        self.alignment=ft.Alignment.TOP_LEFT
        self.padding=ft.Padding.only(left=10, top=10)
        
        self.status_icon = ft.Icon(ft.Icons.DOWNLOADING_OUTLINED, ft.Colors.BLUE_300)
        
        self.titulo_text = ft.Text(nome)
        self.ip_text = ft.Text(f"● {ip}", color=ft.Colors.BLUE_300, size=10)
        self.firmware_text = ft.Text("● ", color=ft.Colors.BLUE_300, size=10)
        self.modelo_text = ft.Text("● ", color=ft.Colors.BLUE_300, size=10)
        self.mac_address_text = ft.Text("● ", color=ft.Colors.BLUE_300, size=10)
        
        self.titulo_col = ft.Column(
            spacing=0,
            width=150,
            controls=[
                self.titulo_text,
                self.ip_text,
                self.firmware_text,
                self.modelo_text,
                self.mac_address_text
            ]
        )

        self.titulo = ft.Container(
            content=self.titulo_col,
            on_click=lambda e: self.__show_popup(e, self.popup_copy)
        )

        self.pessoas_text = ft.Text(f" {pessoas}", color=ft.Colors.YELLOW_300)
        self.faces_text = ft.Text(f" - ", color=ft.Colors.YELLOW_300)

        self.pessoas_row = ft.Row(
            spacing=0,
            controls=[
                ft.Icon(ft.Icons.PEOPLE_OUTLINE, color=ft.Colors.YELLOW_300, size=16), 
                self.pessoas_text
            ]
        )

        self.faces_row = ft.Row(
            spacing=0,
            controls=[
                ft.Icon(ft.Icons.FACE_RETOUCHING_OFF_OUTLINED, color=ft.Colors.YELLOW_300, size=16), 
                self.faces_text
            ]
        )

        self.pessoas_card = ft.Column(
            spacing=0,
            controls=[
                self.pessoas_row,
                self.faces_row
            ]
        )

        self.bt_restart = ft.IconButton(
            icon=ft.Icons.POWER_OFF_OUTLINED, 
            icon_color=ft.Colors.RED_300,
            on_click=lambda e: self.__show_popup(e, self.popup)
        )

        self.layout = ft.Row(
            expand=True,
            margin=ft.Margin.all(5),
            controls=[
                self.status_icon,
                self.titulo,
                self.pessoas_card,
                ft.Container(expand=True, content=self.bt_restart, alignment=ft.Alignment.CENTER_RIGHT),
            ]
        )

        self.content = ft.Card(
            expand=True,
            content=self.layout
        )

    def did_mount(self):
        # Iniciar thread para carregar info apenas após o componente estar na página
        threading.Thread(target=self._load_async_data, daemon=True).start()

    def _load_async_data(self):
            
        self.facial.load_info()
        
        # Atualizar UI
        if self.facial.online:
            self.status_icon.icon = ft.Icons.ONLINE_PREDICTION_OUTLINED
            self.status_icon.color = ft.Colors.GREEN_300
        else:
            self.status_icon.icon = ft.Icons.OFFLINE_BOLT_OUTLINED
            self.status_icon.color = ft.Colors.RED_300
            
        self.pessoas_text.value = f" {self.facial.pessoas if self.facial.pessoas is not None else 0}"

        if self.facial.pessoas is not None and self.facial.faces is not None:
            self.faces_text.value = f" {int(self.facial.pessoas) - int(self.facial.faces)}"
        else:
            self.faces_text.value = " - "
        
        self.firmware_text.value = f"● {self.facial.firmware if self.facial.firmware is not None else ' - '}"
        self.modelo_text.value = f"● {self.facial.modelo if self.facial.modelo is not None else ' - '}"
        self.mac_address_text.value = f"● {self.facial.mac_address if self.facial.mac_address is not None else ' - '}"


        try:
            self.update()
        except Exception:
            pass

    def __show_popup(self, e:ft.ControlEvent, popup:ft.AlertDialog):
        e.control.page.show_dialog(popup)
        e.control.page.update()

    def __close_popup(self, e:ft.ControlEvent, popup:ft.AlertDialog):
        popup.open = False
        e.control.page.update()
    
    def _reboot_device(self, e:ft.ControlEvent):
        self.facial.reboot()
        self.__close_popup(e, self.popup)

    async def _copy_device(self, e:ft.ControlEvent):
        """ Copia os dados do equipamento para o clipboard e fecha o popup """
        atributo = e.control.data
        texto_copiar = getattr(self.facial, atributo)
        await ft.Clipboard().set(texto_copiar)

class TabelaHardwares(ft.Column):
    def __init__(self, hardwares:list[CardHardware]):
        super().__init__()
        self.hardwares = hardwares
        self.online = 0
        self.offline = 0

        self.expand=True
        self.scroll=ft.ScrollMode.AUTO

        self.controls = hardwares

        self.__reverse = True

    def update_status(self):
        self.online = 0
        self.offline = 0
        for hardware in self.hardwares:
            hardware._load_async_data()

            if hardware.facial.online:
                self.page.data.online += 1
            else:
                self.page.data.offline += 1
    
    def sort_by_nome(self):
        self.controls.sort(key=lambda x: x.facial.nome_db)
        self.update()

    def sort_by_pessoas(self):
        self.controls.sort(key=lambda x: x.facial.pessoas, reverse=self.__reverse)
        self.__reverse = not self.__reverse
        self.update()

    def filter_search(self, search_text):
        """Filtra o os equipamentos por nome, mac e ip"""
        self.controls = [hardware for hardware in self.hardwares if search_text.lower() in hardware.facial.nome_db.lower() or search_text.lower() in hardware.facial.mac_address.lower() or search_text.lower() in hardware.facial.ip.lower()]
        self.update()


    