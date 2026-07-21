"""Configuration loaded from env vars."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    SITE_URL: str = os.getenv("SITE_URL", "https://donttalk.vercel.app")
    SITE_NAME: str = os.getenv("SITE_NAME", "donttalk")

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.getenv(
            "ALLOWED_ORIGINS",
            "https://donttalk.vercel.app,http://localhost:4321",
        ).split(",") if o.strip()
    ]

    CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./data/chroma")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
