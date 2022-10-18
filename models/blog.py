from app import db
from .constants import Constant

class Tag(db.Model):
    __tablename__ = "blog_tag"
    id        = db.Column(db.Integer,    autoincrement = True, primary_key = True, nullable = False)  
    creator   = db.Column(db.Integer,    nullable = True) 
    modifier  = db.Column(db.Integer,    nullable = True)      
    name      = db.Column(db.String(20), nullable = False, unique = True) 
    created_at   = db.Column(db.DateTime)
    modified_at  = db.Column(db.DateTime)
    def __repr__(self):
        return "<Tag:id=%02d-name=%s>" % (self.id,self.name)

class Catalog(db.Model):
    __tablename__ = "blog_catalog"
    id        = db.Column(db.Integer,    autoincrement = True, primary_key = True, nullable = False)  
    creator   = db.Column(db.Integer,    nullable = True) 
    modifier  = db.Column(db.Integer,    nullable = True) 
    name      = db.Column(db.String(50), nullable = False, unique = True)  
    created_at   = db.Column(db.DateTime)
    modified_at  = db.Column(db.DateTime)
    parent_id    = db.Column(db.Integer, db.ForeignKey("blog_catalog.id", ondelete="CASCADE"), default = 0) 
    cls_articles = db.relationship("Article", backref = "catalog")
    
    def __repr__(self):
        return "<Catalog:id=%02d,name=%s,parent_id=%02d>" % (self.id,self.name,self.parent_id)
        
article_tag = db.Table('article_tag',
                       db.Column('id',         db.Integer, primary_key = True, autoincrement = True),
                       db.Column('article_id', db.Integer, db.ForeignKey('blog_article.id')),
                       db.Column('tag_id',     db.Integer, db.ForeignKey('blog_tag.id'))
                       )     
        
class Article(db.Model):
    __tablename__ = "blog_article"
    id        = db.Column(db.Integer,      autoincrement = True, primary_key = True, nullable = False)  
    creator   = db.Column(db.Integer,      nullable = True) 
    modifier  = db.Column(db.Integer,      nullable = True) 
    title     = db.Column(db.String(100),  nullable = False, unique = True)     
    cover     = db.Column(db.Text,         nullable = True)
    excerpt   = db.Column(db.String(200),  nullable = True)
    keyword   = db.Column(db.String(200),  nullable = True)
    markdown  = db.Column(db.Text,         nullable = False)
    status    = db.Column(db.String(30),   nullable = False, default = Constant.ARTICLE_STATUS_DRAFT)
    views     = db.Column(db.Integer,      nullable = False, default = 0)
    comments  = db.Column(db.Integer,      nullable = False, default = 0)
    likes     = db.Column(db.Integer,      nullable = False, default = 0)
    words     = db.Column(db.Integer,      nullable = False, default = 0)
    created_at   = db.Column(db.DateTime )
    modified_at  = db.Column(db.DateTime )
    catalog_id   = db.Column(db.Integer,      db.ForeignKey("blog_catalog.id", ondelete="NO ACTION"),nullable = False) 
    author_id    = db.Column(db.Integer,      db.ForeignKey("blog_user.id", ondelete = "NO ACTION"), nullable = False)
    tags         = db.relationship("Tag", secondary=article_tag, backref=db.backref("articles", lazy="dynamic"),
                                   lazy="dynamic")
    article_comments = db.relationship("Comment", backref = "article")
    article_likes    = db.relationship("Like")
    def __repr__(self):
        return "<Article:id=%02d,title=%s,catalog_id=%02d>" % (self.id,self.title,self.catalog_id)
 
class Comment(db.Model):
    __tablename__ = "blog_comment"
    id           = db.Column(db.Integer,  autoincrement = True, primary_key = True, nullable = False)  
    creator      = db.Column(db.Integer,  nullable = True) 
    modifier     = db.Column(db.Integer,  nullable = True) 
    content      = db.Column(db.Text,     nullable = False)  
    created_at   = db.Column(db.DateTime )
    modified_at  = db.Column(db.DateTime )
    article_id   = db.Column(db.Integer,      db.ForeignKey("blog_article.id", ondelete = "NO ACTION"), nullable = False)
    reply_id     = db.Column(db.Integer,      db.ForeignKey("blog_comment.id", ondelete = "CASCADE"), nullable = True)
    user_id      = db.Column(db.Integer,      db.ForeignKey("blog_user.id", ondelete = "NO ACTION"), nullable = False) 
    replies      = db.relationship("Comment", back_populates = "comment")
    comment      = db.relationship("Comment", back_populates = "replies", remote_side = [id])

    def __repr__(self):
        return ""
        
class Like(db.Model):
    __tablename__ = "blog_like"
    id           = db.Column(db.Integer, autoincrement = True, primary_key = True, nullable = False)  
    creator      = db.Column(db.Integer, nullable = True) 
    modifier     = db.Column(db.Integer, nullable = True)   
    created_at   = db.Column(db.DateTime )
    modified_at  = db.Column(db.DateTime)
    article_id   = db.Column(db.Integer,      db.ForeignKey("blog_article.id", ondelete = "NO ACTION"), nullable = False)
    user_id      = db.Column(db.Integer,      db.ForeignKey("blog_user.id", ondelete = "NO ACTION"), nullable = False) #like_users
    def __repr__(self):
        return ""
        
class Message(db.Model):
    __tablename__ = "blog_message"
    id           = db.Column(db.Integer,      autoincrement = True, primary_key = True, nullable = False)  
    creator      = db.Column(db.Integer,      nullable = True) 
    modifier     = db.Column(db.Integer,      nullable = True)      
    email        = db.Column(db.String(100),  nullable = False)
    content      = db.Column(db.Text,         nullable = False)
    phone        = db.Column(db.String(20),   nullable = True)
    name         = db.Column(db.String(20),   nullable = True) 
    created_at   = db.Column(db.DateTime)
    modified_at  = db.Column(db.DateTime)
    def __repr__(self):
        return ""