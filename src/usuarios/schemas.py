from pydantic import BaseModel, ConfigDict

class UsuarioSchema(BaseModel):
    cedula: int

class UsuarioCreateSchema(UsuarioSchema):
    model_config = ConfigDict(
        from_attributes=True,
    )

    nombre: str
    apellido: str
    cedula: int