import os
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from models.models import SqliteBase, Camera
from models.hikvision_isapi import HikvisionClient
from dotenv import load_dotenv

load_dotenv()

# Caminho absoluto para garantir o local correto do banco
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
DB_PATH = os.path.join(TEMP_DIR, "cameras.db")

class SqliteControl:
    def __init__(self):
        # Garante a existência do diretório temporário
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
            
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
        # Cria as tabelas se não existirem
        SqliteBase.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logging.info(f"SQLite conectado em: {DB_PATH}")

    def save_camera(self, ip: str, nome: str, user: str, password: str, serial_number: str, mac: str):
        """Salva ou atualiza os dados da câmera no SQLite."""
        session = self.Session()
        try:
            stmt = select(Camera).where(Camera.ip == ip)
            camera = session.execute(stmt).scalar_one_or_none()
            
            if camera:
                camera.nome = nome
                camera.user = user
                camera.password = password
                camera.serial_number = serial_number
                camera.mac = mac
            else:
                camera = Camera(
                    ip=ip,
                    nome=nome,
                    user=user,
                    password=password,
                    serial_number=serial_number,
                    mac=mac
                )
                session.add(camera)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logging.error(f"Erro ao salvar câmera {ip} no SQLite: {e}")
            return False
        finally:
            session.close()

    def get_all_cameras(self):
        """Retorna todas as câmeras cadastradas no SQLite."""
        session = self.Session()
        try:
            stmt = select(Camera)
            return session.execute(stmt).scalars().all()
        except Exception as e:
            logging.error(f"Erro ao obter câmeras do SQLite: {e}")
            return []
        finally:
            session.close()

    def normalize_and_save_all_cameras(self, hardwares_list) -> tuple[int, int]:
        """
        Normaliza e salva os dados de todas as câmeras no SQLite,
        unindo informações do banco de dados (IP, Nome, user, password)
        e coletados do equipamento por ISAPI (Número de Série - 9 últimos dígitos, MAC).
        """
        default_user = os.getenv("HIK_USER", "admin")
        default_pass = os.getenv("HIK_PASS", "@ThinKim2020")
        
        success_count = 0
        failure_count = 0
        
        for hw in hardwares_list:
            facial = hw.facial
            ip = facial.ip
            nome = facial.nome_db
            
            # Obtém credenciais das câmeras (prioriza as configuradas no cliente isapi, depois o .env)
            user = getattr(facial.isapi, 'username', default_user)
            password = getattr(facial.isapi, 'password', default_pass)
            
            mac = facial.mac_address
            serial_number = ""
            
            try:
                # Efetua requisição ISAPI para obter os dados do hardware em tempo real
                device_info = facial.isapi.get_device_info()
                if device_info:
                    mac = device_info.get("macAddress", mac)
                    full_serial = device_info.get("serialNumber")
                    if full_serial:
                        # Pega os 9 últimos dígitos do número de série
                        serial_number = full_serial[-9:]
            except Exception as e:
                logging.warning(f"Não foi possível obter dados ISAPI de {ip}: {e}")
            
            # Garante que None não vá ao banco
            if not mac:
                mac = ""
            if not serial_number:
                serial_number = ""
                
            # Grava no SQLite usando SQLAlchemy
            saved = self.save_camera(
                ip=ip,
                nome=nome,
                user=user,
                password=password,
                serial_number=serial_number,
                mac=mac
            )
            
            if saved:
                success_count += 1
                # Se for bem sucedido, atualiza os atributos no objeto facial
                if mac:
                    facial.mac_address = mac
            else:
                failure_count += 1
                
        return success_count, failure_count
