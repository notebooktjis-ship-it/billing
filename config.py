import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'snb-hotel-secret-key-2024'
    
    # Database - PostgreSQL with SQLite fallback
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'snb_hotel.db').replace('\\', '/')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 0,
    }
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # Hotel settings
    HOTEL_NAME = 'HOTEL SHRI GOVIND'
    HOTEL_ADDRESS = 'Jagmal Chowk, near Honda Showroom, Tikrapara, Bilaspur, Chhattisgarh 495001'
    HOTEL_PHONE = '7891234560'
    HOTEL_EMAIL = 'example@gmail.com'
    HOTEL_GST = '22AATFH3393Q1ZL'
    HOTEL_OWNER = 'Akshay Shukla'
    
    # Billing settings
    GST_RATE = 5.00
    LATE_CHECKOUT_CHARGE_PER_HOUR = 200
    EXTRA_PERSON_CHARGE = 300
    
    # Room prices
    ROOM_PRICES = {
        'standard': 1500,
        'deluxe': 2500,
        'suite': 4000
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
