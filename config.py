# Imports
import os
from dotenv import load_dotenv

# Load from .env
load_dotenv()

# Define config class and Development, Testing, and Production subclasses
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_URI = os.environ.get('DATABASE_URI')

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DATABASE_URI = 'sqlite:///test.db'

class ProductionConfig(Config):
    DEBUG = False

# Add a dictionary to map string names to the relevant classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}