"""Configuration handling for job-campaign-tracker Flask app."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class with shared settings for all environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_URI = os.environ.get('DATABASE_URI')

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-secret-key'
    DATABASE_URI = 'test.db'

class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}