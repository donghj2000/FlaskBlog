import datetime
import os
class DefaultConfig:
    """默认配置"""
    DEBUG = True

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEDIA_ROOT = os.path.join(BASE_DIR, 'upload')
    MEDIA_URL = "../upload"
    UPLOAD_URL = 'upload'
    
    SQLALCHEMY_DATABASE_URI = "sqlite:///../data/db.sqlite3"
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    
    JWT_SECRET_KEY = "alita666666"
    JWT_EXPIRATION_DAYS = 7
    JWT_VERIFY_CLAIMS = ['signature', 'exp', 'iat']
    JWT_REQUIRED_CLAIMS = ['exp', 'iat']
    JWT_AUTH_COOKIE= "JwtCookie"
    JWT_ALGORITHM = 'HS256'
    JWT_LEEWAY = datetime.timedelta(seconds=10)
    JWT_NOT_BEFORE_DELTA = datetime.timedelta(seconds=0)
    
    SECRET_KEY = '3p--&e$%^%71)ijd@td7e2=s9gdlxalogjkor@_f#@47+sc=qo'
    HOST_SITE = "127.0.0.1:8000"
    MAIL_SERVER = "smtp.qq.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'xxxxxxx@qq.com'
    MAIL_PASSWORD = 'aldfjasldfjsf'
    
    ELASTICSEARCH_ON = True
    ELASTICSEARCH_HOST = "127.0.0.1:9200"
    ELASTICSEARCH_INDEX = "flaskblog"
    
    
config_dict = {
    "dev": DefaultConfig
}