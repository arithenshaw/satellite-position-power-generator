from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Solar Panel Power Simulator API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # File storage
    OUTPUT_DIR: str = "outputs"
    MAX_SIMULATION_DURATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"

settings = Settings()