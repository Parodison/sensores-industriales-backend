from decouple import config

secret_key: str = config("SECRET_KEY", default="default_secret_key")
database_url: str = config("DATABASE_URL")
