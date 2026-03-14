import flet as ft
from controls.devices import Facial
from controls.bancos import FalconDB

import threading

class CardInfo(ft.Card):
    def __init__(self, valor_online, valor_offline, valor_total, actions:list[ft.Control] = None):
        super().__init__()
        self.alignment=ft.Alignment.TOP_LEFT
        self.padding=ft.Padding.only(left=10, top=10)
        self.valor_total = ft.Text(f"Total: {valor_total}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300)
        self.valor_online = ft.Text(f"ON: {valor_online}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300)
        self.valor_offline = ft.Text(f"OFF: {valor_offline}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_300)
        
        self.width = 365

        self.actions = ft.Container(
            expand=True,
            alignment=ft.Alignment.BOTTOM_RIGHT,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=actions
            )
        )

        self.dashboard = ft.Container(
            alignment=ft.Alignment.CENTER_LEFT,
            content=ft.Column(
                spacing=0,
                controls=[
                    self.valor_total,
                    ft.Row([self.valor_online, self.valor_offline])
                ]
            )
        )

        self.content = ft.Column(
                margin=ft.Margin.only(left=10, bottom=10, top=10),
                controls=[
                    ft.Row(controls=[self.dashboard, self.actions], expand=True),
                    ft.Divider(height=1, color=ft.Colors.BLUE_300),
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

        self.width = 365
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
            expand=3,
            content=self.layout
        )

    def did_mount(self):
        # Iniciar thread para carregar info apenas após o componente estar na página
        threading.Thread(target=self._load_async_data, daemon=True).start()

    def _load_async_data(self):
            
        self.facial.load_info()
        
        # Atualizar UI individual do card
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
            
            # Notificar o pai (TabelaHardwares) para atualizar as estatísticas globais
            if hasattr(self, "parent") and self.parent:
                if hasattr(self.parent, "refresh_stats"):
                    self.parent.refresh_stats()
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
        texto_copiar = str(getattr(self.facial, atributo))
        try:
            await ft.Clipboard().set(texto_copiar)
        except Exception as e:
            print(e)

class TabelaHardwares(ft.Column):
    def __init__(self, hardwares:list[CardHardware]):
        super().__init__()
        self.hardwares:list[CardHardware] = hardwares
        self.card_info = None # Referência que será ligada no main.py

        self.expand=True
        self.scroll=ft.ScrollMode.AUTO

        # Controle para exibir quando a busca for vazia
        self.empty_result = ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=50, color=ft.Colors.GREY_400),
                    ft.Text("Nenhum equipamento encontrado", color=ft.Colors.GREY_400)
                ]
            ),
            padding=50,
            visible=False
        )

        self.controls = [self.empty_result] + hardwares

        self.__reverse = True

    def refresh_stats(self):
        """ Recalcula ON/OFF via len() e atualiza o CardInfo se ligado """
        if self.card_info:
            online_count = len([h for h in self.hardwares if h.facial.online])
            offline_count = len([h for h in self.hardwares if not h.facial.online])
            
            self.card_info.valor_online.value = f"ON: {online_count}"
            self.card_info.valor_offline.value = f"OFF: {offline_count}"
            self.card_info.update()

    def update_status(self, card_info):
        """ Atualiza todos os hardwares e vincula o card_info """
        self.card_info = card_info
        
        for hardware in self.hardwares:
            # Reseta o ícone visual para "carregando"
            hardware.status_icon.icon = ft.Icons.DOWNLOADING_OUTLINED
            hardware.status_icon.color = ft.Colors.BLUE_300
            try: hardware.update()
            except: pass
            
            # Dispara a carga em nova thread
            threading.Thread(target=hardware._load_async_data, daemon=True).start()
    
    def sort_by(self, attr_return:str):
        """ Ordena a lista de hardwares por qualquer atributo do objeto facial """
        self.hardwares.sort(key=lambda x: getattr(x.facial, attr_return) if getattr(x.facial, attr_return) is not None else "", reverse=self.__reverse)
        self.controls = [self.empty_result] + self.hardwares
        self.__reverse = not self.__reverse
        self.update()

    def sort_by_nome(self):
        """ Ordena especificamente por nome_db """
        self.hardwares.sort(key=lambda x: x.facial.nome_db.lower() if x.facial.nome_db else "")
        self.controls = [self.empty_result] + self.hardwares
        self.update()

    def sort_by_pessoas(self):
        """ Ordena especificamente por quantidade de pessoas """
        self.hardwares.sort(key=lambda x: int(x.facial.pessoas) if x.facial.pessoas is not None else 0, reverse=self.__reverse)
        self.controls = [self.empty_result] + self.hardwares
        self.__reverse = not self.__reverse
        self.update()

    def filter_search(self, search_text):
        """Filtra os equipamentos por nome, mac e ip de forma otimizada"""
        search_text = search_text.lower().strip()
        
        # Se a busca estiver vazia, mostra todos e esconde o aviso de vazio
        if not search_text:
            self.empty_result.visible = False
            for h in self.hardwares:
                h.visible = True
            self.update()
            return

        algum_visivel = False
        for hardware in self.hardwares:
            # String de busca segura tratando Nones
            nome = (hardware.facial.nome_db or "").lower()
            ip = (hardware.facial.ip or "").lower()
            mac = (hardware.facial.mac_address or "").lower()
            
            # Verifica se o termo está em algum dos campos
            if search_text in nome or search_text in ip or search_text in mac:
                hardware.visible = True
                algum_visivel = True
            else:
                hardware.visible = False
        
        # Exibe aviso se nenhum resultado for encontrado
        self.empty_result.visible = not algum_visivel
        self.update()

    def export_hardwares_csv(self):
        pass
    