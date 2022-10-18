from utils.util import encrypt,decrypt
from app import create_app, import db
from models.user import User
from models.blog import Tag,Catalog, article_tag, Article, Comment,Like,Message
from datetime import datetime

def CreateDatabase():
    print(db)
    db.drop_all()
    db.create_all()
    
def CreateAdmin():
    user0 = User(
        password=encrypt("123456"),
        is_superuser=True,
        username="admin",
        email="111@qq.com",
        is_active=True,
        creator=0,
        modifier=0,
        avatar="",
        nickname="admin",
        created_at=datetime.utcnow())
                
    db.session.add(user0)
    db.session.commit()
 
def Create():
    app = create_app("dev")
    with app.app_context():
        CreateDatabase()
        CreateAdmin()
    print("created admin")

Create()

