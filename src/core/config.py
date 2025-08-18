from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Fast API - Sales"
    app_version: str = "0.0.1"
    database_url: str
    
    # pylint: disable=too-few-public-methods
    class Config:
        env_file = ".env"
        
settings = Settings()