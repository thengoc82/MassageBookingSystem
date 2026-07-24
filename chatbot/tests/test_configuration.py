"""Tests for Phase 0 — Configuration"""
import os

from app.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.session_expiration_seconds == 3600

def test_settings_env_prefix():
    os.environ["CHATBOT_REDIS_URL"] = "redis://custom:6379/1"
    os.environ["CHATBOT_SESSION_EXPIRATION_SECONDS"] = "1800"
    
    settings = Settings()
    assert settings.redis_url == "redis://custom:6379/1"
    assert settings.session_expiration_seconds == 1800