from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = ""
    DB_PORT: int = 3000
    DB_USER: str = ""
    DB_PASS: str = ""
    DB_NAME: str = ""

    OAUTH_CHECK_URL: str = ""
    STORAGE_URL: str = ""

    DEBUG: bool = False

    @property
    def database_url(self):
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
