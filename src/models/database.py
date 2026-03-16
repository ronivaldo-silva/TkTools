import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis de ambiente a partir do arquivo .env
load_dotenv()

class SqlServer:
    def __init__(self, banco):
        self.host = os.getenv("DB_HOST", "192.168.1.102")
        self.user = os.getenv("DB_USER", "sa")
        self.password = os.getenv("DB_PASSWORD", "S0l1d3fs")
        self.database = banco
        self.engine = None
        self.SessionLocal = None
        
    def get_engine(self):
        """Inicializa e retorna a engine do SQLAlchemy para o banco especificado."""
        if self.engine is None:
            drivers = [
                "ODBC Driver 17 for SQL Server",
                "SQL Server Native Client 11.0",
                "SQL Server"
            ]
            
            for driver in drivers:
                try:
                    params = urllib.parse.quote_plus(
                        f"DRIVER={{{driver}}};"
                        f"SERVER={self.host};"
                        f"DATABASE={self.database};"
                        f"UID={self.user};"
                        f"PWD={self.password}"
                    )
                    connection_url = f"mssql+pyodbc:///?odbc_connect={params}"
                    engine = create_engine(connection_url, fast_executemany=True)
                    # Teste rapido da conexao
                    with engine.connect() as conn:
                        pass
                    
                    self.engine = engine
                    self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
                    break
                except Exception as e:
                    # Tenta proximo driver silenciosamente
                    continue
            
            if self.engine is None:
                print(f"Erro ao conectar ao banco de dados {self.database}. Verifique os drivers OBDC.")
                
        return self.engine

    def get_session(self):
        """Retorna uma nova sessão SQLAlchemy para interação com o banco."""
        if not self.engine:
            self.get_engine()
            
        if self.SessionLocal:
            return self.SessionLocal()
        return None
