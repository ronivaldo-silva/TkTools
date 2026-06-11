from sqlalchemy import select
from models.database import SqlServer
from models.models import Hardware, Entity, EntityIdentifier, ThinkimBase, EntityPrecess

class FalconDB:
    def __init__(self):
        self.banco = SqlServer("falcon")
        self.engine = self.banco.get_engine()
        self.is_connected = self.engine is not None

    def _conectar(self):
        return self.engine

    def _try_start_db(self):
        """Tenta conectar ao banco de dados e criar as tabelas se não existirem."""
        try:
            return self.is_connected
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados falcon: {e}")
            self.is_connected = False
            return False

    def _get_hardware(self, hardwaretype:int = None):
        """Busca o hardware do banco de dados usando ORM.
        
        Args:
            hardwaretype (int): Tipo de hardware a ser buscado.
            10 = DECs (Equipamento OTIs para chamada de elevadores)
            7 = Faciais hikvision (Usados)
        
        Returns:
            list: Lista de objetos Hardware.
        """
        session = self.banco.get_session()
        try:
            stmt = select(Hardware)
            if hardwaretype is not None:
                stmt = stmt.where(Hardware.HardwareType == hardwaretype)
            return session.execute(stmt).scalars().all()
        except Exception as e:
            print(f"Erro ao buscar hardware: {e}")
            return []
        finally:
            if session:
                session.close()

    def _get_pessoas(self, isblocked:bool = False, has_face:bool = True):
        session = self.banco.get_session()
        try:
            stmt = select(Entity).where(Entity.EntityType == 1)
            
            if has_face:
                stmt = stmt.join(EntityIdentifier, Entity.EntityId == EntityIdentifier.EntityEntityId)
                
            stmt = stmt.where(Entity.IsBlocked == isblocked)
            return session.execute(stmt).scalars().all()
        except Exception as e:
            print(f"Erro ao buscar pessoas: {e}")
            return []
        finally:
            if session:
                session.close()

    def get_user_base64_photo(self, entity_identifier_id) -> str:
        """Coleta a imagem base64 de um usuário a partir do caminho padrão.
        Nome do arquivo: <EntityIdentifierId>.jpg
        Caminho: C:\\Solid Falcon\\Local\\Photos\\Faces
        """
        import base64
        import os

        base_dir = r"C:\Solid Falcon\Local\Photos\Faces"
        filename = f"{entity_identifier_id}.jpg"
        filepath = os.path.join(base_dir, filename)

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            print(f"Erro ao ler imagem para ID {entity_identifier_id}: {e}")
            return None

class ThinkimDB:
    def __init__(self):
        self.banco = SqlServer("thinkim")
        self.engine = self.banco.get_engine()
        self.is_connected = self.engine is not None
        self.try_start_db()

    def _conectar(self):
        return self.engine

    def try_start_db(self):
        """Tenta conectar ao banco de dados e criar as tabelas se não existirem."""
        try:
            if self.is_connected:
                self._create_tables_if_not_exists()
                return True
            return False
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados thinkim: {e}")
            self.is_connected = False
            return False

    def _create_tables_if_not_exists(self):
        engine = self.banco.get_engine()
        if engine:
            try:
                ThinkimBase.metadata.create_all(engine)
                print("Tabelas do ThinkimDB verificadas/criadas com sucesso (SQLAlchemy).")
            except Exception as e:
                print(f"Erro ao criar tabelas no banco de dados thinkim: {e}")

    def coletar_e_salvar_usuarios(self, hardware: Hardware) -> int:
        """Coleta a lista de usuários de um hardware (Hikvision) e salva na tabela UsuariosFaciais.
        Deleta os usuários correspondentes no banco de dados ANTES de iniciar a coleta.
        
        Args:
            hardware (Hardware): Instância do hardware a ser processado.
            
        Returns:
            int: Quantidade de usuários salvos.
        """
        import os
        from datetime import datetime
        from models.hikvision_isapi import HikvisionClient
        from models.models import UsuariosFaciais
        from sqlalchemy import delete
        
        hw_id = getattr(hardware, 'HardwareId', getattr(hardware, 'hardware_id', None))
        hw_ip = getattr(hardware, 'IP', getattr(hardware, 'ip', None))
        hw_name = getattr(hardware, 'Name', getattr(hardware, 'nome_db', 'Equipamento'))
        
        if hw_id is None:
            print("Erro: Hardware sem ID informado.")
            return 0
            
        # 1. Deletar os usuários no banco ANTES da coleta
        session = self.banco.get_session()
        if not session:
            print("Não foi possível abrir sessão no banco thinkim para exclusão prévia.")
            return 0
        try:
            stmt_delete = delete(UsuariosFaciais).where(UsuariosFaciais.HardwareId == hw_id)
            session.execute(stmt_delete)
            session.commit()
            print(f"Usuários do HardwareId {hw_id} deletados previamente com sucesso.")
        except Exception as e:
            session.rollback()
            print(f"Erro ao deletar usuários antigos de HardwareId {hw_id} antes da coleta: {e}")
        finally:
            session.close()
            
        # 2. Iniciar coleta do hardware
        default_user = os.getenv("HIK_USER", "admin").strip("'\"")
        default_pass = os.getenv("HIK_PASS", "@ThinKim2020").strip("'\"")
        
        client = HikvisionClient(hw_ip, default_user, default_pass)
        
        print(f"Conectando ao hardware {hw_name} ({hw_ip})...")
        
        usuarios_coletados = []
        pagina = 1
        total_matches = None
        responseStatusStrg = None
        
        def parse_isapi_datetime(dt_str):
            if not dt_str:
                return None
            try:
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1] + '+00:00'
                return datetime.fromisoformat(dt_str)
            except Exception:
                try:
                    return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    return None

        print(f'Coletando os dados do hardware {hw_name} ({hw_ip})...')
        while True:
            res = client.get_user_list(pagina=pagina)
            if res == "Err" or not isinstance(res, dict):
                print(f"Erro ou resposta inválida do hardware {hw_ip} na página {pagina}.")
                break
            
            search_res = res.get("UserInfoSearch", {})
            
            # Inicializa totalMatches na primeira iteração
            if total_matches is None:
                total_matches = search_res.get("totalMatches", 0)
                if total_matches == 0:
                    print(f"Hardware {hw_name} retornou 0 totalMatches de usuários.")
                    break

            # Se a requisição for bem-sucedida, o equipamento retornará o status de resposta 
            # indicando se a busca terminou ("OK") ou 
            # se ainda há mais dados para serem coletados em outras páginas ("MORE")
            if responseStatusStrg is None:
                responseStatusStrg = search_res.get("responseStatusStrg", "OK")
            
            user_info_list = search_res.get("UserInfo", [])
            if isinstance(user_info_list, dict):
                user_info_list = [user_info_list]
                
            if not user_info_list:
                break
                
            for user in user_info_list:
                emp_no = user.get("employeeNo")
                if not emp_no:
                    continue
                    
                valid_dict = user.get("Valid", {})
                begin_time = parse_isapi_datetime(valid_dict.get("beginTime"))
                end_time = parse_isapi_datetime(valid_dict.get("endTime"))
                
                # Tratamento robusto para doorRight/RightPlan
                door_right = None
                right_plan = user.get("RightPlan", [])
                if isinstance(right_plan, dict):
                    right_plan = [right_plan]
                if isinstance(right_plan, list) and right_plan:
                    door_right = str(right_plan[0].get("planTemplateNo", ""))
                
                # Tratamento para name (garantir conversão para string e evitar dicionários)
                name = user.get("name")
                if isinstance(name, dict):
                    name = name.get("#text") or str(name)
                elif name is not None:
                    name = str(name)
                    
                # Tratamento para userType (garantir conversão para string)
                user_type = user.get("userType")
                if isinstance(user_type, dict):
                    user_type = user_type.get("#text") or str(user_type)
                elif user_type is not None:
                    user_type = str(user_type)
                
                usuarios_coletados.append({
                    "HardwareId": hw_id,
                    "employeeNo": str(emp_no),
                    "name": name,
                    "userType": user_type,
                    "beginTime": begin_time,
                    "endTime": end_time,
                    "doorRight": door_right,
                    "numOfCard": int(user.get("numOfCard", 0)) if user.get("numOfCard") is not None else 0,
                    "numOfFace": int(user.get("numOfFace", 0)) if user.get("numOfFace") is not None else 0
                })
            
            # Para o loop se coletamos todos os totalMatches ou se a página retornou menos que 100 usuários
            if responseStatusStrg == "OK":
                break
            pagina += 1

        if not usuarios_coletados:
            print(f"Nenhum usuário coletado do hardware {hw_name} ({hw_ip}).")
            return 0

        # 3. Salvar no banco os dados coletados
        session = self.banco.get_session()
        if not session:
            print("Não foi possível abrir sessão no banco thinkim para salvar os dados.")
            return 0
            
        try:
            for user_data in usuarios_coletados:
                db_user = UsuariosFaciais(**user_data)
                session.add(db_user)
                
            session.commit()
            print(f"Sincronizados {len(usuarios_coletados)} usuários para o hardware {hw_name} no banco thinkim.")
            return len(usuarios_coletados)
        except Exception as e:
            session.rollback()
            print(f"Erro ao salvar usuários no banco thinkim: {e}")
            return 0
        finally:
            session.close()

    def entity_to_temp_process(self, falcon_db: FalconDB) -> int:
        """Coleta dados de usuários ativos do FalconDB, busca suas fotos em base64 e os salva/atualiza na tabela entity_precess."""
        from datetime import datetime, timedelta
        from models.models import EntityPrecess, Entity, EntityIdentifier
        from sqlalchemy import select

        falcon_session = falcon_db.banco.get_session()
        if not falcon_session:
            print("Não foi possível abrir sessão no banco falcon.")
            return 0

        users_to_sync = []
        try:
            # Seleciona usuários ativos (EntityType = 1 e IsBlocked = False) que possuem identificadores
            stmt = select(EntityIdentifier.EntityIdentifierId, Entity.Name)\
                .join(Entity, Entity.EntityId == EntityIdentifier.EntityEntityId)\
                .where(Entity.EntityType == 1, Entity.IsBlocked == False)
            
            results = falcon_session.execute(stmt).all()
            
            for row in results:
                emp_id = row.EntityIdentifierId
                name = row.Name
                
                # Coleta a imagem base64
                photo_b64 = falcon_db.get_user_base64_photo(emp_id)
                
                hoje = datetime.now()
                # Limita endTime a 2037-12-31 para evitar estouro do Unix Epoch (Year 2038 overflow) no hardware embarcado
                hoje_mais_30 = datetime(2037, 12, 31, 23, 59, 59)
                
                users_to_sync.append({
                    "employeeNo": str(emp_id),
                    "name": name,
                    "userType": "normal",
                    "beginTime": hoje,
                    "endTime": hoje_mais_30,
                    "doorRight": "1",
                    "userVerifyMode": "face",
                    "password": "",
                    "photo": photo_b64
                })
        except Exception as e:
            print(f"Erro ao buscar pessoas do FalconDB para precess: {e}")
            return 0
        finally:
            falcon_session.close()

        if not users_to_sync:
            print("Nenhum usuário ativo com identificador encontrado no FalconDB.")
            return 0

        # Gravar no ThinkimDB
        thinkim_session = self.banco.get_session()
        if not thinkim_session:
            print("Não foi possível abrir sessão no banco thinkim.")
            return 0

        success_count = 0
        try:
            thinkim_session.query(EntityPrecess).delete(synchronize_session=False)
            thinkim_session.commit()
        except Exception as e:
            thinkim_session.rollback()
            print(f"Erro ao limpar tabela entity_precess: {e}")
            return 0

        try:
            for user_data in users_to_sync:
                stmt_check = select(EntityPrecess).where(EntityPrecess.employeeNo == user_data["employeeNo"])
                existing = thinkim_session.execute(stmt_check).scalar_one_or_none()
                
                if existing:
                    existing.name = user_data["name"]
                    existing.userType = user_data["userType"]
                    existing.beginTime = user_data["beginTime"]
                    existing.endTime = user_data["endTime"]
                    existing.doorRight = user_data["doorRight"]
                    existing.userVerifyMode = user_data["userVerifyMode"]
                    existing.password = user_data["password"]
                    existing.photo = user_data["photo"]
                else:
                    new_entity = EntityPrecess(**user_data)
                    thinkim_session.add(new_entity)
                
                success_count += 1
                
            thinkim_session.commit()
            print(f"Sincronizados {success_count} usuários na tabela entity_precess.")
            return success_count
        except Exception as e:
            thinkim_session.rollback()
            print(f"Erro ao salvar na tabela entity_precess: {e}")
            return 0
        finally:
            thinkim_session.close()

    def cadastrar_usuario_facial_completo(self, hardware_ip: str, employee_no: str, user_data_precess: dict = None) -> bool:
        """
        Cadastra um usuário completo no terminal Hikvision de forma síncrona.
        Realiza:
          1. Cadastro textual do usuário.
          2. Vinculação da face biométrica (se houver foto).
          3. Vinculação do cartão de acesso (número do cartão sendo o mesmo employeeNo).
        
        Args:
          hardware_ip (str): IP do terminal.
          employee_no (str): Identificador do usuário (employeeNo).
          user_data_precess (dict, opcional): Dados do usuário já extraídos da tabela entity_precess.
                                               Se não fornecido, busca na tabela localmente.
        """
        import os
        from models.hikvision_isapi import HikvisionClient
        from models.models import EntityPrecess
        from sqlalchemy import select

        # 1. Obter dados da tabela entity_precess se não fornecidos
        if not user_data_precess:
            session = self.banco.get_session()
            if not session:
                print("Não foi possível abrir sessão no thinkim para buscar dados do precess.")
                return False
            try:
                stmt = select(EntityPrecess).where(EntityPrecess.employeeNo == str(employee_no))
                db_record = session.execute(stmt).scalar_one_or_none()
                if not db_record:
                    print(f"Usuário {employee_no} não encontrado na tabela entity_precess.")
                    return False
                user_data_precess = {
                    "employeeNo": db_record.employeeNo,
                    "name": db_record.name,
                    "userType": db_record.userType,
                    "beginTime": db_record.beginTime,
                    "endTime": db_record.endTime,
                    "doorRight": db_record.doorRight,
                    "userVerifyMode": db_record.userVerifyMode,
                    "password": db_record.password,
                    "photo": db_record.photo
                }
            except Exception as e:
                print(f"Erro ao consultar entity_precess para {employee_no}: {e}")
                return False
            finally:
                session.close()

        # 2. Conectar ao cliente Hikvision
        default_user = os.getenv("HIK_USER", "admin").strip("'\"")
        default_pass = os.getenv("HIK_PASS", "@ThinKim2020").strip("'\"")
        client = HikvisionClient(hardware_ip, default_user, default_pass)

        try:
            # 3. Formatar dados para o padrão ISAPI
            hik_user_data = {
                "employeeNo": str(employee_no),
                "name": user_data_precess["name"],
                "userType": user_data_precess["userType"],
                "closeDelayEnabled": False,
                "Valid": {
                    "enable": True,
                    "beginTime": user_data_precess["beginTime"].strftime("%Y-%m-%dT%H:%M:%S") if hasattr(user_data_precess["beginTime"], 'strftime') else str(user_data_precess["beginTime"]),
                    "endTime": user_data_precess["endTime"].strftime("%Y-%m-%dT%H:%M:%S") if hasattr(user_data_precess["endTime"], 'strftime') else str(user_data_precess["endTime"]),
                    "timeType": "local"
                },
                "doorRight": user_data_precess.get("doorRight", "1"),
                "RightPlan": [
                    {
                        "doorNo": 1,
                        "planTemplateNo": "1"
                    }
                ]
            }

            # 4. Cadastrar dados textuais
            print(f"Registrando usuário {employee_no} ({user_data_precess['name']}) no terminal {hardware_ip}...")
            client.create_user(employee_no, hik_user_data)

            # 5. Se possuir foto, registrar a face
            if user_data_precess.get("photo"):
                print(f"Enviando face em base64 para o usuário {employee_no}...")
                client.set_user_face_base64(
                    employee_no=employee_no,
                    name=user_data_precess["name"],
                    photo_b64=user_data_precess["photo"]
                )

            # 6. Registrar o cartão (o número do cartão deve ser o mesmo employeeNo!)
            print(f"Registrando cartão de acesso '{employee_no}' para o usuário {employee_no}...")
            client.set_user_card(employee_no, card_no=employee_no)

            print(f"[OK] Usuário {employee_no} sincronizado com face e cartão com sucesso!")
            return True
        except Exception as e:
            print(f"[-] Erro ao cadastrar usuário completo {employee_no} no terminal {hardware_ip}: {e}")
            return False
