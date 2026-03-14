
from models.database import SqlServer

class FalconDB:
    def __init__(self):
        self.banco = SqlServer("falcon")
        self.banco.create_database()
        self.conn = None
        self.is_connected = False
        self._try_start_db()

    def _conectar(self):
        try:
            if self.is_connected:
                return self.conn
            else:
                self.conn = self.banco._conectar()
                self.is_connected = True
                return self.conn
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados falcon: {e}")
            self.is_connected = False
            return None

    def _try_start_db(self):
        """Tenta conectar ao banco de dados e criar as tabelas se não existirem."""
        try:
            self._conectar()
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados falcon: {e}")
            self.is_connected = False
            return False

    def _get_hardware(self, hardwaretype:int = None):
        """Busca o hardware do banco de dados.
        
        Args:
            hardwaretype (int): Tipo de hardware a ser buscado.
            10 = DECs (Equipamento OTIs para chamada de elevadores)
            7 = Faciais hikvision (Usados )
        
        Returns:
            list: Lista de dicionários contendo os dados do hardware.
        """
        script = "SELECT "\
                "[HardwareId],"\
                "[Name],"\
                "[HardwareType],"\
                "[IP],"\
                "[ControllerMode],"\
                "[Priority],"\
                "[Sync] "\
            "FROM dbo.hardware"
        if hardwaretype:
            script += f" WHERE HardwareType = {hardwaretype}"
        return self.banco.consultar(script)

    def _get_pessoas(self, isblocked:bool = False, has_face:bool = True):
        if has_face:
            filter_identifier = "INNER JOIN DBO.entityidentifier AS EI ON EI.EntityEntityId = E.EntityId"
        else:
            filter_identifier = ""

        script = f"""
        SELECT
            [E].[EntityId],
            [E].[Name],
            [E].[GroupGroupId],
            [E].[EntityType],
            [E].[LocationLocationId],
            [E].[UserUserId],
            [E].[IsBlocked],
            [E].[IsRandomBlocked],
            [E].[CreatedAt],
            [E].[BlockedEnd],
            [E].[BlockedStart],
            [E].[IsTempBlocked]
        FROM dbo.entity AS E
        {filter_identifier}

        WHERE E.EntityType = 1
        """
        script += f"AND E.IsBlocked = {int(isblocked)}"
        return self.banco.consultar(script)

class ThinkimDB:
    def __init__(self):
        self.banco = SqlServer("thinkim")
        self.conn = None
        self.is_connected = False
        self.try_start_db()

    def _conectar(self):
        try:
            if self.is_connected:
                return self.conn
            else:
                self.conn = self.banco._conectar()
                self.is_connected = True
                return self.conn
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados thinkim: {e}")
            self.is_connected = False
            return None

    def try_start_db(self):
        """Tenta conectar ao banco de dados e criar as tabelas se não existirem."""
        try:
            self._conectar()
            self._create_tables_if_not_exists()
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados thinkim: {e}")
            self.is_connected = False
            return False

    def _create_tables_if_not_exists(self):
        script = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='usuarios_faciais' AND xtype='U')
        CREATE TABLE usuarios_faciais (
            HardwareId INT,
            employeeNo VARCHAR(50),
            name VARCHAR(150),
            userType VARCHAR(50),
            beginTime DATETIME,
            endTime DATETIME,
            doorRight VARCHAR(50),
            numOfCard INT,
            numOfFace INT,
            PRIMARY KEY (HardwareId, employeeNo)
        )
        """
        self.banco._executar(script)

        script_elevators = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='log_elevators' AND xtype='U')
        BEGIN
            CREATE TABLE log_elevators (
                id INT IDENTITY(1,1) PRIMARY KEY,
                datahora DATETIME,
                dados NVARCHAR(MAX)
            )
        END
        """
        self.banco._executar(script_elevators)

        script_integrations = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='log_integrations' AND xtype='U')
        BEGIN
            CREATE TABLE log_integrations (
                id INT IDENTITY(1,1) PRIMARY KEY,
                datahora DATETIME,
                evento NVARCHAR(255),
                dados NVARCHAR(MAX)
            )
        END
        """
        self.banco._executar(script_integrations)
