from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "tree-education-datacollecting"
    api_prefix: str = "/api/v1"
    ocr_engine: str = "mock"
    internal_api_token: str = ""
    max_image_mb: int = 20

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
