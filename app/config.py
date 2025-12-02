from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_title: str
    database_url: str
    openai_api_key: str
    huggingfacehub_api_token: str
    files: str

    class Config:
        env_file = ".env"


settings = Settings()
