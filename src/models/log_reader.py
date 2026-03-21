import os

class LogReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read_all_lines(self):
        """Lê e retorna as linhas do arquivo de texto."""
        if not os.path.exists(self.file_path):
            print(f"[LogReader] Arquivo não encontrado: {self.file_path}")
            return []
        try:
            print(f"[LogReader] Lendo as linhas do arquivo: {self.file_path}")
            with open(self.file_path, "r", encoding="utf-8") as f:
                linhas = [line.strip() for line in f.readlines() if line.strip()]
            print(f"[LogReader] {len(linhas)} linhas lidas com sucesso.")
            return linhas
        except Exception as e:
            print(f"[LogReader] Erro ao ler arquivo {self.file_path}: {e}")
            return []

    def get_modified_time(self):
        """Retorna o tempo de modificação do arquivo para detecção de alterações."""
        if not os.path.exists(self.file_path):
            return 0
        try:
            return os.path.getmtime(self.file_path)
        except OSError:
            return 0
