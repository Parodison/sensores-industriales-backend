from conf.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, String, DateTime, Float
from datetime import date, datetime, timezone

class Microcontrolador(Base):
    __tablename__ = 'microcontroladores'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_registro: Mapped[date] = mapped_column(Date, default=date.today)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

class Monitoreo(Base):
    __tablename__ = "monitoreos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sensor: Mapped[str] = mapped_column(String, nullable=False)
    fecha_lectura: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False
    )
    valor: Mapped[float | int] = mapped_column(Float, nullable=False)