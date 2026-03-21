from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
from datetime import datetime

class FalconBase(DeclarativeBase):
    pass

class ThinkimBase(DeclarativeBase):
    pass

# ---- Banco de Dados: FALCON ----

class Hardware(FalconBase):
    __tablename__ = 'hardware'
    __table_args__ = {'schema': 'dbo'}

    HardwareId: Mapped[int] = mapped_column(Integer, primary_key=True)
    Name: Mapped[str] = mapped_column(String(255))
    HardwareType: Mapped[int] = mapped_column(Integer)
    IP: Mapped[str] = mapped_column(String(50))
    ControllerMode: Mapped[int] = mapped_column(Integer)
    Priority: Mapped[int] = mapped_column(Integer)
    Sync: Mapped[int] = mapped_column(Integer)

class Entity(FalconBase):
    __tablename__ = 'entity'
    __table_args__ = {'schema': 'dbo'}

    EntityId: Mapped[int] = mapped_column(Integer, primary_key=True)
    Name: Mapped[str] = mapped_column(String(255))
    GroupGroupId: Mapped[int] = mapped_column(Integer)
    EntityType: Mapped[int] = mapped_column(Integer)
    LocationLocationId: Mapped[int] = mapped_column(Integer)
    UserUserId: Mapped[int] = mapped_column(Integer)
    IsBlocked: Mapped[bool] = mapped_column(Boolean)
    IsRandomBlocked: Mapped[bool] = mapped_column(Boolean)
    CreatedAt: Mapped[datetime] = mapped_column(DateTime)
    BlockedEnd: Mapped[Optional[datetime]] = mapped_column(DateTime)
    BlockedStart: Mapped[Optional[datetime]] = mapped_column(DateTime)
    IsTempBlocked: Mapped[bool] = mapped_column(Boolean)

class EntityIdentifier(FalconBase):
    __tablename__ = 'entityidentifier'
    __table_args__ = {'schema': 'dbo'}

    EntityEntityId: Mapped[int] = mapped_column(Integer, ForeignKey("dbo.entity.EntityId"), primary_key=True)

# ---- Banco de Dados: THINKIM ----

class UsuariosFaciais(ThinkimBase):
    __tablename__ = 'usuarios_faciais'
    
    HardwareId: Mapped[int] = mapped_column(Integer, primary_key=True)
    employeeNo: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(150))
    userType: Mapped[Optional[str]] = mapped_column(String(50))
    beginTime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    endTime: Mapped[Optional[datetime]] = mapped_column(DateTime)
    doorRight: Mapped[Optional[str]] = mapped_column(String(50))
    numOfCard: Mapped[Optional[int]] = mapped_column(Integer)
    numOfFace: Mapped[Optional[int]] = mapped_column(Integer)

class LogElevators(ThinkimBase):
    __tablename__ = 'log_elevators'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datahora: Mapped[Optional[datetime]] = mapped_column(DateTime)
    dados: Mapped[str] = mapped_column(String)

class LogIntegrations(ThinkimBase):
    __tablename__ = 'log_integrations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datahora: Mapped[Optional[datetime]] = mapped_column(DateTime)
    evento: Mapped[Optional[str]] = mapped_column(String(255))
    dados: Mapped[str] = mapped_column(String)
