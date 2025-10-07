import asyncio
from io import BytesIO
from fastapi import Request, WebSocket
from conf.settings import redis_instance
from conf.authentication import auth
from typing import TypedDict, Optional
from datetime import datetime, timezone
import json
from src.sensores.models import Monitoreo
from conf.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from playwright.async_api import async_playwright
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from conf.utils import imagen_base64
import qrcode

jinja2_environment = Environment(loader=FileSystemLoader("templates"))

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
        print(f"Se ha registrado el valor {registrar_monitoreo.valor} para el sensor {registrar_monitoreo.sensor} con fecha {registrar_monitoreo.fecha_lectura.astimezone().strftime('%d/%m/%Y %H:%M:%S')}")

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
            if not registros_estadisticos:
                query_estadistico = (
                    select(Monitoreo)
                    .order_by(Monitoreo.fecha_lectura.asc())
                    
                )
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
    
    async def obtener_reporte(self, session: AsyncSession):
        template_reporte = jinja2_environment.get_template("reporte.html")
        directorio_template = Path().parent.parent.resolve() / "templates"
        
        query = (
            select(Monitoreo)
            .limit(100)
            .order_by(Monitoreo.fecha_lectura.desc())
        )

        result = await session.execute(query)
        datos_reporte = result.scalars().all()
        for reporte in datos_reporte:
            reporte.fecha_lectura = reporte.fecha_lectura.astimezone().strftime("%H:%M:%S")
            if reporte.sensor == "aire":
                reporte.sensor = f"{reporte.sensor.capitalize()} (MQ135)"
                reporte.valor = f"{reporte.valor} ppm"
            elif reporte.sensor == "polvo":
                reporte.sensor = f"{reporte.sensor.capitalize()} (DSM501B)"
                reporte.valor = f"{reporte.valor} µg/m³"
            elif reporte.sensor == "temperatura":
                reporte.sensor = f"{reporte.sensor.capitalize()} (DHT11)"
                reporte.valor = f"{reporte.valor} C°"
            elif reporte.sensor == "humedad":
                reporte.sensor = f"{reporte.sensor.capitalize()} (DHT11)"
                reporte.valor = f"{reporte.valor} %"

        context = {
            "reportes": datos_reporte ,
            "eik_logo": imagen_base64(directorio_template / "eik-logo.png"),
            "ctn_logo": imagen_base64(directorio_template / "ctn-logo.png"),
            "solaris_logo": imagen_base64(directorio_template / "solaris-logo.png")
        }
    
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(template_reporte.render(context))
            await page.wait_for_load_state("networkidle")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
            await browser.close()
            
            pdf_io = BytesIO(pdf_bytes)
        return pdf_io
    
    async def generar_qr(self, request: Request):
        url = request.base_url

        qr = qrcode.make(f"{url}api/sensores/obtener-reporte")
        qr_bytes = BytesIO()
        qr.save(qr_bytes, format="PNG")
        qr_bytes.seek(0)
        return qr_bytes

