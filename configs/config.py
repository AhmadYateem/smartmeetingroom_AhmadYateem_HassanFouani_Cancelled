"""
Configuration management for Smart Meeting Room System.
Handles loading and accessing environment variables and configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration class with common settings."""

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///smartmeetingroom.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv('FLASK_DEBUG', 'False') == 'True'

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # Flask
    DEBUG = os.getenv('FLASK_DEBUG', 'False') == 'True'
    TESTING = False
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')

    # Service Configuration
    USER_SERVICE_PORT = int(os.getenv('USER_SERVICE_PORT', 5001))
    ROOM_SERVICE_PORT = int(os.getenv('ROOM_SERVICE_PORT', 5002))
    BOOKING_SERVICE_PORT = int(os.getenv('BOOKING_SERVICE_PORT', 5003))
    REVIEW_SERVICE_PORT = int(os.getenv('REVIEW_SERVICE_PORT', 5004))

    # Service URLs
    USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:5001')
    ROOM_SERVICE_URL = os.getenv('ROOM_SERVICE_URL', 'http://localhost:5002')
    BOOKING_SERVICE_URL = os.getenv('BOOKING_SERVICE_URL', 'http://localhost:5003')
    REVIEW_SERVICE_URL = os.getenv('REVIEW_SERVICE_URL', 'http://localhost:5004')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 300))

    # RabbitMQ
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'admin')
    RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

    # Security
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
    ACCOUNT_LOCK_DURATION = int(os.getenv('ACCOUNT_LOCK_DURATION', 1800))

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', 1000))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'app.log')

    # CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:8080']


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'sqlite:///test_smartmeetingroom.db')
    JWT_SECRET_KEY = 'test-secret-key'


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False


# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration object based on environment name.

    Args:
        config_name: Name of configuration ('development', 'testing', 'production')

    Returns:
        Configuration class
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    return config_by_name.get(config_name, DevelopmentConfig)
