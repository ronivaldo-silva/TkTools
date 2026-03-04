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
             raise Exception(f"HTTP Error: {e.response.status_code}")
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
             raise Exception(f"HTTP Error: {e.response.status_code}")
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

    def get_user_count(self):
        try:
            info = self.get_user_info_count()
            return info.get('userNumber', 0)
        except Exception as e:
             logging.error(f"Error getting user count for {self.ip}: {e}")
             return "Err"

    def get_face_count(self):
        try:
            info = self.get_user_info_count()
            return info.get('bindFaceUserNumber', 0)
        except Exception as e:
            logging.error(f"Error getting face count for {self.ip}: {e}")
            return "Err"

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

    def get_access_groups(self, id:int = 1):
        """Lista todos os grupos de acesso via ISAPI e retorna uma lista de dicts."""

        data = self._get_request(f"/ISAPI/AccessControl/UserRightPlanTemplate/{id}")
        
        return data.json()

    def get_user_list(self, pagina:int = 1) -> dict:
        try:
            payload = {
                "UserInfoSearchCond": {
                    "searchID": '1',
                    "maxResults": 100,
                    "searchResultPosition": (pagina -1) * 100
                }
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

            tabela = pd.DataFrame(data['UserInfoSearch']['UserInfo'])

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


    def set_advertising_mode(self, mode: str = "advertising", display_type: str = "full", popup_preview: bool = True):
        """
        Configura o modo de exibição do terminal (IdentityTerminal).
        :param mode: "normal", "concise", "advertising", "meeting", "selfDefine"
        :param display_type: "full" ou "split" (apenas para modo advertising)
        :param popup_preview: True/False (exibe janela de visualização)
        """
        endpoint = "/ISAPI/AccessControl/IdentityTerminal?format=json"
        
        payload = {
            "IdentityTerminal": {
                "showMode": mode,
                "advertisingDisplayType": display_type,
                "popUpPreviewWindow": popup_preview
            }
        }
        
        try:
            # PUT request to update configuration
            response = self._put_request(endpoint, json_data=payload)
            return response.json()
        except Exception as e:
            logging.error(f"Error setting advertising mode for {self.ip}: {e}")
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
