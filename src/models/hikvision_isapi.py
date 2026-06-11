from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import logging
import requests
import uuid

class HikvisionClient:
    def __init__(self, ip, username, password):
        self.ip = ip
        self.username = username
        self.password = password
        self.base_url = f"http://{ip}"
        self.timeout = 5  # Seconds

    def _get_request(self, endpoint, data=None, json_data=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if json_data:
                response = requests.post(url, auth=HTTPDigestAuth(self.username, self.password), json=json_data, timeout=self.timeout)
            elif data:
                response = requests.post(url, auth=HTTPDigestAuth(self.username, self.password), data=data, timeout=self.timeout)
            else:
                response = requests.get(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise Exception("Timeout")
        except requests.exceptions.ConnectionError:
            raise Exception("Offline")
        except requests.exceptions.HTTPError as e:
             raise Exception(f"HTTP Error: {e.response.status_code} - Response: {e.response.text}")
        except Exception as e:
            raise Exception(str(e))

    def _put_request(self, endpoint, data=None, json_data=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if json_data:
                response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password), json=json_data, timeout=self.timeout)
            elif data:
                response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password), data=data, timeout=self.timeout)
            else:
                response = requests.put(url, auth=HTTPDigestAuth(self.username, self.password), timeout=self.timeout)
            
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise Exception("Timeout")
        except requests.exceptions.ConnectionError:
            raise Exception("Offline")
        except requests.exceptions.HTTPError as e:
             raise Exception(f"HTTP Error: {e.response.status_code} - Response: {e.response.text}")
        except Exception as e:
            raise Exception(str(e))

    def get_user_info_count(self):
        """
        Retorna um resumo estatístico do total de usuários, faces, digitais, etc.
        Endpoint: GET /ISAPI/AccessControl/UserInfo/Count?format=json

        Retorna Dicionário no formato:
            "UserInfoCount": {
                "userNumber": int,
                "bindFaceUserNumber": int,
                "bindFingerprintUserNumber": int,
                "bindCardUserNumber": int,
                "bindRemoteControlNumber": int
            }
        """
        try:
            response = self._get_request("/ISAPI/AccessControl/UserInfo/Count?format=json")
            return response.json().get('UserInfoCount', {})
        except Exception as e:
            logging.error(f"Error getting user info count for {self.ip}: {e}")
            raise e

    def get_device_capacity(self):
        """
        Tenta buscar a capacidade máxima de usuários do dispositivo via /ISAPI/AccessControl/Capabilities.
        Retorna um inteiro (ex: 10000) ou None se não encontrar.
        """
        try:
            # Tentar via JSON primeiro
            response = self._get_request("/ISAPI/AccessControl/Capabilities?format=json")
            
            # Tenta decodificar o JSON somente se houver corpo de resposta
            if response.content:
                try:
                    data = response.json()
                    # Estrutura típica: AccessControl -> UserInfo -> maxUserInfoNum
                    if "AccessControl" in data and "UserInfo" in data["AccessControl"]:
                        return int(data["AccessControl"]["UserInfo"].get("maxUserInfoNum", 0))
                except Exception:
                    pass # Vai cair no fallback de XML
            
            return 10000 # Valor default seguro se não conseguir ler
            
        except Exception as e:
            # Fallback para XML se JSON falhar
            try:
                response = self._get_request("/ISAPI/AccessControl/Capabilities")
                content = response.text
                # Parse simples strings
                import re
                match = re.search(r"<maxUserInfoNum>(\d+)</maxUserInfoNum>", content)
                if match:
                    return int(match.group(1))
            except:
                pass
            
            logging.error(f"Error getting capacity for {self.ip}: {e}")
            return 0

    def get_device_info(self):
        """Retorna informações detalhadas do hardware (modelo, serial, fw, etc).
        Retorna dicionário com elementos:
            deviceName
            deviceID
            model
            serialNumber
            macAddress
            firmwareVersion
            firmwareReleasedDate
            encoderVersion
            encoderReleasedDate
            deviceType
            subDeviceType
            manufacturer
            customizedInfo
            productionDate
        """
        try:
            response = self._get_request("/ISAPI/System/deviceInfo")
            content = response.text
            
            import re
            content_cleaned = re.sub(r' xmlns="[^"]+"', '', content, count=1)
            content_cleaned = re.sub(r' xmlns:[a-zA-Z0-9]+="[^"]+"', '', content_cleaned)
            
            root = ET.fromstring(content_cleaned)
            info = {}
            for child in root:
                info[child.tag] = child.text
                
            return info
        except Exception as e:
            logging.error(f"Erro ao obter informacoes do dispositivo {self.ip}: {e}")
            raise e

    def set_device_name(self, name: str):
        """
        Altera o nome do dispositivo.
        Método HTTP: PUT
        Endpoint: /ISAPI/System/deviceInfo?format=json
        """
        try:
            # 1. Coleta os dados atuais em XML com GET
            response_get = self._get_request("/ISAPI/System/deviceInfo")
            xml_data = response_get.text
            
            # 2. Altera o campo <deviceName> com o nome novo
            import re
            novo_xml = re.sub(r'<deviceName>.*?</deviceName>', f'<deviceName>{name}</deviceName>', xml_data, flags=re.IGNORECASE | re.DOTALL)
            
            # Caso o equipamento retorne tag vazia como <deviceName/>
            if '<deviceName/>' in novo_xml:
                novo_xml = novo_xml.replace('<deviceName/>', f'<deviceName>{name}</deviceName>')
            
            # 3. Envia o XML atualizado como corpo em PUT
            endpoint_put = "/ISAPI/System/deviceInfo"
            response_put = self._put_request(endpoint_put, data=novo_xml)
            return response_put.text
        except Exception as e:
            logging.error(f"Erro ao alterar nome do dispositivo {self.ip}: {e}")
            raise e

    def get_access_groups(self, id:int = 1):
        """Lista todos os grupos de acesso via ISAPI e retorna uma lista de dicts."""

        data = self._get_request(f"/ISAPI/AccessControl/UserRightPlanTemplate/{id}")
        
        return data.json()

    def get_user_list(self, pagina:int = 1, max_results:int = 30, user_type:str = None, name:str = None, employee_ids:list = None, has_face:bool = None, has_card:bool = None) -> dict:
        try:
            cond = {
                "searchID": '1',
                "maxResults": max_results,
                "searchResultPosition": (pagina - 1) * max_results
            }
            if user_type:
                cond["userType"] = user_type
            if name:
                cond["fuzzySearch"] = name
            if has_face is not None:
                cond["hasFace"] = bool(has_face)
            if has_card is not None:
                cond["hasCard"] = bool(has_card)
            if employee_ids:
                cond["EmployeeNoList"] = [{"employeeNo": str(eid)} for eid in employee_ids]

            payload = {
                "UserInfoSearchCond": cond
            }
            response = self._get_request("/ISAPI/AccessControl/UserInfo/Search?format=json", json_data=payload)
            data = response.json()
            return data
        except Exception as e:
            logging.error(f"Error getting user list for {self.ip}: {e}")
            return "Err"

    def get_user(self, position: int = 0, max_results: int = 30, 
                 user_type: str = "normal", name: str = None, employee_ids: list = None, 
                 has_face: bool = None, has_card: bool = None) -> dict:
        """
        Busca usuários com filtros e paginação (UserInfoSearch).
        :param position: Posição inicial (searchResultPosition)
        :param max_results: Máximo de resultados
        :param user_type: Tipo de usuário (ex: 'normal')
        :param name: Busca aproximada por nome (fuzzySearch)
        :param employee_ids: Lista de matrículas (EmployeeNoList)
        :param has_face: Filtra quem tem face
        :param has_card: Filtra quem tem cartão
        :return: JSON response (dict)
        """

        cond = {
            "searchID": '1',
            "searchResultPosition": position,
            "maxResults": max_results,
            "userType": user_type
        }

        if name:
            cond["fuzzySearch"] = name
        
        if has_face is not None:
            cond["hasFace"] = bool(has_face)
            
        if has_card is not None:
            cond["hasCard"] = bool(has_card)

        if employee_ids:
            # EmployeeNoList expects [{'employeeNo': '1001'}, ...]
            cond["EmployeeNoList"] = [{"employeeNo": str(eid)} for eid in employee_ids]

        payload = {
            "UserInfoSearchCond": cond
        }

        try:
            response = self._get_request("/ISAPI/AccessControl/UserInfo/Search?format=json", json_data=payload)
            return response.json()
        except Exception as e:
            logging.error(f"Error getting users from {self.ip}: {e}")
            raise e

    def get_user_list_to_table(self, pagina:int = 1) -> dict:
        try:
            response = self.get_user_list(pagina)
            data = response

            tabela = None #pd.DataFrame(data['UserInfoSearch']['UserInfo'])

            tabela['RightPlan'] = tabela['RightPlan'].apply(lambda x: x[0]['planTemplateNo'])
            
            return tabela
        except Exception as e:
            logging.error(f"Error getting user list for {self.ip}: {e}")
            return "Err"

    def insert_rule(self, id_regra: int, nome_regra: str, id_week_plan: int = 1):
        """
        Insere uma regra de acesso (UserRightPlanTemplate).
        Padrão: Acesso Sempre (weekPlanNo = 1).
        """
        endpoint = f"/ISAPI/AccessControl/UserRightPlanTemplate/{id_regra}?format=json"
        
        payload = {
            "UserRightPlanTemplate": {
                "enable": True,
                "templateName": nome_regra,
                "weekPlanNo": id_week_plan,
                "holidayGroupNo": ""
            }
        }
        
        try:
            # PUT is typically used for creating/updating specific ID resources in ISAPI
            response = self._put_request(endpoint, json_data=payload)
            # Response handling logic can be refined if needed, usually returns status in JSON
            return response.json()
        except Exception as e:
            logging.error(f"Error inserting rule {id_regra} for {self.ip}: {e}")
            raise e

    def get_week_plans(self, id):
        plan_url = f"/ISAPI/AccessControl/UserRightWeekPlanCfg/{id}?format=json"
        resp = self._get_request(plan_url)
        return resp.json()

    def get_week_plans_list(self, _ = None):
        """
        Retorna uma lista de Planos Semanais (UserRightWeekPlanCfg).
        Processo: Checa capabilities para pegar o range de IDs e itera GET por ID.
        """
        plans = []
        try:
            # 1. Check Capabilities for range
            cap_url = "/ISAPI/AccessControl/UserRightWeekPlanCfg/capabilities?format=json"
            try:
                cap_resp = self._get_request(cap_url)
                cap_data = cap_resp.json()
                # Finding max planNo. Structure varies, but looking for UserRightWeekPlanCfg -> planNo -> @max
                # Example: {'UserRightWeekPlanCfg': {'planNo': {'@min': '1', '@max': '16'}}}
                max_plans = 16 # Default
                if 'UserRightWeekPlanCfg' in cap_data:
                    plan_no = cap_data['UserRightWeekPlanCfg'].get('planNo', {})
                    if '@max' in plan_no:
                        max_plans = int(plan_no['@max'])
            except Exception as e:
                logging.warning(f"Could not get WeekPlan capabilities, defaulting to 16: {e}")
                max_plans = 16

            # 2. Iterate
            for i in range(1, max_plans + 1):
                try:
                    plan_url = f"/ISAPI/AccessControl/UserRightWeekPlanCfg/{i}?format=json"
                    resp = self._get_request(plan_url)
                    data = resp.json()
                    
                    # Check if enabled/valid
                    # Structure: {'UserRightWeekPlanCfg': {'enable': True, 'weekPlanNo': 1, ...}}
                    if 'UserRightWeekPlanCfg' in data:
                        plan_info = data['UserRightWeekPlanCfg']
                        # Some devices might return plan even if empty/disabled, so we can filter or just add all.
                        # User documentation suggests checking 'enable'.
                        if plan_info.get('enable'):
                             plans.append(plan_info)
                except Exception as iter_err:
                    # If an ID doesn't exist or error, just continue or log
                    # logging.debug(f"Plan {i} not found or error: {iter_err}")
                    continue
            
            return plans

        except Exception as e:
            logging.error(f"Error getting week plans for {self.ip}: {e}")
            return "Err"

    def insert_week_plan(self, id_plan: int, week_config: list = None):
        """
        Insere/Configura um Plano Semanal (UserRightWeekPlanCfg).
        :param id_plan: ID do plano (ex: 1).
        :param week_config: Lista de dicts com a configuração dos dias. Se None, cria padrão 24hs todos os dias.
        """
        endpoint = f"/ISAPI/AccessControl/UserRightWeekPlanCfg/{id_plan}?format=json"

        if week_config is None:
            # Default configuration: Full Access 00:00-23:59:59
            week_config = []
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for day in days:
                week_config.append({
                    "week": day,
                    "id": 1,
                    "enable": True,
                    "TimeSegment": {
                        "beginTime": "00:00:00",
                        "endTime": "23:59:59"
                    }
                })

        payload = {
            "UserRightWeekPlanCfg": {
                "enable": True,
                "WeekPlanCfg": week_config
            }
        }

        try:
            response = self._put_request(endpoint, json_data=payload)
            return response.json()
        except Exception as e:
            logging.error(f"Error inserting week plan {id_plan} for {self.ip}: {e}")
            raise e

    def get_event_access(self, start_time: str, end_time: str, employee_no: str = None, name: str = None, card_no: str = None, major: int = 5, minor: int = 0, max_results: int = 30):
        """
        Coleta registros de eventos de acesso (AcsEvent).
        Suporta paginação automática.
        :param start_time: Data inicio ISO 8601 (ex: "2024-05-01T08:00:00+08:00")
        :param end_time: Data fim ISO 8601
        :param employee_no: Filtro por matrícula
        :param name: Filtro por nome
        :param card_no: Filtro por cartão
        :param major: Tipo Principal (default 5 para acesso)
        :param minor: Subtipo (default 0 para todos)
        :param max_results: Resultados por página
        """
        endpoint = "/ISAPI/AccessControl/AcsEvent?format=json"
        
        # Gera UUID único para esta busca
        search_id = str(uuid.uuid4())
        position = 0
        all_events = []
        
        while True:
            # Constrói o payload da requisição
            acs_event_cond = {
                "searchID": search_id,
                "searchResultPosition": position,
                "maxResults": max_results,
                "major": major,
                "minor": minor,
                "startTime": start_time,
                "endTime": end_time,
                "picEnable": False
            }
            
            # Adiciona filtros opcionais se fornecidos
            if employee_no:
                acs_event_cond["employeeNoString"] = employee_no
            if name:
                acs_event_cond["name"] = name
            if card_no:
                acs_event_cond["cardNo"] = card_no
            
            payload = {"AcsEventCond": acs_event_cond}
                
            try:
                # _get_request usa POST se json_data for fornecido
                # Nota: A implementação original de _get_request usa POST se json_data for passado.
                response = self._get_request(endpoint, json_data=payload)
                data = response.json()
                
                response_status = data.get("AcsEvent", {}).get("responseStatusStrg", "NO MORE")
                
                # Check for matches
                if "AcsEvent" in data and "InfoList" in data["AcsEvent"]:
                    info_list = data["AcsEvent"]["InfoList"]
                    
                    if not info_list:
                         break

                    # InfoList pode ser uma lista ou um único dict?
                    # Geralmente é uma lista de dicts.
                    if isinstance(info_list, list):
                        all_events.extend(info_list)
                        position += len(info_list)
                    elif isinstance(info_list, dict): 
                         # Caso retorne um único objeto não envelopado em lista (menos comum em JSON array, mas possível na conversão XML->JSON interna da lib do Hikvision se houver)
                         all_events.append(info_list)
                         position += 1
                else:
                    # Nenhum evento encontrado nesta página ou estrutura diferente
                    break
                    
                # Se não houver mais registros, sai do loop
                if response_status != "MORE":
                    break
                    
            except Exception as e:
                logging.error(f"Error getting access events from {self.ip}: {e}")
                # Se falhar no meio, retorna o que pegou ou levanta erro?
                # Vamos levantar erro para ser tratado lá fora se não pegou nada
                raise e
                
        return all_events

    def set_IdentityTerminal_showmode(self, showmode: str = "normal", display_type: str = "full", popup_preview: bool = True):
        """
        Configura o modo de exibição do terminal (IdentityTerminal).
        :param showmode: "normal", "concise", "advertising", "meeting", "selfDefine"
        :param display_type: "full" ou "split" (apenas para modo advertising)
        :param popup_preview: True/False (exibe janela de visualização)
        """
        endpoint = "/ISAPI/AccessControl/IdentityTerminal"
        
        try:
            # 1. Coleta os dados atuais em XML com GET
            response_get = self._get_request(endpoint)
            xml_data = response_get.text
            
            # 2. Altera o campo <showMode> com o novo modo
            import re
            novo_xml = re.sub(r'<showMode>.*?</showMode>', f'<showMode>{showmode}</showMode>', xml_data, flags=re.IGNORECASE | re.DOTALL)
            
            # Caso o equipamento retorne tag vazia como <showMode/>
            if '<showMode/>' in novo_xml:
                novo_xml = novo_xml.replace('<showMode/>', f'<showMode>{showmode}</showMode>')
            
            # Opcional: Alterar os demais campos se existirem no XML (popUpPreviewWindow e advertisingDisplayType)
            # Para o scopo da instrução, garantimos a alteração do showMode acima
            
            # 3. Envia o XML atualizado como corpo em PUT
            response_put = self._put_request(endpoint, data=novo_xml)
            return response_put.text
        except Exception as e:
            logging.error(f"Erro ao configurar showMode no terminal {self.ip}: {e}")
            raise e

    def reboot_device(self):
        """
        Reinicia o equipamento (reboot).
        Método: PUT
        Endpoint: /ISAPI/System/reboot
        """
        endpoint = "/ISAPI/System/reboot"
        
        try:
            response = self._put_request(endpoint)
            # Tenta converter o XML de resposta
            content = response.text
            
            import re
            content_cleaned = re.sub(r' xmlns="[^"]+"', '', content, count=1)
            content_cleaned = re.sub(r' xmlns:[a-zA-Z0-9]+="[^"]+"', '', content_cleaned)
            
            try:
                root = ET.fromstring(content_cleaned)
                status_string = root.find(".//statusString")
                if status_string is not None:
                    return {"status": status_string.text, "raw": content}
            except Exception:
                pass
                
            return {"status": "OK", "raw": content}

        except Exception as e:
            logging.error(f"Erro ao reiniciar o dispositivo {self.ip}: {e}")
            raise e

    # Trabalhos com HTTP Hosts configuração de envio de eventos para servidor
    def get_http_host_capabilities(self, host_type: str = None):
        """
        Obtem as capacidades de configuração dos servidores de escuta (Listening Hosts).
        Permite descobrir quais configurações o dispositivo suporta e os limites dos campos.
        
        :param host_type: (Opcional) 'custom' ou 'default'.
        :return: Dicionário contendo as capacidades sob a chave raiz 'HttpHostNotificationCap'.
                 Aqui você encontra número de hosts suportados, formatos, protocolos, limites e eventos aceitos.
        """
        # Constrói o endpoint considerando os query params opcionais
        base_endpoint = "/ISAPI/Event/notification/httpHosts/capabilities"
        params = ["format=json"]
        if host_type:
            params.append(f"type={host_type}")
        
        endpoint = f"{base_endpoint}?{'&'.join(params)}"

        try:
            response = self._get_request(endpoint)
            # Tenta converter o JSON nativamente
            if response.headers.get("Content-Type", "").startswith("application/json") or response.text.strip().startswith("{"):
                try:
                    return response.json()
                except Exception:
                    pass

            # Se não veio JSON, o equipamento respondeu em XML (fallback padrão)
            content = response.text
            import re
            content_cleaned = re.sub(r' xmlns="[^"]+"', '', content, count=1)
            content_cleaned = re.sub(r' xmlns:[a-zA-Z0-9]+="[^"]+"', '', content_cleaned)

            root = ET.fromstring(content_cleaned)
            
            # Função recursiva para transformar o XML da Hikvision em um Dicionário Python
            def xml_to_dict(element):
                # Se o elemento tem atributos, adiciona-os com prefixo '@' (ex: limits como @min, @max)
                result = {f"@{k}": v for k, v in element.attrib.items()}
                
                # Se houver elementos filhos
                if list(element):
                    for child in element:
                        child_result = xml_to_dict(child)
                        
                        if child.tag in result:
                            # Se já existe a chave, transforma em lista (isso lida com <EventList><Event>...)
                            if isinstance(result[child.tag], list):
                                result[child.tag].append(child_result)
                            else:
                                result[child.tag] = [result[child.tag], child_result]
                        else:
                            result[child.tag] = child_result
                else:
                    # Sem filhos, é apenas texto ou atributos
                    text = element.text.strip() if element.text else ""
                    if text:
                        if result:
                            result['#text'] = text
                        else:
                            return text
                    elif not result:
                        return ""
                
                return result

            return {root.tag: xml_to_dict(root)}

        except Exception as e:
            logging.error(f"Erro ao obter capacidades de http hosts do dispositivo {self.ip}: {e}")
            raise e

    def get_http_hosts(self, host_id: int = None):
        """
        Coleta os httpHosts (servidores de escuta/recebimento de eventos) cadastrados no equipamento usando XML.
        
        :param host_id: (Opcional) ID específico do host (1 a 10). Se None, retorna todos os hosts.
        :return: Uma lista de dicionários (se host_id for None) ou um único dicionário (se ID especificado) no formato:
            {
                "id": str,
                "url": str,
                "protocolType": str,
                "parameterFormatType": str,
                "addressingFormatType": str,
                "ipAddress": str,
                "portNo": str,
                "httpAuthenticationMethod": str
            }
        """
        if host_id is not None:
            endpoint = f"/ISAPI/Event/notification/httpHosts/{host_id}"
        else:
            endpoint = "/ISAPI/Event/notification/httpHosts"

        try:
            response = self._get_request(endpoint)
            content = response.text
            
            # Limpeza de namespaces para facilitar o parser com ET
            import re
            content_cleaned = re.sub(r' xmlns="[^"]+"', '', content, count=1)
            content_cleaned = re.sub(r' xmlns:[a-zA-Z0-9]+="[^"]+"', '', content_cleaned)
            
            root = ET.fromstring(content_cleaned)
            
            def parse_host_node(node):
                return {
                    "id": getattr(node.find('id'), 'text', ''),
                    "url": getattr(node.find('url'), 'text', ''),
                    "protocolType": getattr(node.find('protocolType'), 'text', ''),
                    "parameterFormatType": getattr(node.find('parameterFormatType'), 'text', ''),
                    "addressingFormatType": getattr(node.find('addressingFormatType'), 'text', ''),
                    "ipAddress": getattr(node.find('ipAddress'), 'text', ''),
                    "portNo": getattr(node.find('portNo'), 'text', ''),
                    "httpAuthenticationMethod": getattr(node.find('httpAuthenticationMethod'), 'text', '')
                }

            if root.tag == "HttpHostNotificationList":
                hosts = []
                for child in root.findall('HttpHostNotification'):
                     hosts.append(parse_host_node(child))
                return hosts
            elif root.tag == "HttpHostNotification":
                return parse_host_node(root)
            else:
                return {"status": "error", "message": f"Tag raiz desconhecida: {root.tag}", "raw": content}

        except Exception as e:
            logging.error(f"Erro ao obter http hosts do dispositivo {self.ip}: {e}")
            raise e

    def config_http_host(self, server_ip: str, endpoint: str, host_id: int = 1, port: int = 8080, heartbeat_interval: int = 30):
        """
        Configura o equipamento para enviar requisições de eventos e heartbeats para o servidor (Listening Mode).
        :param server_ip: IP do servidor que vai escutar os eventos.
        :param endpoint: A rota (URI) da API/Servidor que vai receber o POST (ex: /api/eventos).
        :param host_id: O número do Host ID (de 1 a 10). Padrão é 1.
        :param port: A porta do servidor. Padrão é 8080.
        :param heartbeat_interval: Intervalo em segundos para envio do pulso de vida. Padrão é 30.
        """
        url_endpoint = f"/ISAPI/Event/notification/httpHosts/{host_id}?format=json"
        
        payload = {
            "HttpHostNotification": {
                "id": str(host_id),
                "url": endpoint, 
                "protocolType": "HTTP",
                "parameterFormatType": "JSON",
                "addressingFormatType": "ipaddress",
                "ipAddress": server_ip,
                "portNo": port,
                "httpAuthenticationMethod": "none",
                "enabled": True,
                "SubscribeEvent": {
                    "heartbeat": heartbeat_interval,
                    "eventMode": "all"
                }
            }
        }
        
        try:
            response = self._put_request(url_endpoint, json_data=payload)
            # A resposta pode ser vazia dependendo da versão do firmware, mas normalmente retorna status 200 OK
            if response.content:
                try:
                    return response.json()
                except:
                    pass
            return {"status": "OK", "message": f"Heartbeat configurado com sucesso para {server_ip}:{port}{endpoint}"}
        except Exception as e:
            logging.error(f"Erro ao configurar heartbeat no dispositivo {self.ip}: {e}")
            raise e

    # Configurações globais de Controle de Acesso (AcsCfg)
    def get_acs_capabilities(self):
        """
        Obtém as capacidades de configuração do dispositivo (AcsCfg).
        Método: GET
        Endpoint: /ISAPI/AccessControl/AcsCfg/capabilities?format=json
        """
        endpoint = "/ISAPI/AccessControl/AcsCfg/capabilities?format=json"
        try:
            response = self._get_request(endpoint)
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            return {"AcsCfg": {}}
        except Exception as e:
            logging.error(f"Erro ao obter capacidades de AcsCfg do dispositivo {self.ip}: {e}")
            raise e

    def get_acs_cfg(self):
        """
        Lê as configurações atuais do controle de acesso (AcsCfg).
        Método: GET
        Endpoint: /ISAPI/AccessControl/AcsCfg?format=json
        """
        endpoint = "/ISAPI/AccessControl/AcsCfg?format=json"
        try:
            response = self._get_request(endpoint)
            # Para fallback, é bom checar se veio algo e tentar o parse:
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            return {}
        except Exception as e:
            logging.error(f"Erro ao coletar configurações de AcsCfg no dispositivo {self.ip}: {e}")
            raise e

    def set_acs_cfg(self, config_dict: dict):
        """
        Altera as configurações do controle de acesso (AcsCfg).
        Método: PUT
        Endpoint: /ISAPI/AccessControl/AcsCfg?format=json
        
        :param config_dict: Dicionário contendo os parâmetros que deseja alterar, 
                            Exemplo: {"showName": True, "voicePrompt": False}
        """
        endpoint = "/ISAPI/AccessControl/AcsCfg?format=json"
        
        # Constrói o corpo da requisição conforme o modelo da Hikvision
        payload = {
            "AcsCfg": config_dict
        }
        
        try:
            response = self._put_request(endpoint, json_data=payload)
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            # Baseado no exemplo de Retorno (Sucesso) fornecido por você
            return {
                "statusCode": 1,
                "statusString": "ok",
                "subStatusCode": "ok",
                "errorCode": 1,
                "errorMsg": "ok"
            }
        except Exception as e:
            logging.error(f"Erro ao configurar AcsCfg no dispositivo {self.ip}: {e}")
            raise e

    # Configurações de Botões de Atalho e Intercomunicador (KeyCfg)
    def get_key_capabilities(self, key_id: int = 1):
        """
        Obtém as capacidades de configuração do botão/atalho da tela (KeyCfg).
        Método: GET
        Endpoint: /ISAPI/VideoIntercom/keyCfg/<key_id>/capabilities?format=json
        """
        endpoint = f"/ISAPI/VideoIntercom/keyCfg/{key_id}/capabilities?format=json"
        try:
            response = self._get_request(endpoint)
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            return {"KeyCfg": {}}
        except Exception as e:
            logging.error(f"Erro ao obter capacidades de KeyCfg do botão {key_id} no dispositivo {self.ip}: {e}")
            raise e

    def get_key_cfg(self, key_id: int = 1):
        """
        Lê como o botão de atalho está configurado no momento (KeyCfg).
        Método: GET
        Endpoint: /ISAPI/VideoIntercom/keyCfg/<key_id>?format=json
        """
        endpoint = f"/ISAPI/VideoIntercom/keyCfg/{key_id}?format=json"
        try:
            response = self._get_request(endpoint)
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            return {}
        except Exception as e:
            logging.error(f"Erro ao coletar configurações de KeyCfg do botão {key_id} no dispositivo {self.ip}: {e}")
            raise e

    def set_key_cfg(self, key_id: int, config_dict: dict):
        """
        Altera as configurações de funcionalidade e ação do botão (KeyCfg).
        Método: PUT
        Endpoint: /ISAPI/VideoIntercom/keyCfg/<key_id>?format=json
        
        :param key_id: ID numérico do botão (geralmente 1 para o principal).
        :param config_dict: Dicionário contendo os parâmetros da alteração.
                            A tag 'id' será embutida internamente para segurança.
                            Exemplo: {"callMethod": "manageCenter", "enableCallCenter": True}
        """
        endpoint = f"/ISAPI/VideoIntercom/keyCfg/{key_id}?format=json"
        
        # Garante a presença do ID na estrutura enviada se ele foi intencionalmente modificado
        config_dict["id"] = key_id
        
        payload = {
            "KeyCfg": config_dict
        }
        
        try:
            response = self._put_request(endpoint, json_data=payload)
            if response.content:
                try:
                    return response.json()
                except Exception:
                    pass
            return {
                "statusCode": 1,
                "statusString": "OK",
                "subStatusCode": "OK",
                "errorCode": 1,
                "errorMsg": "ok"
            }
        except Exception as e:
            logging.error(f"Erro ao configurar KeyCfg do botão {key_id} no dispositivo {self.ip}: {e}")
            raise e

    def create_user(self, employee_no: str, user_data: dict) -> dict:
        """
        Cria/insere um novo usuário no equipamento.
        Método: POST
        Endpoint: /ISAPI/AccessControl/UserInfo/Record?format=json
        """
        endpoint = "/ISAPI/AccessControl/UserInfo/Record?format=json"
        user_data["employeeNo"] = str(employee_no)
        payload = {"UserInfo": user_data}
        try:
            response = self._get_request(endpoint, json_data=payload)
            data = response.json()
            if str(data.get("statusCode", "1")) != "1":
                raise Exception(f"Falha ao criar usuário ({employee_no}): {data.get('errorMsg', 'Erro desconhecido')} (Status: {data.get('statusCode')})")
            return data
        except Exception as e:
            logging.error(f"Erro ao criar usuário {employee_no} no dispositivo {self.ip}: {e}")
            raise e

    def edit_user(self, employee_no: str, user_data: dict) -> dict:
        """
        1. Alterar Usuário (Edit Person Information)
        Objetivo: Modificar os dados de um usuário já existente.
        Método HTTP: PUT
        Endpoint: /ISAPI/AccessControl/UserInfo/Modify?format=json
        
        :param employee_no: Número da matrícula do usuário (obrigatório).
        :param user_data: Dicionário com os dados modificados do usuário a serem enviados.
        :return: Resposta JSON confirmando a edição.
        """
        endpoint = "/ISAPI/AccessControl/UserInfo/Modify?format=json"
        
        # Regra do Payload: O JSON deve ser enviado dentro do objeto "UserInfo".
        # O campo "employeeNo" é obrigatório para identificar quem será alterado.
        user_data["employeeNo"] = str(employee_no)
        payload = {"UserInfo": user_data}
        
        try:
            response = self._put_request(endpoint, json_data=payload)
            data = response.json()
            
            # Tratamento de erro: lendo o "statusCode" da resposta.
            # Se for diferente de 1, lance uma exceção contendo o "errorMsg".
            if str(data.get("statusCode", "1")) != "1":
                raise Exception(f"Falha ao alterar usuário ({employee_no}): {data.get('errorMsg', 'Erro desconhecido')} (Status: {data.get('statusCode')})")
                
            return data
        except Exception as e:
            logging.error(f"Erro ao modificar usuário {employee_no} no dispositivo {self.ip}: {e}")
            raise e

    def delete_users(self, mode: str = "all", employee_ids: list = None) -> dict:
        """
        2. Deletar Usuário(s) (Delete Person Information)
        Objetivo: Excluir usuários específicos ou todos os usuários.
        Método HTTP: PUT
        Endpoint: /ISAPI/AccessControl/UserInfoDetail/Delete?format=json
        
        :param mode: "all" para limpar todos os usuários, ou "byEmployeeNo" para excluir por IDs.
        :param employee_ids: Lista de matrículas em formato string (ex: ["1001", "1002"]).
        :return: Resposta JSON confirmando a deleção.
        """
        endpoint = "/ISAPI/AccessControl/UserInfoDetail/Delete?format=json"
        
        # Regra do Payload: O JSON deve indicar o "mode" de exclusão
        payload = {
            "UserInfoDetail": {
                "mode": mode
            }
        }
        
        # Se for por ID, deve enviar a lista "EmployeeNoList"
        if mode == "byEmployeeNo" and employee_ids:
            payload["UserInfoDetail"]["EmployeeNoList"] = [{"employeeNo": str(eid)} for eid in employee_ids]
            
        try:
            response = self._put_request(endpoint, json_data=payload)
            data = response.json()
            
            # Validação dostatusCode e errorMsg
            if str(data.get("statusCode", "1")) != "1":
                raise Exception(f"Falha ao deletar usuários (modo: {mode}): {data.get('errorMsg', 'Erro desconhecido')} (Status: {data.get('statusCode')})")
                
            return data
        except Exception as e:
            logging.error(f"Erro ao deletar usuários no dispositivo {self.ip}: {e}")
            raise e

    def get_user_capabilities(self) -> dict:
        """
        3 - A) Obter Capacidade de Usuários
        Objetivo: Consultar capacidades e suporte de operações da rota de UserInfo.
        Método HTTP: GET
        Endpoint: /ISAPI/AccessControl/UserInfo/capabilities?format=json
        
        :return: Dicionário contendo os dados brutos de capacidade e o atributo mapeado "supports_put_modify".
        """
        endpoint = "/ISAPI/AccessControl/UserInfo/capabilities?format=json"
        
        try:
            response = self._get_request(endpoint)
            data = response.json()
            
            # O código deve mapear no JSON de retorno se o nó supportFunction contém a string "put"
            supports_put = False
            user_info_cap = data.get("UserInfo", {})
            
            if "supportFunction" in user_info_cap:
                supp_func = user_info_cap["supportFunction"]
                if isinstance(supp_func, dict) and "@opt" in supp_func:
                    supports_put = "put" in supp_func["@opt"].lower()
                elif isinstance(supp_func, str):
                    supports_put = "put" in supp_func.lower()
                    
            return {
                "raw_capabilities": data,
                "supports_put_modify": supports_put
            }
        except Exception as e:
            logging.error(f"Erro ao obter capacidades de UserInfo no dispositivo {self.ip}: {e}")
            raise e

    def get_delete_capabilities(self) -> dict:
        """
        3 - B) Obter Capacidade de Exclusão
        Objetivo: Consultar capacidades da rota de exclusão (Delete).
        Método HTTP: GET
        Endpoint: /ISAPI/AccessControl/UserInfoDetail/Delete/capabilities?format=json
        
        :return: Dicionário mapeando os modos de exclusão suportados.
        """
        endpoint = "/ISAPI/AccessControl/UserInfoDetail/Delete/capabilities?format=json"
        
        try:
            response = self._get_request(endpoint)
            data = response.json()
            
            # O código deve mapear os modos de exclusão suportados no nó "mode"
            modes_suportados = []
            delete_cap = data.get("UserInfoDetail", {})
            
            if "mode" in delete_cap:
                mode_node = delete_cap["mode"]
                if isinstance(mode_node, dict) and "@opt" in mode_node:
                    modes_suportados = mode_node["@opt"].split(",")
                elif isinstance(mode_node, str):
                    modes_suportados = mode_node.split(",")
                    
            return {
                "raw_capabilities": data,
                "supported_modes": modes_suportados
            }
        except Exception as e:
            logging.error(f"Erro ao obter capacidades do Delete no dispositivo {self.ip}: {e}")
            raise e

    def get_delete_process_status(self) -> dict:
        """
        4. Coletar Status da Deleção em Massa (Delete Process)
        Objetivo: Monitorar o progresso do processo de exclusão de usuários na base de dados do dispositivo.
        Método HTTP: GET
        Endpoint: /ISAPI/AccessControl/UserInfoDetail/DeleteProcess?format=json
        
        :return: Dicionário contendo o percentual (0 a 100) e o status atual.
        """
        endpoint = "/ISAPI/AccessControl/UserInfoDetail/DeleteProcess?format=json"
        
        try:
            response = self._get_request(endpoint)
            data = response.json()
            
            # A função deve processar o JSON de resposta extraindo "status" e "percent"
            process_data = data.get("UserInfoDetailDeleteProcess", {})
            
            status = process_data.get("status", "unknown")
            percent = 0
            if "percent" in process_data:
                try:
                    percent = int(process_data["percent"])
                except ValueError:
                    percent = 0
                    
            return {
                "status": status,
                "percent": percent,
                "raw_process_data": data
            }
        except Exception as e:
            logging.error(f"Erro ao obter o status do delete process no dispositivo {self.ip}: {e}")
            raise e

    def get_system_time(self) -> dict:
        """
        Coleta as configuracoes de data e hora atuais do equipamento.
        Metodo: GET
        Endpoint: /ISAPI/System/time
        Autenticacao: HTTP Digest Auth.
        
        A funcao realiza o parser do XML retornado pela API da Hikvision
        convertendo o padrao ISO 8601 da tag <localTime> para um objeto de formato nativo datetime
        utilizando datetime.fromisoformat.
        """
        endpoint = "/ISAPI/System/time"
        
        try:
            response = self._get_request(endpoint)
            
            content = response.text
            import re
            
            # Limpa namespaces da resposta XML para facilitar a analise usando ElementTree
            content_cleaned = re.sub(r' xmlns="[^"]+"', '', content, count=1)
            content_cleaned = re.sub(r' xmlns:[a-zA-Z0-9]+="[^"]+"', '', content_cleaned)
            
            root = ET.fromstring(content_cleaned)
            
            result_dict = {}
            for child in root:
                if child.tag == 'localTime' and child.text:
                    # O valor da tag <localTime> vem no padrao ISO 8601 (com fuso horario).
                    # Utilizamos o metodo datetime.fromisoformat() para transformar diretamente.
                    from datetime import datetime
                    try:
                        result_dict[child.tag] = datetime.fromisoformat(child.text)
                    except ValueError:
                        # Excecao para caso particular o formato saia do padrao nativo
                        result_dict[child.tag] = child.text
                else:
                    result_dict[child.tag] = child.text
                    
            return result_dict
            
        except Exception as e:
            logging.error(f"Erro ao obter configuracoes de tempo do dispositivo {self.ip}: {e}")
            raise e

    def set_user_card(self, employee_no: str, card_no: str, card_type: str = "normalCard") -> dict:
        """
        Insere/vincula um cartão a um usuário recém-criado.
        Método: POST
        Endpoint: /ISAPI/AccessControl/CardInfo/Record?format=json
        """
        endpoint = "/ISAPI/AccessControl/CardInfo/Record?format=json"
        payload = {
            "CardInfo": {
                "employeeNo": str(employee_no),
                "cardNo": str(card_no),
                "cardType": card_type
            }
        }
        try:
            # Reutiliza o _get_request que faz o POST se passar json_data
            response = self._get_request(endpoint, json_data=payload)
            data = response.json()
            if str(data.get("statusCode", "1")) != "1":
                raise Exception(f"Falha ao cadastrar cartão ({card_no}) para usuário ({employee_no}): {data.get('errorMsg', 'Erro desconhecido')} (Status: {data.get('statusCode')})")
            return data
        except Exception as e:
            logging.error(f"Erro ao vincular cartão {card_no} ao usuário {employee_no}: {e}")
            raise e

    def set_user_face_base64(self, employee_no: str, name: str, photo_b64: str, face_lib_type: str = "blackFD", fdid: str = "1") -> dict:
        """
        Envia a foto da face do usuário a partir de uma string Base64.

        Decodifica o Base64 para bytes e realiza o envio via multipart/form-data:
          - Part 'faceURL': JSON com metadados (faceLibType, FDID, FPID, name)
          - Part 'img': bytes binários do JPEG

        Método: POST
        Endpoint: /ISAPI/Intelligent/FDLib/FaceDataRecord?format=json
        """
        import base64 as _b64
        import json as _json
        from requests.auth import HTTPDigestAuth

        try:
            photo_bytes = _b64.b64decode(photo_b64)
        except Exception as e:
            raise ValueError(f"Falha ao decodificar imagem base64 para usuário {employee_no}: {e}")

        url = f"{self.base_url}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"

        face_meta = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": str(employee_no),
            "name": name
        }

        files = {
            "faceURL": (None, _json.dumps(face_meta), "application/json"),
            "img": ("face.jpg", photo_bytes, "image/jpeg")
        }

        try:
            resp = requests.post(
                url,
                auth=HTTPDigestAuth(self.username, self.password),
                files=files,
                timeout=self.timeout
            )
            if resp.ok:
                return resp.json()
            raise Exception(f"HTTP Error: {resp.status_code} - Response: {resp.text}")
        except Exception as e:
            logging.error(f"Erro ao cadastrar face para usuário {employee_no}: {e}")
            raise e

    def set_user_face_multipart(self, employee_no: str, photo_bytes: bytes, face_lib_type: str = "blackFD", fdid: str = "1") -> dict:
        """
        Envia a foto da face do usuário usando formato multipart/form-data.
        Método: POST
        Endpoint: /ISAPI/Intelligent/FDLib/FaceDataRecord?format=json
        """
        url = f"{self.base_url}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
        
        # Parte 1 (Dados do usuário): faceURL
        face_url_json = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": str(employee_no)
        }
        
        # Constrói o multipart
        import json
        files = {
            "faceURL": (None, json.dumps(face_url_json), "application/json"),
            "img": ("face.jpg", photo_bytes, "image/jpeg")
        }
        
        try:
            from requests.auth import HTTPDigestAuth
            response = requests.post(
                url, 
                auth=HTTPDigestAuth(self.username, self.password), 
                files=files, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro ao cadastrar face multipart para usuário {employee_no}: {e}")
            raise e


