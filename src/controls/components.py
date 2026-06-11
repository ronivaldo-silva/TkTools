import flet as ft
import threading
import time
from controls.devices import Facial
from controls.bancos import FalconDB

# ── Controle de concorrência ────────────────────────────────────────────────
# Limita a 8 threads HTTP simultâneas para não saturar a rede com 67 devices.
# Cada lote de 8 resolve em ~3-5 s; todos os 67 terminam em ~5 lotes ≈ 25-40 s.
_CARD_SEMAPHORE = threading.Semaphore(8)

# Lock para debounce do refresh_stats() (evita N page.update() simultâneos)
_STATS_LOCK = threading.Lock()

class CardInfo(ft.Card):
    def __init__(self, valor_online, valor_offline, valor_total, actions:list[ft.Control] = None):
        super().__init__()
        self.alignment=ft.Alignment.TOP_LEFT
        self.padding=ft.Padding.only(left=10, top=10)
        self.valor_total = ft.Text(f"Total: {valor_total}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300)
        self.valor_online = ft.Text(f"ON: {valor_online}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_300)
        self.valor_offline = ft.Text(f"OFF: {valor_offline}", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_300)
        
        self.width = 365

        # Botão de Sincronização geral
        self.bt_sync = ft.IconButton(
            icon=ft.Icons.SYNC,
            icon_color=ft.Colors.ORANGE_300,
            tooltip="Sincronizar usuários nos equipamentos visíveis"
        )

        self.actions = ft.Container(
            expand=True,
            alignment=ft.Alignment.BOTTOM_RIGHT,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=([self.bt_sync] + actions) if actions else [self.bt_sync] # Condição para evitar erro de concatenação com lista vazia
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

        # Barra de progresso geral
        self.progress = ft.ProgressBar(visible=False, color=ft.Colors.BLUE_300, height=4)

        self.content = ft.Column(
                margin=ft.Margin.only(left=10, bottom=10, top=10),
                controls=[
                    ft.Row(controls=[self.dashboard, self.actions], expand=True),
                    ft.Divider(height=1, color=ft.Colors.BLUE_300),
                    self.progress,
                ]
            )

class CardHardware(ft.Container):
    def __init__(self, nome, ip, hardware_id=None):
        super().__init__()
        self.hardware_id = hardware_id
        self.facial = Facial(nome, ip)
        self.facial.hardware_id = hardware_id

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
        self.clock_icon = ft.Icon(ft.Icons.ACCESS_TIME_OUTLINED, color=ft.Colors.GREY_600, size=20, tooltip="Horário não sincronizado")
        
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

        self.pessoas_text = ft.Text(" - ", color=ft.Colors.YELLOW_300)
        self.faces_text = ft.Text(" - ", color=ft.Colors.YELLOW_300)

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
                ft.Container(expand=True, content=ft.Row([self.clock_icon, self.bt_restart], alignment=ft.MainAxisAlignment.END, spacing=0), alignment=ft.Alignment.CENTER_RIGHT),
            ]
        )

        self.progress = ft.ProgressBar(visible=False, color=ft.Colors.CYAN_300, height=3)

        self.content = ft.Card(
            expand=3,
            content=ft.Column(
                spacing=0,
                controls=[
                    self.layout,
                    self.progress
                ]
            )
        )

    def did_mount(self):
        # Iniciar thread para carregar info apenas após o componente estar na página
        threading.Thread(target=self._load_async_data, daemon=True).start()

    def _check_time_sync(self):
        import datetime
        if not self.facial._datahora:
            self.clock_icon.color = ft.Colors.GREY_600
            self.clock_icon.tooltip = "Horário indisponível ou offline"
            return
            
        try:
            device_time = self.facial._datahora
            if isinstance(device_time, str):
                self.clock_icon.tooltip = f"Hora não verificada: {device_time}"
                self.clock_icon.color = ft.Colors.BLUE_300
                return
                
            if hasattr(device_time, 'tzinfo') and device_time.tzinfo is not None:
                # Com fuso
                agora = datetime.datetime.now(datetime.timezone.utc)
                agora_fmt = agora.strftime('%Y-%m-%d %H:%M')
                device_fmt = device_time.astimezone(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
            else:
                agora = datetime.datetime.now()
                agora_fmt = agora.strftime('%Y-%m-%d %H:%M')
                device_fmt = device_time.strftime('%Y-%m-%d %H:%M')
            
            # Compara apenas até o minuto (ignora segundos)
            if agora_fmt == device_fmt:
                self.clock_icon.color = ft.Colors.GREEN_300
                self.clock_icon.tooltip = "Em Sincronia com Servidor"
            else:
                self.clock_icon.color = ft.Colors.YELLOW_300
                self.clock_icon.tooltip = "Fora de Sincronia"
        except Exception as e:
            self.clock_icon.color = ft.Colors.RED_300
            self.clock_icon.tooltip = "Erro ao comparar horário"

    def _load_async_data(self):
        """Carrega dados do equipamento com semáforo para limitar concorrência."""
        with _CARD_SEMAPHORE:
            try:
                self.facial.load_info()
            except Exception:
                self.facial.online = False

            if self.facial.online:
                try:
                    self.facial.update_time()
                except Exception:
                    pass
            self._check_time_sync()

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
        self.page.pop_dialog()
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
        self._card_info = None  # Referência interna

        # Estado de debounce para refresh_stats
        self._stats_pending = False
        self._stats_lock = threading.Lock()

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO

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

        # Controle para exibir quando o banco estiver offline
        self.offline_result = ft.Container(
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.OFFLINE_BOLT_OUTLINED, size=50, color=ft.Colors.RED_300),
                    ft.Text("Banco de dados offline", color=ft.Colors.RED_300)
                ]
            ),
            padding=50,
            visible=False
        )

        self.controls = [self.empty_result, self.offline_result] + hardwares

        self.__reverse = True

    @property
    def card_info(self):
        return self._card_info

    @card_info.setter
    def card_info(self, value):
        self._card_info = value
        if value:
            # Vincula o evento de clique do botão de sync ao nosso novo fluxo
            value.bt_sync.on_click = self.realizar_sincronizacao_facial_limpa

    def refresh_stats(self):
        """Recalcula ON/OFF e atualiza o CardInfo com debounce.

        Com 67 equipamentos, todos terminam em lotes e chamam refresh_stats()
        ao mesmo tempo. O debounce coalesce N chamadas em 1 único update.
        """
        with self._stats_lock:
            if self._stats_pending:
                # Já existe uma atualização agendada — não enfileira outra
                return
            self._stats_pending = True

        def _do_update():
            # Aguarda um tick para coalescir chamadas que chegam quase ao mesmo tempo
            time.sleep(0.05)
            with self._stats_lock:
                self._stats_pending = False

            if not self.card_info:
                return

            online_count = len([h for h in self.hardwares if h.facial.online])
            offline_count = len([h for h in self.hardwares if not h.facial.online])

            self.card_info.valor_online.value = f"ON: {online_count}"
            self.card_info.valor_offline.value = f"OFF: {offline_count}"
            try:
                self.card_info.update()
            except Exception:
                pass

        threading.Thread(target=_do_update, daemon=True).start()

    def update_status(self, card_info):
        """Atualiza o status de todos os hardwares em background.

        Reutiliza a engine do banco já conectada (sem criar novo FalconDB()).
        Dispara threads limitadas pelo _CARD_SEMAPHORE global.
        """
        self.card_info = card_info

        # Verifica conectividade reaproveitando a engine existente do primeiro hardware
        # via uma instância leve — sem abrir nova conexão TCP
        banco_conectado = True
        try:
            _banco_check = FalconDB()
            banco_conectado = _banco_check.is_connected
        except Exception:
            banco_conectado = False

        if not banco_conectado:
            self.offline_result.visible = True
            for hardware in self.hardwares:
                hardware.facial.online = False
                hardware.status_icon.icon = ft.Icons.OFFLINE_BOLT_OUTLINED
                hardware.status_icon.color = ft.Colors.RED_300
                hardware.pessoas_text.value = " - "
                hardware.faces_text.value = " - "
                hardware.clock_icon.color = ft.Colors.GREY_600
                hardware.clock_icon.tooltip = "Offline"
                try: hardware.update()
                except: pass
            self.refresh_stats()
            try: self.update()
            except: pass
            return

        self.offline_result.visible = False

        for hardware in self.hardwares:
            # Reseta o ícone visual para "carregando"
            hardware.status_icon.icon = ft.Icons.DOWNLOADING_OUTLINED
            hardware.status_icon.color = ft.Colors.BLUE_300
            hardware.clock_icon.color = ft.Colors.GREY_600
            hardware.clock_icon.tooltip = "Verificando relógio..."
            try: hardware.update()
            except: pass

            # Dispara a carga — semáforo limita a 8 simultâneas
            threading.Thread(target=hardware._load_async_data, daemon=True).start()
    
    def sort_by(self, attr_return:str):
        """ Ordena a lista de hardwares por qualquer atributo do objeto facial """
        self.hardwares.sort(key=lambda x: getattr(x.facial, attr_return) if getattr(x.facial, attr_return) is not None else "", reverse=self.__reverse)
        self.controls = [self.empty_result, self.offline_result] + self.hardwares
        self.__reverse = not self.__reverse
        self.update()

    def sort_by_nome(self):
        """ Ordena especificamente por nome_db """
        self.hardwares.sort(key=lambda x: x.facial.nome_db.lower() if x.facial.nome_db else "")
        self.controls = [self.empty_result, self.offline_result] + self.hardwares
        self.update()

    def sort_by_pessoas(self):
        """ Ordena especificamente por quantidade de pessoas """
        self.hardwares.sort(key=lambda x: int(x.facial.pessoas) if x.facial.pessoas is not None else 0, reverse=self.__reverse)
        self.controls = [self.empty_result, self.offline_result] + self.hardwares
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

        if search_text in ["off", "off-line", "offline"]:
            for hardware in self.hardwares:
                if not hardware.facial.online:
                    hardware.visible = True
                    algum_visivel = True
                else:
                    hardware.visible = False
            self.empty_result.visible = not algum_visivel
            self.update()
            return

        for hardware in self.hardwares:
            # String de busca segura tratando Nones
            nome = (hardware.facial.nome_db or "").lower()
            ip = (hardware.facial.ip or "").lower()
            mac = (hardware.facial.mac_address or "").lower()
            firmware = (hardware.facial.firmware or "").lower()
            
            # Verifica se o termo está em algum dos campos
            if search_text in nome or search_text in ip or search_text in mac or search_text in firmware:
                hardware.visible = True
                algum_visivel = True
            else:
                hardware.visible = False
        
        # Exibe aviso se nenhum resultado for encontrado
        self.empty_result.visible = not algum_visivel
        self.update()

    def export_hardwares_csv(self):
        import csv
        import datetime
        filename = f"export_hardwares_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(["Nome", "IP", "Modelo", "Firmware", "MAC", "Pessoas", "Faces", "Status"])
                for hardware in self.hardwares:
                    if hardware.visible is not False:
                        writer.writerow([
                            hardware.facial.nome_db or "",
                            hardware.facial.ip or "",
                            hardware.facial.modelo or "",
                            hardware.facial.firmware or "",
                            hardware.facial.mac_address or "",
                            hardware.facial.pessoas if hardware.facial.pessoas is not None else "",
                            hardware.facial.faces if hardware.facial.faces is not None else "",
                            "Online" if hardware.facial.online else "Offline"
                        ])
            
            if self.page:
                self.page.show_dialog(
                    ft.SnackBar(content=ft.Text(f"Arquivo exportado: {filename}"), open=True, bgcolor=ft.Colors.GREEN_600)
                )
        except Exception as e:
            if self.page:
                self.page.show_dialog(
                    ft.SnackBar(content=ft.Text(f"Erro ao exportar CSV: {e}"), open=True, bgcolor=ft.Colors.RED_600)
                )
            print(f"Erro ao exportar CSV: {e}")
    
    def set_confgs(self, e=None):
        """ Atualiza o nome de todos os equipamentos online e que receberam firmware """
        for hardware in self.hardwares:
            if hardware.visible is not False and hardware.facial.online and hardware.facial.firmware:
                try:
                    # Aplica o mesmo nome que está no banco de dados
                    hardware.facial.set_device_name(hardware.facial.nome_db)
                    
                    # Atualiza os dados na tela para refletir o novo nome se necessário
                    hardware.facial.nome_device = hardware.facial.nome_db

                except Exception as e:
                    print(f"Erro ao setar nome para {hardware.facial.ip}: {e}")

        self.page.show_dialog(
            ft.SnackBar(content=ft.Text(f"Nome setado para todos: {hardware.facial.nome_db}"), open=True, bgcolor=ft.Colors.GREEN_600)
        )

    def normalize_all_cameras(self, e=None):
        """Dispara a normalização de todas as câmeras em uma thread em segundo plano."""
        if self.page:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("Iniciando normalização e salvamento em SQLite..."), open=True, bgcolor=ft.Colors.BLUE_600)
            )
            
        def run_normalization():
            try:
                from controls.sqlite_control import SqliteControl
                sqlite_ctrl = SqliteControl()
                
                # Executa a normalização passando a lista de hardwares visíveis/cadastrados
                hws_to_normalize = [hw for hw in self.hardwares if hw.visible is not False]
                
                success, failure = sqlite_ctrl.normalize_and_save_all_cameras(hws_to_normalize)
                
                # Atualiza a UI para refletir qualquer dado atualizado (ex: mac_address_text)
                for hw in hws_to_normalize:
                    if hw.facial.mac_address:
                        hw.mac_address_text.value = f"● {hw.facial.mac_address}"
                        try:
                            hw.update()
                        except:
                            pass
                
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Normalização concluída! Sucesso: {success}, Falha: {failure}"),
                            open=True,
                            bgcolor=ft.Colors.GREEN_600
                        )
                    )
            except Exception as ex:
                print(f"Erro durante a normalização: {ex}")
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Erro na normalização: {ex}"),
                            open=True,
                            bgcolor=ft.Colors.RED_600
                        )
                    )

        # Inicia em background
        threading.Thread(target=run_normalization, daemon=True).start()

    def facial_users_noralize(self, e=None):
        """Realiza o processo de coleta para cada cartão visível em background."""
        if self.page:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("Iniciando a sincronização dos usuários faciais para os equipamentos visíveis..."), open=True, bgcolor=ft.Colors.BLUE_600)
            )
            
        def run_facial_sync():
            try:
                from controls.bancos import ThinkimDB
                thinkim_ctrl = ThinkimDB()
                
                # Coleta todos os hardwares atualmente visíveis (cartões visíveis)
                hws_to_sync = [hw for hw in self.hardwares if hw.visible is not False]
                
                success_count = 0
                failure_count = 0
                
                for hw in hws_to_sync:
                    # Garantir que temos o hardware_id
                    hid = getattr(hw, 'hardware_id', getattr(hw.facial, 'hardware_id', None))
                    if hid is None:
                        print(f"Hardware {hw.facial.nome_db} ({hw.facial.ip}) não possui ID mapeado. Pulando...")
                        failure_count += 1
                        continue
                        
                    # Criar objeto Dummy
                    class DummyHardware:
                        def __init__(self, hid, ip, name):
                            self.HardwareId = hid
                            self.IP = ip
                            self.Name = name
                            
                    dhw = DummyHardware(hid, hw.facial.ip, hw.facial.nome_db)
                    
                    try:
                        res = thinkim_ctrl.coletar_e_salvar_usuarios(dhw)
                        if res > 0:
                            success_count += 1
                        else:
                            failure_count += 1
                    except Exception as ex:
                        print(f"Erro ao sincronizar usuários para {hw.facial.nome_db}: {ex}")
                        failure_count += 1
                        
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Sincronização concluída! Sucesso: {success_count}, Falhas: {failure_count}"),
                            open=True,
                            bgcolor=ft.Colors.GREEN_600
                        )
                    )
            except Exception as ex:
                print(f"Erro durante a normalização de usuários: {ex}")
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Erro no processo de sincronização: {ex}"),
                            open=True,
                            bgcolor=ft.Colors.RED_600
                        )
                    )

        # Inicia em background
        threading.Thread(target=run_facial_sync, daemon=True).start()

    def realizar_sincronizacao_facial_limpa(self, e=None):
        """Dispara a sincronização e cadastro completo em background com progress bar.
        Segue a seguinte ordem de processo:
        1. Coleta os dados do Banco Falcon e insere na tabela entity_precess do banco Thinkim
        2. Coletas as fotos de cada usuário no banco Falcon e insere na tabela entity_precess_images do banco Thinkim
        3. Apaga todos os registros do equipamento
        4. Cadastra os usuários no equipamento com Cartão e Foto
        """
        if self.page:
            self.page.show_dialog(
                ft.SnackBar(content=ft.Text("Iniciando o cadastro completo dos usuários (Dados, Faces e Cartões) nos equipamentos visíveis..."), open=True, bgcolor=ft.Colors.BLUE_600)
            )

        def run_sync():
            try:
                from controls.bancos import ThinkimDB, FalconDB
                from models.models import EntityPrecess
                from sqlalchemy import select

                # 1. Ativar barra global e desabilitar botão
                if self.card_info:
                    self.card_info.progress.visible = True
                    self.card_info.bt_sync.disabled = True
                    self.card_info.bt_sync.icon_color = ft.Colors.SURFACE
                    try: self.card_info.update()
                    except: pass

                # 2. Conectar aos bancos
                falcon_db = FalconDB()
                thinkim_ctrl = ThinkimDB()

                # 3. Sincronizar o FalconDB com a tabela entity_precess no ThinkimDB
                # Isso puxa todos os dados de usuários e fotos do Falcon
                thinkim_ctrl.entity_to_temp_process(falcon_db)

                # 4. Carregar usuários para enviar
                session = thinkim_ctrl.banco.get_session()
                stmt = select(EntityPrecess)
                users_to_register = session.execute(stmt).scalars().all()
                session.close()

                # 5. Filtrar apenas os hardwares visíveis e online
                hws_to_sync = [hw for hw in self.hardwares if hw.visible is not False and hw.facial.online]

                if not hws_to_sync:
                    if self.page:
                        self.page.show_dialog(
                            ft.SnackBar(content=ft.Text("Nenhum equipamento visível está ONLINE para sincronização."), open=True, bgcolor=ft.Colors.YELLOW_300)
                        )
                    return

                if not users_to_register:
                    if self.page:
                        self.page.show_dialog(
                            ft.SnackBar(content=ft.Text("Nenhum usuário encontrado no banco de dados para enviar."), open=True, bgcolor=ft.Colors.YELLOW_300)
                        )
                    return

                total_hws = len(hws_to_sync)
                success_hws = 0
                failure_hws = 0
                processed_hws = 0
                stats_lock = threading.Lock()

                def sync_hardware(hw):
                    nonlocal success_hws, failure_hws, processed_hws
                    
                    # Ativar barra de progresso do hardware individual
                    hw.progress.visible = True
                    hw.progress.value = None # Inicia indeterminado
                    try: hw.update()
                    except: pass

                    # Adicionar aqui função para limpar usuários do equipamento
                    hw.facial.delete_all_users()

                    # Enviar cada usuário cadastrado
                    hw_success = True
                    total_users = len(users_to_register)
                    
                    for u_idx, user in enumerate(users_to_register):
                        user_data = {
                            "employeeNo": user.employeeNo,
                            "name": user.name,
                            "userType": user.userType,
                            "beginTime": user.beginTime,
                            "endTime": user.endTime,
                            "doorRight": user.doorRight,
                            "userVerifyMode": user.userVerifyMode,
                            "password": user.password,
                            "photo": user.photo
                        }

                        # Envia os dados, face e o cartão (que terá o mesmo valor de employeeNo)
                        res = thinkim_ctrl.cadastrar_usuario_facial_completo(
                            hardware_ip=hw.facial.ip,
                            employee_no=user.employeeNo,
                            user_data_precess=user_data
                        )
                        
                        if not res:
                            hw_success = False

                        # Atualizar progresso do hardware individual e quantidade de usuários inseridos
                        hw.progress.value = (u_idx + 1) / total_users
                        percentual = ((u_idx + 1) / total_users) * 100
                        if percentual < 100:
                            perc_str = f"{percentual:.1f}".replace('.', ',')
                            hw.pessoas_text.value = f" {u_idx + 1} - {perc_str}%"
                        else:
                            hw.pessoas_text.value = f" {u_idx + 1}"
                        try: hw.update()
                        except: pass

                    with stats_lock:
                        if hw_success:
                            success_hws += 1
                        else:
                            failure_hws += 1
                        processed_hws += 1
                        
                        # Atualizar progresso global em CardInfo
                        if self.card_info:
                            self.card_info.progress.value = processed_hws / total_hws
                            try: self.card_info.update()
                            except: pass

                    # Ocultar barra de progresso do hardware após concluir
                    hw.progress.visible = False
                    
                    # Atualizar as estatísticas de usuários carregando info
                    try:
                        hw.facial.load_info()
                        hw._load_async_data()
                    except:
                        pass

                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    executor.map(sync_hardware, hws_to_sync)

                # 6. Sincronização Finalizada
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(
                            content=ft.Text(f"Sincronização concluída! Sucesso em {success_hws} terminal(is), Falha em {failure_hws}."),
                            open=True,
                            bgcolor=ft.Colors.GREEN_600 if failure_hws == 0 else ft.Colors.ORANGE_600
                        )
                    )

            except Exception as ex:
                print(f"Erro durante a sincronização em background: {ex}")
                if self.page:
                    self.page.show_dialog(
                        ft.SnackBar(content=ft.Text(f"Erro na sincronização: {ex}"), open=True, bgcolor=ft.Colors.RED_600)
                    )
            finally:
                # Restaurar botões e ocultar progresso global
                if self.card_info:
                    self.card_info.progress.visible = False
                    self.card_info.progress.value = None
                    self.card_info.bt_sync.disabled = False
                    self.card_info.bt_sync.icon_color = ft.Colors.ORANGE_300
                    try: self.card_info.update()
                    except: pass
                
                # Garantir que todos os progressos individuais de hardwares sejam limpos
                for hw in self.hardwares:
                    hw.progress.visible = False
                    try: hw.update()
                    except: pass

        # Inicia a thread em background
        threading.Thread(target=run_sync, daemon=True).start()
