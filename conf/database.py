from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from conf.env import database_url

engine = create_async_engine(database_url, echo=False, future=True)

async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async_session: AsyncSession = async_session_maker()

async def get_session():
    async with async_session_maker() as session:
        yield session

class Base(DeclarativeBase):
    pass