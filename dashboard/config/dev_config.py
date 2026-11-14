"""Local development configuration."""

from dashboard.config.base_config import Config


class DevConfig(Config):
    """Local development: verbose errors on, CSRF still enabled."""

    DEBUG = True
