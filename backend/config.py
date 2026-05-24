from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    voice_debrief_host: str = '0.0.0.0'
    voice_debrief_port: int = 8787
    public_base_url: str = 'http://localhost:8787'
    debrief_output_dir: Path = Path('/mnt/c/Users/Trevis/Documents/Phone/debriefs')

    hermes_api_base: str = 'http://127.0.0.1:8642/v1'
    hermes_api_key: str = 'change-me-local-dev'
    hermes_model: str = 'hermes-agent'

    stt_provider: str = 'local'
    whisper_model: str = 'small'
    whisper_device: str = 'cuda'
    whisper_compute_type: str = 'float16'
    whisper_language: str = 'en'
    whisper_vad_min_silence_ms: int = 700
    endpoint_min_speech_seconds: float = 0.55
    endpoint_min_text_chars: int = 8

    edge_tts_voice: str = 'en-US-AriaNeural'

    # Beta multi-user scaffolding
    app_env: str = 'local'
    multi_user_mode: bool = False
    beta_signups_open: bool = True
    max_beta_users: int = 3
    allowed_emails: str = ''

    supabase_url: str = 'https://YOUR_PROJECT.supabase.co'
    supabase_anon_key: str = 'YOUR_ANON_KEY'
    supabase_service_role_key: str = 'YOUR_SERVICE_ROLE_KEY'
    supabase_jwt_audience: str = 'authenticated'


@lru_cache
def get_settings() -> Settings:
    return Settings()
