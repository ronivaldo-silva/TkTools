from sqlalchemy import select
from models.database import SqlServer
from models.models import Hardware, Entity, EntityIdentifier, Base

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

class ThinkimDB:
    def __init__(self):
        self.banco = SqlServer("thinkim")
        self.engine = self.banco.get_engine()
        self.is_connected = self.engine is not None
        if self.is_connected:
            self._create_tables_if_not_exists()

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
                Base.metadata.create_all(engine)
                print("Tabelas do ThinkimDB verificadas/criadas com sucesso (SQLAlchemy).")
            except Exception as e:
                print(f"Erro ao criar tabelas no banco de dados thinkim: {e}")
