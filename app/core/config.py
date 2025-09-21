# from pydantic_settings import BaseSettings, SettingsConfigDict
# from pathlib import Path
# from pydantic import Field

# BASE_DIR = Path(__file__).resolve().parent.parent.parent

# # class Settings(BaseSettings):

# #     model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")

# #     HF_TOKEN: str = Field(validation_alias="hf_token")

# #     GROQ_API_KEY: str = Field(validation_alias="groq_api_key")

# #     SPITCH_API_KEY: str = Field(validation_alias="spitch_api_key")



# # settings = Settings()