import time
import os
from dotenv import load_dotenv
from datetime import datetime
from threading import Thread

from models.database import SqlServer
from models.log_reader import LogReader
from models.models import LogElevators, LogIntegrations
from sqlalchemy import select, desc

load_dotenv()

class LogElevatorControl:
    """
    Controle projetado para monitorar um arquivo de log e atualizar no banco de dados.
    """
    def __init__(self, file_path="C:/Solid Falcon/Integrations/Elevators/Local/Logs/ElevatorsLog.txt"):
        self.path = os.getenv("PATH_LOG_ELEVATOR", file_path)
        self.db = SqlServer("thinkim")
        self.log_reader = LogReader(self.path)
        self.is_running = False

    def _parse_file_line(self, line):
        parts = line.split(" - ", 1)
        if len(parts) == 2:
            datahora_str = parts[0].strip()
            dados = parts[1].strip()
            try:
                datetime.strptime(datahora_str, "%d/%m/%Y %H:%M")
                return datahora_str, dados
            except ValueError:
                pass
        return "", line.strip()

    def atualizar_banco(self):
        try:
            linhas = self.log_reader.read_all_lines()
            if not linhas:
                return

            session = self.db.get_session()
            if not session:
                return
            
            # Busca últimos registros no banco (usamos os ultimos inseridos)
            stmt = select(LogElevators).order_by(desc(LogElevators.id)).limit(100)
            ultimos_db = session.execute(stmt).scalars().all()

            db_signature = []
            for row in ultimos_db:
                if row.datahora:
                    dh_str = row.datahora.strftime("%d/%m/%Y %H:%M")
                else:
                    dh_str = ""
                db_signature.append((dh_str, row.dados or ''))

            # Parse log do arquivo 
            # (Note: logs mais recentes estão no topo do arquivo)
            file_parsed = [self._parse_file_line(l) for l in linhas]

            match_index = -1
            db_len = len(db_signature)

            if db_len > 0:
                for i in range(len(file_parsed)):
                    if file_parsed[i] == db_signature[0]:
                        match = True
                        check_len = min(db_len, len(file_parsed) - i)
                        for j in range(check_len):
                            if file_parsed[i+j] != db_signature[j]:
                                match = False
                                break
                        # Busca por sequencia de garantias para evitar hits em linhas comuns de status
                        if match and check_len >= min(db_len, 5):
                            match_index = i
                            break

            if match_index == -1:
                novas_linhas = linhas
            else:
                novas_linhas = linhas[:match_index]

            # Inserção a partir dos antigos para garantir a integridade DB e lógicas de sequencia 
            # (oldest is index N, newest is index 0)
            print(f"[LogElevatorControl] Preparando inserção de {len(novas_linhas)} novas linhas no banco...")
            linhas_inseridas = 0
            for linha in reversed(novas_linhas):
                dh_str, dados = self._parse_file_line(linha)
                if dh_str:
                    dh_sql = datetime.strptime(dh_str, "%d/%m/%Y %H:%M")
                    novo_log = LogElevators(datahora=dh_sql, dados=dados)
                else:
                    novo_log = LogElevators(dados=linha)
                session.add(novo_log)
                linhas_inseridas += 1
            session.commit()
            print(f"[LogElevatorControl] Concluído! {linhas_inseridas} registros salvos no banco.")
            session.close()

        except Exception as e:
            print(f"[LogElevatorControl] Erro ao atualizar o banco: {e}")

    def _monitor_loop(self):
        last_mtime = self.log_reader.get_modified_time()
        while self.is_running:
            try:
                current_mtime = self.log_reader.get_modified_time()
                if current_mtime != last_mtime:
                    print(f"[LogElevatorControl] Mudança detectada no arquivo. Atualizando...")
                    last_mtime = current_mtime
                    self.atualizar_banco()
            except Exception as e:
                print(f"[LogElevatorControl] Erro na thread de monitoramento: {e}")
            time.sleep(2)

    def iniciar(self):
        if not self.is_running:
            self.is_running = True
            self.atualizar_banco()
            thread = Thread(target=self._monitor_loop, daemon=True)
            thread.start()
            print("Monitoramento iniciado.")

    def parar(self):
        self.is_running = False
        print("Monitoramento finalizado.")

class LogIntegrationControl:
    """
    Controle projetado para monitorar um arquivo de log de integrações e atualizar no banco de dados.
    """
    def __init__(self, file_path="C:/Solid Falcon/Local/Logs/IntegrationsLog.txt"):
        self.path = os.getenv("PATH_LOG_INTEGRATION", file_path)
        self.db = SqlServer("thinkim")
        self.log_reader = LogReader(self.path)
        self.is_running = False

    def _parse_file_line(self, line):
        parts = line.split(" - ", 1)
        if len(parts) == 2:
            datahora_str = parts[0].strip()
            rest = parts[1].strip()
            
            if ":" in rest:
                ev_parts = rest.split(":", 1)
                evento = ev_parts[0].strip()
                dados = ev_parts[1].strip()
            else:
                evento = rest
                dados = ""
                
            try:
                datetime.strptime(datahora_str, "%d/%m/%Y %H:%M")
                return datahora_str, evento, dados
            except ValueError:
                pass
        return "", "", line.strip()

    def atualizar_banco(self):
        try:
            linhas = self.log_reader.read_all_lines()
            if not linhas:
                return

            session = self.db.get_session()
            if not session:
                return

            stmt = select(LogIntegrations).order_by(desc(LogIntegrations.id)).limit(100)
            ultimos_db = session.execute(stmt).scalars().all()

            db_signature = []
            for row in ultimos_db:
                if row.datahora:
                    dh_str = row.datahora.strftime("%d/%m/%Y %H:%M")
                else:
                    dh_str = ""
                db_signature.append((dh_str, row.evento or '', row.dados or ''))

            file_parsed = [self._parse_file_line(l) for l in linhas]

            match_index = -1
            db_len = len(db_signature)

            if db_len > 0:
                for i in range(len(file_parsed)):
                    if file_parsed[i] == db_signature[0]:
                        match = True
                        check_len = min(db_len, len(file_parsed) - i)
                        for j in range(check_len):
                            if file_parsed[i+j] != db_signature[j]:
                                match = False
                                break
                        # Busca por sequencia de garantias para evitar hits em linhas comuns de status
                        if match and check_len >= min(db_len, 5):
                            match_index = i
                            break

            if match_index == -1:
                novas_linhas = linhas
            else:
                novas_linhas = linhas[:match_index]

            print(f"[LogIntegrationControl] Preparando inserção de {len(novas_linhas)} novas linhas no banco...")
            linhas_inseridas = 0
            for linha in reversed(novas_linhas):
                dh_str, evento, dados = self._parse_file_line(linha)
                if dh_str:
                    dh_sql = datetime.strptime(dh_str, "%d/%m/%Y %H:%M")
                    novo_log = LogIntegrations(datahora=dh_sql, evento=evento, dados=dados)
                else:
                    novo_log = LogIntegrations(dados=linha)
                session.add(novo_log)
                linhas_inseridas += 1
            session.commit()
            print(f"[LogIntegrationControl] Concluído! {linhas_inseridas} registros salvos no banco de integrações.")
            session.close()

        except Exception as e:
            print(f"[LogIntegrationControl] Erro ao atualizar o banco de integrações: {e}")

    def _monitor_loop(self):
        last_mtime = self.log_reader.get_modified_time()
        while self.is_running:
            try:
                current_mtime = self.log_reader.get_modified_time()
                if current_mtime != last_mtime:
                    print(f"[LogIntegrationControl] Mudança detectada no arquivo. Atualizando...")
                    last_mtime = current_mtime
                    self.atualizar_banco()
            except Exception as e:
                print(f"[LogIntegrationControl] Erro na thread de monitoramento: {e}")
            time.sleep(2)

    def iniciar(self):
        if not self.is_running:
            self.is_running = True
            self.atualizar_banco()
            thread = Thread(target=self._monitor_loop, daemon=True)
            thread.start()
            print("Monitoramento de integrações iniciado.")

    def parar(self):
        self.is_running = False
        print("Monitoramento de integrações finalizado.")
