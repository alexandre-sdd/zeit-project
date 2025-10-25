"""
Smoke tests for the Zeit project structure.
"""
from app.core import settings


def test_settings_load():
    config = settings.get_settings()
    assert config.app_name
