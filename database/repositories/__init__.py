"""
Репозитории для работы с БД
Разделение логики доступа к данным по сущностям
"""
from database.repositories.employee_repository import EmployeeRepository
from database.repositories.material_repository import MaterialRepository
from database.repositories.router_repository import RouterRepository
from database.repositories.connection_repository import ConnectionRepository
from database.repositories.snr_box_repository import SNRBoxRepository
from database.repositories.onu_repository import ONURepository
from database.repositories.media_converter_repository import MediaConverterRepository
from database.repositories.sfp_module_repository import SFPModuleRepository
from database.repositories.access_repository import AccessRepository
from database.repositories.admin_repository import AdminRepository

__all__ = [
    "EmployeeRepository",
    "MaterialRepository",
    "RouterRepository",
    "ConnectionRepository",
    "SNRBoxRepository",
    "ONURepository",
    "MediaConverterRepository",
    "SFPModuleRepository",
    "AccessRepository",
    "AdminRepository",
]
