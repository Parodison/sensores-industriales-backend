from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from conf.database import get_session
from conf.authentication import auth
from sqlalchemy.ext.asyncio import AsyncSession
from src.usuarios.models import Usuario
from src.usuarios.schemas import UsuarioSchema, UsuarioCreateSchema


router = APIRouter()

@router.post("/iniciar-sesion")
async def iniciar_sesion(data: UsuarioSchema, db: AsyncSession = Depends(get_session)):
    try:
        
        result = await db.execute(select(Usuario).where(Usuario.cedula == data.cedula))
        usuario = result.scalars().first()
        
        if not usuario:
            return JSONResponse(
                status_code=404,
                content={"mensaje": "Usuario no encontrado"}
            )
        
        access_token = auth.create_access_token({"id": usuario.id})
        refresh_token = auth.create_refresh_token({"id": usuario.id})

        return JSONResponse(
            status_code=200,
            content={
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"mensaje": f"Error al iniciar sesión: {str(e)}"}
        )
    
@router.post("/crear-usuario")
async def crear_usuario(data: UsuarioCreateSchema, db: AsyncSession = Depends(get_session)):
    try:
        nuevo_usuario = Usuario(
            cedula= data.cedula,
            nombre=data.nombre,
            apellido=data.apellido
        )
        db.add(nuevo_usuario)
        await db.commit()
        await db.refresh(nuevo_usuario)

        return JSONResponse(
            status_code=201,
            content={"mensaje": "Usuario creado exitosamente", "usuario": UsuarioCreateSchema.model_validate(nuevo_usuario).model_dump()}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"mensaje": f"Error al crear usuario: {str(e)}"}
        )   