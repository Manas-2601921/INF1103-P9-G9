"""Environment configuration package for the dashboard application factory."""

from dashboard.config.base_config import BASE_DIR, DATA_DIR, Config
from dashboard.config.dev_config import DevConfig
from dashboard.config.test_config import TestConfig

__all__ = ["BASE_DIR", "DATA_DIR", "Config", "DevConfig", "TestConfig"]
