from pathlib import Path
from pydantic_settings import BaseSettings

class KenConfig(BaseSettings):
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"
    data_dir: Path = Path.home() / ".local" / "share" / "ken"
    
    class Config:
        env_prefix = "KEN_"

config = KenConfig()
config.data_dir.mkdir(parents=True, exist_ok=True)
