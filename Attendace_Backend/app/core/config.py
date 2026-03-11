"""Application configuration with environment-based settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from project root (parent of backend/) or backend/
_backend_dir = Path(__file__).resolve().parent.parent.parent  # backend/
_env_path = _backend_dir.parent / ".env"  # project root
if not _env_path.exists():
    _env_path = _backend_dir / ".env"  # fallback: backend/.env


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_env_path if _env_path.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Attendance Tracking System"
    APP_VERSION: str = "1.0.0"
    SCHOOL_NAME: str = "XYZ School"
    AUTO_LOW_ATTENDANCE_ALERTS: bool = True
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    # SECRET_KEY or JWT_SECRET (Render compatibility)
    SECRET_KEY: str = "change-me-in-production-use-strong-secret"

    def get_secret_key(self) -> str:
        """Prefer JWT_SECRET for Render; fallback to SECRET_KEY."""
        return os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or self.SECRET_KEY

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Fast2SMS (SMS alerts)
    FAST2SMS_API_KEY: str = ""

    # ML - buffalo_l for best accuracy (~91%); buffalo_s if 512MB RAM (Render: use 1GB+ for buffalo_l)
    INSIGHTFACE_MODEL: str = "buffalo_l"  # buffalo_l ~326MB best accuracy, buffalo_s ~160MB for 512MB
    PRELOAD_ML_ENGINES: bool = False
    # Thresholds - tuned for clear identification
    FACE_RECOGNITION_THRESHOLD: float = 0.55  # Match threshold - lower = more matches (buffalo_l accurate)
    FACE_RECOGNITION_THRESHOLD_REALTIME: float = 0.55  # Same for real-time
    ENROLLMENT_DUPLICATE_THRESHOLD: float = 0.68  # Reject if face matches existing (stricter: 0.68 catches more duplicates)
    LIVENESS_BLINK_THRESHOLD: float = 0.2
    MAX_FACES_DETECT: int = 3
    EMBEDDING_DIM: int = 512
    DETECTION_SCORE_MIN: float = 0.45  # Accept more detections for registration
    # Enrollment: permissive - accept varied lighting, angles, webcam quality
    ENROLLMENT_DETECTION_SCORE_MIN: float = 0.35  # Very permissive for live environment
    ENROLLMENT_MIN_BLUR_VARIANCE: float = 30.0  # Accept webcam blur (Laplacian variance)
    ENROLLMENT_MIN_FACE_PIXELS: int = 50 * 50  # Min 50x50 face (small faces in frame ok)
    MIN_BLUR_VARIANCE: float = 50.0  # Laplacian - permissive for live
    DET_SIZE: int = 960  # Larger = better detection (960 for accuracy; 640 for 512MB RAM)
    REALTIME_DET_SIZE: int = 640  # Unused with single engine
    REALTIME_DET_THRESH: float = 0.35  # Lower = detect more faces
    EMBEDDING_CACHE_REFRESH_SEC: int = 300  # 5 minutes

    # Security
    RATE_LIMIT_PER_MINUTE: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Redis (optional)
    REDIS_URL: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
