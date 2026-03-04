from models.hikvision_isapi import HikvisionClient
from controls.bancos import FalconDB

class Facial:
    def __init__(self, nome, ip):
        self.nome_db = nome
        self.ip = ip
        self.nome_device = None
        self.pessoas = None
        self.faces = None
        self.modelo = None
        self.firmware = None
        self.mac_address = None
        self.online = False
        
        self.isapi = HikvisionClient(ip, 'admin', '@ThinKim2020')

    def load_info(self):
        """Atualiza os atributos da classe com informações do equipamento."""
        try:
            device_info = self.isapi.get_device_info()
        except Exception as e:
            self.online = False
            print(f"Error getting device info for {self.ip}: {e}")
            raise e
        finally:
            self.online = True
        
        try:
            user_info = self.isapi.get_user_info_count()
            
            self.nome_device = device_info.get("deviceName")
            self.pessoas = user_info.get("userNumber")
            self.faces = user_info.get("bindFaceUserNumber")
            self.modelo = device_info.get("model")
            self.firmware = device_info.get("firmwareVersion") + device_info.get("firmwareReleasedDate").replace("build", " ")
            self.mac_address = device_info.get("macAddress")
            self.online = True
        except Exception as e:
            print(f"Error getting user info for {self.ip}: {e}")
            raise e

    def reboot(self):
        self.isapi.reboot_device()

    def get_people_count(self):
        self.pessoas = self.isapi.get_user_count()
        return self.pessoas
    
    def get_device_info(self):
        return self.isapi.get_device_info()
    
    