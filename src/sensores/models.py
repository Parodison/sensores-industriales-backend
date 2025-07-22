from conf.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, String
from datetime import date

class Microcontrolador(Base):
    __tablename__ = 'microcontroladores'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha_registro: Mapped[date] = mapped_column(Date, default=date.today)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)