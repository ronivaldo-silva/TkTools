import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker

# Carrega as variáveis de ambiente a partir do arquivo .env
load_dotenv()

class SqlServer:
    def __init__(self, banco):
        self.host = os.getenv("DB_HOST", "localhost")
        self.user = os.getenv("DB_USER", "sa")
        self.password = os.getenv("DB_PASSWORD", "S0l1d3fs")
        self.database = banco
        self.engine = None
        self.SessionLocal = None

    def get_engine(self):
        """Inicializa e retorna a engine do SQLAlchemy para o banco especificado.

        Configuração de pool:
          - pool_size=3      : conexões persistentes mantidas abertas.
          - max_overflow=5   : conexões extras permitidas sob carga.
          - pool_pre_ping    : valida a conexão antes de usar (detecta quedas de rede).
          - pool_timeout=10  : máximo de espera por uma conexão do pool (segundos).
          - connect_args     : timeout de handshake ODBC de 8s para não bloquear a UI.
        """
        if self.engine is None:
            try:
                params = URL.create(
                    drivername="mssql+pyodbc",
                    username=self.user,
                    password=self.password,
                    host=self.host,
                    database=self.database,
                    query={
                        "driver": "ODBC Driver 17 for SQL Server"
                    }
                )

                engine = create_engine(
                    params,
                    fast_executemany=True,
                    pool_size=3,
                    max_overflow=5,
                    pool_pre_ping=True,
                    pool_timeout=10,
                    connect_args={"timeout": 8},
                )
                # Teste rápido de conectividade
                with engine.connect() as conn:
                    pass
                self.engine = engine
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine,
                )
                print(f"[DB] Banco '{self.database}' conectado com pool ativo.")
            except Exception as e:
                print(f"[DB] Falha ao conectar ao banco '{self.database}' em {self.host}.")
                print(f"[DB] Detalhe: {e}")

        return self.engine

    def get_session(self):
        """Retorna uma nova sessão SQLAlchemy para interação com o banco."""
        if not self.engine:
            self.get_engine()

        if self.SessionLocal:
            return self.SessionLocal()
        return None
