
from models.database import SqlServer


class FalconDB:
    def __init__(self):
        self.banco = SqlServer("falcon")


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

class ThinkimDB:
    def __init__(self):
        self.banco = SqlServer("thinkim")
