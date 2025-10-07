from fastapi import FastAPI
from fastapi.responses import FileResponse
from src.usuarios.routers import router as usuarios_router
from conf.database import engine, Base
from src.sensores.routes import router as sensores_router
import os

app = FastAPI()

@app.get("/descargar-apk")
async def descargar_apk():
    apk_path = os.path.join(os.getcwd(), "apk", "solaris.apk")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="solaris.apk"
    )

app.include_router(usuarios_router, prefix="/api/usuarios", tags=["usuarios"])
app.include_router(sensores_router, prefix="/api/sensores", tags=["sensores"])

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O usa ["http://192.168.100.31"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)