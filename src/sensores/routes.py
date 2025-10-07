from datetime import date
from fastapi import APIRouter, Depends, WebSocket, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from src.sensores.sensor_handler import SensorHandler
from conf.authentication import auth
from sqlalchemy.ext.asyncio import AsyncSession
from conf.database import get_session
from conf import env
import jwt
from src.sensores.models import Microcontrolador
from starlette.websockets import WebSocketDisconnect
from src.sensores.sensor_handler import conexiones_activas


router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        sensor_handler = SensorHandler(websocket)
        await sensor_handler.connect()
    except WebSocketDisconnect:
        for conexion in conexiones_activas:
            if conexion["websocket"] == websocket:
                conexiones_activas.remove(conexion)

@router.post("/crear-token-microcontrolador")
async def crear_token_microcontrolador(db: AsyncSession = Depends(get_session)):
    microcontrolador = await db.execute(select(Microcontrolador))
    microcontrolador = microcontrolador.scalars().first()
    if not microcontrolador:
        token = jwt.encode(
            {"microcontrolador": "Sensor Industrial"},
            env.secret_key,
            algorithm=auth.algorithm
        )
        microcontrolador = Microcontrolador(
            fecha_registro=date.today(),
            token=token
        )
        db.add(microcontrolador)
        await db.commit()
        await db.refresh(microcontrolador)
        return {"token": microcontrolador.token}
    
    return {"token": microcontrolador.token}

@router.get("/obtener-historial-sensor")
async def obtener_historial_sensor(
    sensor: str = Query("aire", description="Nombre del sensor"),
    db: AsyncSession = Depends(get_session)
):
    sensor_handler = SensorHandler()
    datos_sensor = await sensor_handler.obtener_historial_monitoreo(sensor)
    return datos_sensor

@router.get("/obtener-reporte")
async def obtener_reporte(
    request: Request,
    db: AsyncSession = Depends(get_session),
    qr: bool = Query(False),
    
):
    sensor_handler = SensorHandler()
    if qr:
        qr_image = await sensor_handler.generar_qr(request)
        return StreamingResponse(
            qr_image,
            media_type="image/png"
        )

    pdf = await sensor_handler.obtener_reporte(db)
    
    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=reporte.pdf"}
    )