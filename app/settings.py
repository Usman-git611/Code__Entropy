from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./learndna.db'
    secret_key: str = 'change-this-development-secret'
    access_token_minutes: int = 480
    ai_provider: str = 'demo'
    openai_api_key: str = ''
    gemini_api_key: str = ''
    ai_model: str = 'gpt-5'
    ollama_host: str = 'http://127.0.0.1:11434'
    ollama_model: str = 'llama3.2:1b'
    local_compiler_enabled: bool = False

settings = Settings()
