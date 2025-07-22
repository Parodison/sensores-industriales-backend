from conf.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer

class Usuario(Base):
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cedula: Mapped[int] = mapped_column(unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(nullable=False)
    apellido: Mapped[str] = mapped_column(nullable=False)

 