from fastapi import WebSocket
from conf.settings import redis_instance
from conf.authentication import auth
from typing import TypedDict, Optional
from datetime import datetime, timezone
import json

class WebsocketList(TypedDict):
    usuario_id: Optional[WebSocket]
    microcontrolador: Optional[WebSocket]
    websocket: WebSocket

conexiones_activas: list[WebsocketList] = []

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

        fecha_hora_actual = datetime.now(timezone.utc).isoformat()

        datos_a_guardar = {
            "sensor": sensor,
            "valor": valor,
            "timestamp": fecha_hora_actual
        }
        
        await self.redis.lpush("sensor_data", json.dumps(datos_a_guardar))
        print(datos_a_guardar)

        

    
    