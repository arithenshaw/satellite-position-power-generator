from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Solar Panel Power Simulator API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    OUTPUT_DIR: str = "outputs"
    MAX_SIMULATION_DURATION_HOURS: int = 24

    DATABASE_URL:str = "sqlite:///./simulations.db"
    
    class Config:
        env_file = ".env"

settings = Settings()