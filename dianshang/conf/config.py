from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parents[2] / ".env"


class Settings(BaseSettings):
    # LLM 配置
    llm_model: str
    llm_base_url: str
    llm_api_key: str
    # 电商业务服务地址
    commerce_api_base_url: str
    # 数据库
    database_url: str
    # 服务监听
    app_host: str
    app_port: int

    model_config = SettingsConfigDict(env_file=ENV_FILE)


settings = Settings()

if __name__ == '__main__':
    print(settings.llm_model)
