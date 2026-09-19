import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # We default to an empty string so the module can be imported without raising errors immediately.
    # Validation is executed when the application starts or when APIs are called.
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    jarvis_api_key: str = Field(default="jarvis_secure_key_123", validation_alias="JARVIS_API_KEY")
    llm_model: str = Field(default="qwen/qwen3.8-27b", validation_alias="LLM_MODEL")
    stt_model: str = Field(default="whisper-large-v3-turbo", validation_alias="STT_MODEL")
    tts_voice: str = Field(default="en-US-AnaNeural", validation_alias="TTS_VOICE")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        # Look for a .env file in the current working directory or parents
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_config(self):
        """Validate that all required settings are present."""
        if not self.groq_api_key or self.groq_api_key == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY is not set or is using the default placeholder value. "
                "Please configure a valid Groq API key in your '.env' file."
            )

# Create a single instance to share across modules
settings = Settings()
