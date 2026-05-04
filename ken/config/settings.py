from pathlib import Path

from pydantic_settings import BaseSettings

from ken.config.modes import ModeName


class KenConfig(BaseSettings):
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2:3b"
    default_mode: ModeName = "linux"
    request_timeout_s: float = 60.0
    ollama_keep_alive: str = "15m"

    # CPU-safe defaults; override with KEN_OLLAMA_NUM_GPU and KEN_OLLAMA_NUM_THREAD as needed.
    ollama_num_gpu: int = 0
    ollama_num_thread: int = 6

    memory_recent_window: int = 12
    memory_summary_trigger: int = 40
    memory_keep_after_summary: int = 12
    memory_summary_char_limit: int = 2200

    data_dir: Path = Path.home() / ".local" / "share" / "ken"

    class Config:
        env_prefix = "KEN_"


config = KenConfig()
config.data_dir.mkdir(parents=True, exist_ok=True)
