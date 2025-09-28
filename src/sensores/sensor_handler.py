import asyncio
from fastapi import WebSocket
from conf.settings import redis_instance
from conf.authentication import auth
from typing import TypedDict, Optional
from datetime import datetime, timezone
import json
from src.sensores.models import Monitoreo
from conf.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

class WebsocketList(TypedDict):
    usuario_id: Optional[WebSocket]
    microcontrolador: Optional[WebSocket]
    websocket: WebSocket

conexiones_activas: list[WebsocketList] = []

class Datasets(TypedDict):
    data: list[str]

class LineChartStruct(TypedDict):
    labels: list[str]
    datasets: list[Datasets]


class SensorHandler:
    def __init__(self, websocket: WebSocket = None):
        self.redis = redis_instance
        self.websocket = websocket


    async def connect(self):

        tipo = self.websocket.query_params.get("tipo")
        if tipo not in ["usuario", "microcontrolador"]:
            await self.websocket.close(code=4000, reason="Tipo no permitido")
            return
        
        token = self.websocket.query_params.get("token")
        match tipo:
            case "usuario":
                verify_user = auth.verify_access_token(token)
                if not verify_user:
                    await self.websocket.close(code=4001, reason="Token de acceso inválido para el usuario")
                    return
                await self.websocket.accept()
                conexiones_activas.append({
                    "usuario_id": verify_user["id"],
                    "websocket": self.websocket,
                })
                print(conexiones_activas)

            case "microcontrolador":
                verify_microcontrolador = auth.verify_access_token(token)
                if not verify_microcontrolador:
                    await self.websocket.close(code=4002, reason="Token de acceso inválido para el microcontrolador")
                    return
                await self.websocket.accept()
                conexiones_activas.append({
                    "microcontrolador": True,
                    "websocket": self.websocket,
                })
                print("Microcontrolador conectado")
        
        while True:
            await self.despachar()

    async def despachar(self):
        data = await self.websocket.receive_json()
        operacion = data.get("operacion")
        if not operacion:
            await self.websocket.send_json({"error": "Operación no especificada"})
            return
        
        match operacion:
            case "enviar_datos_sensor":
                await self.enviar_datos_sensor(data)
            
    async def enviar_datos_sensor(self, data: dict):
        for conexion in conexiones_activas:
            if conexion["websocket"] == self.websocket:
                if not "microcontrolador" in conexion:
                    await self.websocket.send_json({"error": "Conexión no autorizada para enviar datos de sensores"})
                    return
        
        if not data.get("datos"):
            await self.websocket.send_json({"error": "Datos de sensores no especificados"})
            return
        
        for conexion in conexiones_activas:
            if conexion.get("usuario_id") is not None:
                await conexion["websocket"].send_json(data)
        await self.registrar_monitoreo(data)
        return
    
    async def registrar_monitoreo(self, data: dict):
        datos = data["datos"]
        sensor = datos["sensor"]
        valor = datos["valor"]

        fecha_hora_actual = datetime.now()
        
        registrar_monitoreo = Monitoreo()
        registrar_monitoreo.sensor = sensor
        registrar_monitoreo.fecha_lectura = fecha_hora_actual
        registrar_monitoreo.valor = valor
        
        async with AsyncSession(engine) as session:
            session.add(registrar_monitoreo)
            await session.commit()
            await session.refresh(registrar_monitoreo)  
        print(f"Se ha registrado el valor {registrar_monitoreo.valor} para el sensor {registrar_monitoreo.sensor} con fecha {registrar_monitoreo.fecha_lectura.astimezone().strftime("%d/%m/%Y %H:%M:%S")}")

    async def obtener_historial_monitoreo(self, sensor: str):
        line_chart: LineChartStruct = {
            "labels": [],
            "datasets": [{
                "data": []
            }]
        }
        

        hoy = datetime.now().date()
        hora_inicial = datetime.combine(hoy, datetime.min.time())
        hora_final = datetime.combine(hoy, datetime.max.time())
        
        query = (
            select(Monitoreo)
            .where(Monitoreo.sensor == sensor)
            .order_by(Monitoreo.fecha_lectura.desc())
            .limit(100)
        )

        query_estadistico = (
            select(Monitoreo)
            .where(and_(
                Monitoreo.fecha_lectura >= hora_inicial,
                Monitoreo.fecha_lectura <= hora_final
            ))
        )
        

        async with AsyncSession(engine) as session:
            exec = await session.execute(query)
            resultados_generales = exec.scalars().all()
            for resultado in resultados_generales:
                
                
                resultado.fecha_lectura = resultado.fecha_lectura.astimezone()

            result_estadistico = await session.execute(query_estadistico)
            registros_estadisticos = result_estadistico.scalars().all()
            
            hora_leida = 0
            minuto_leido = 0
            segundo_leido = 0
            for registro in registros_estadisticos:
                horario_lectura = registro.fecha_lectura.astimezone()
                hora = horario_lectura.hour
                minuto = horario_lectura.minute
                segundo = horario_lectura.second
                
                
                if hora_leida != hora:
                    hora_leida = hora
                    line_chart["labels"].append(f"{str(int(hora)).zfill(2)}:{str(int(minuto)).zfill(2)}")
                    line_chart["datasets"][0]["data"].append(registro.valor)

            

            
            

        return {
            "mensaje": "Datos de sensor obtenidos",
            "line_chart": line_chart,
            "datos": resultados_generales,
            
        }   
    async def obtener_historial_estadistico():
        pass