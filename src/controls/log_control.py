import time
import os
from datetime import datetime
from threading import Thread

from models.database import SqlServer
from models.log_reader import LogReader

class LogElevatorControl:
    """
    Controle projetado para monitorar um arquivo de log e atualizar no banco de dados.
    """
    def __init__(self, file_path):
        self.db = SqlServer("thinkim")
        self.log_reader = LogReader(file_path)
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

            # Busca últimos registros no banco (usamos os ultimos inseridos)
            ultimos_db = self.db.consultar("SELECT TOP 100 datahora, dados FROM log_elevators ORDER BY id DESC")
            if not ultimos_db:
                ultimos_db = []

            db_signature = []
            for row in ultimos_db:
                if row.get('datahora'):
                    if isinstance(row['datahora'], str):
                        try:
                            dt = datetime.strptime(row['datahora'].split('.')[0], "%Y-%m-%d %H:%M:%S")
                            dh_str = dt.strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            dh_str = row['datahora']
                    else:
                        dh_str = row['datahora'].strftime("%d/%m/%Y %H:%M")
                else:
                    dh_str = ""
                db_signature.append((dh_str, row.get('dados', '')))

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
            for linha in reversed(novas_linhas):
                dh_str, dados = self._parse_file_line(linha)
                if dh_str:
                    dh_sql = datetime.strptime(dh_str, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:00")
                    self.db.inserir("INSERT INTO log_elevators (datahora, dados) VALUES (?, ?)", (dh_sql, dados))
                else:
                    self.db.inserir("INSERT INTO log_elevators (dados) VALUES (?)", (linha,))

        except Exception as e:
            print(f"Erro ao atualizar o banco: {e}")

    def _monitor_loop(self):
        last_mtime = self.log_reader.get_modified_time()
        while self.is_running:
            try:
                current_mtime = self.log_reader.get_modified_time()
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    self.atualizar_banco()
            except Exception:
                pass
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
    def __init__(self, file_path):
        self.db = SqlServer("thinkim")
        self.log_reader = LogReader(file_path)
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

            ultimos_db = self.db.consultar("SELECT TOP 100 datahora, evento, dados FROM log_integrations ORDER BY id DESC")
            if not ultimos_db:
                ultimos_db = []

            db_signature = []
            for row in ultimos_db:
                if row.get('datahora'):
                    if isinstance(row['datahora'], str):
                        try:
                            dt = datetime.strptime(row['datahora'].split('.')[0], "%Y-%m-%d %H:%M:%S")
                            dh_str = dt.strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            dh_str = row['datahora']
                    else:
                        dh_str = row['datahora'].strftime("%d/%m/%Y %H:%M")
                else:
                    dh_str = ""
                db_signature.append((dh_str, row.get('evento', ''), row.get('dados', '')))

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

            for linha in reversed(novas_linhas):
                dh_str, evento, dados = self._parse_file_line(linha)
                if dh_str:
                    dh_sql = datetime.strptime(dh_str, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:00")
                    self.db.inserir("INSERT INTO log_integrations (datahora, evento, dados) VALUES (?, ?, ?)", (dh_sql, evento, dados))
                else:
                    self.db.inserir("INSERT INTO log_integrations (dados) VALUES (?)", (linha,))

        except Exception as e:
            print(f"Erro ao atualizar o banco de integrações: {e}")

    def _monitor_loop(self):
        last_mtime = self.log_reader.get_modified_time()
        while self.is_running:
            try:
                current_mtime = self.log_reader.get_modified_time()
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    self.atualizar_banco()
            except Exception:
                pass
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
