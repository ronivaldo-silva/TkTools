import os
import pyodbc
from dotenv import load_dotenv

# Carrega as variáveis de ambiente a partir do arquivo .env
load_dotenv()

class SqlServer:
    def __init__(self, banco):
        self.host = os.getenv("DB_HOST", "192.168.1.102")
        self.user = os.getenv("DB_USER", "sa")
        self.password = os.getenv("DB_PASSWORD", "S0l1d3fs")
        self.database = banco
        
    def _conectar(self):
        """Estabelece a conexão com o banco de dados SQL Server."""
        try:
            # Tenta conectar usando drivers comuns no Windows
            drivers = [
                "{ODBC Driver 17 for SQL Server}",
                "{SQL Server Native Client 11.0}",
                "{SQL Server}"
            ]
            
            conn = None
            last_err = None
            
            for driver in drivers:
                conn_str = f"DRIVER={driver};SERVER={self.host};DATABASE={self.database};UID={self.user};PWD={self.password}"
                try:
                    conn = pyodbc.connect(conn_str)
                    break
                except pyodbc.Error as e:
                    last_err = e
                    continue
            
            if not conn:
                print(f"Erro ao conectar ao banco de dados. Último erro: {last_err}")
                
            return conn
        except Exception as e:
            print(f"Erro inesperado na conexão: {e}")
            return None

    def _conectar_master(self):
        """Estabelece a conexão com o banco de dados SQL Server."""
        try:
            # Tenta conectar usando drivers comuns no Windows
            drivers = [
                "{ODBC Driver 17 for SQL Server}",
                "{SQL Server Native Client 11.0}",
                "{SQL Server}"
            ]
            
            conn = None
            last_err = None
            
            for driver in drivers:
                conn_str = f"DRIVER={driver};SERVER={self.host};DATABASE=master;UID={self.user};PWD={self.password}"
                try:
                    conn = pyodbc.connect(conn_str)
                    break
                except pyodbc.Error as e:
                    last_err = e
                    continue
            
            if not conn:
                print(f"Erro ao conectar ao banco de dados. Último erro: {last_err}")
                
            return conn
        except Exception as e:
            print(f"Erro inesperado na conexão: {e}")
            return None

    def _executar(self, query, params=None):
        """Método auxiliar para executar comandos que alteram o banco (INSERT/UPDATE/DELETE)."""
        conn = self._conectar()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao executar comando: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def consultar(self, query, params=None):
        """Método básico para consultas (SELECT). Retorna lista de dicionários."""
        conn = self._conectar()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
            else:
                return []
        except Exception as e:
            print(f"Erro na consulta: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def inserir(self, query, params=None):
        """Método básico para inserção de dados (INSERT)."""
        return self._executar(query, params)

    def alterar(self, query, params=None):
        """Método básico para alteração de dados (UPDATE)."""
        return self._executar(query, params)

    def deletar(self, query, params=None):
        """Método básico para exclusão de dados (DELETE)."""
        return self._executar(query, params)

    def create_table(self, nome:str, colunas:list[str], primary_key:str = None):
        """Método básico para criação de tabelas caso não exista.
        Args:
            nome (str): Nome da tabela.
            colunas (list[str]): Lista de colunas no formato "nome tipo".
            primary_key (str, optional): Chave primária. Padrão None.
        Returns:
            bool: True se a tabela foi criada ou já existia, False caso contrário.
        
        OBS: Script para SQL Server
        """
        if primary_key:
            colunas.append(f"PRIMARY KEY ({primary_key})")

        query = f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{nome}' AND xtype='U')
        CREATE TABLE {nome} ({', '.join(colunas)})
        """
        conn = self._conectar_master()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao criar tabela: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def create_database(self):
        """Método básico para criação de banco de dados caso não exista.
        Args:
            nome (str): Nome do banco de dados.
        Returns:
            bool: True se o banco de dados foi criado ou já existia, False caso contrário.
        
        OBS: Script para SQL Server
        """
        query = f"""
        IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{self.database}')
        CREATE DATABASE {self.database}
        """
        conn = self._conectar_master()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao criar banco de dados: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
