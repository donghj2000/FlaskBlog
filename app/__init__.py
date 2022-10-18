from flask import Flask
from os.path import *
import sys
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from elasticsearch import Elasticsearch
from .config import config_dict

BASE_DIR = dirname(dirname(abspath(__file__)))
sys.path.insert(0, BASE_DIR + "\\views")

db = SQLAlchemy()
mail = None

esClient = None

def register_extention(app):
    """组件初始化"""
    #SQLAlchemy
    from app import db, mail, esClient
    db.init_app(app)
    
    global mail
    mail = Mail(app)

    global esClient
    esClient = Elasticsearch(app.config['ELASTICSEARCH_HOST'])
    
def register_bp(app):
    from views.user import user_bp
    from views.blog import blog_bp
    app.register_blueprint(user_bp)
    app.register_blueprint(blog_bp)
    
def create_flask_app(type):
    config_class = config_dict[type]
    app = Flask(__name__,
                static_folder=config_class.MEDIA_URL # 设置静态文件的存储目录（默认）
    )
    
    app.config.from_object(config_class)
    return app

def create_app(type):
    app = create_flask_app(type)
    register_extention(app)
    register_bp(app)
    return app
    
