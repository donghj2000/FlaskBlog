from app import db

class User(db.Model):
    __tablename__ = "blog_user"
    id            = db.Column( db.Integer, autoincrement = True, primary_key = True, nullable = False)     
    password      = db.Column( db.String(128), nullable = True)       
    last_login    = db.Column( db.DateTime)
    is_superuser  = db.Column( db.Boolean, nullable = False, default = False)
    username      = db.Column( db.String(150), unique = True, nullable = False)
    email         = db.Column( db.String(254), unique = True, nullable = False)
    is_active     = db.Column( db.Boolean, nullable = False, default = False)  
    creator       = db.Column( db.Integer, default = 0) 
    modifier      = db.Column( db.Integer, default = 0) 
    avatar        = db.Column( db.String(1000), default = "" )
    nickname      = db.Column( db.String(200), default = "")    
    desc          = db.Column( db.String(200), default = "") 
    created_at    = db.Column( db.DateTime )
    modified_at   = db.Column( db.DateTime )
    comment_users = db.relationship("Comment", backref = "user")
    like_users    = db.relationship("Like")

    def __repr__(self):
        return "<%02d-%s(%s)>" % (self.id,self.username,self.email)
