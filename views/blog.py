#!/usr/bin/env python
# encoding: utf-8

from flask import Blueprint, jsonify, current_app, make_response
from flask_restful import Api,Resource
from flask_restful.reqparse import RequestParser
from sqlalchemy import and_,or_,not_,func
from datetime import datetime

from utils.util import jwt_required,jwt_encode,jwt_decode, current_identity
from app import db
from models.blog import Tag,Catalog, article_tag, Article, Comment,Like,Message
from models.user import User
from models.constants import Constant
from app.elasticsearch7   import ESUpdateIndex, ESSearchIndex

blog_bp = Blueprint("blog", __name__) 
blog_api = Api(blog_bp)

# 递归获取父节点 id
ancestorIds = []
def get_ancestors(parent_id):
    if parent_id != 0:
        ancestorIds.insert(0, parent_id)
        try:
            ret = Catalog.query.filter(Catalog.id == parent_id).first()
            if ret != None:
                parent_id_tmp = ret.parent_id
                get_ancestors(parent_id_tmp)
            else:
                return ancestorIds
        except Exception as ex:
            print("ex,",ex)
            return ancestorIds
    else:
        return ancestorIds
        
# 递归获取子节点 id
descendantsIds = []
def get_descendants(catalog_id):
    descendantsIds.append(catalog_id)
    try:
        catalogs = Catalog.query.filter(Catalog.parent_id == catalog_id).all()
        if len(catalogs) != 0:
            for cata in catalogs:
                get_descendants(cata.id)
        else:
            return descendantsIds
    except Exception as ex:
        print("ex,", ex)
        return descendantsIds
        
class ArticleListResource(Resource):
    def get(self):
        parser = RequestParser()
        parser.add_argument("status",       location="args", default = "")
        parser.add_argument("search",       location="args", default = "")
        parser.add_argument("tag",          location="args", type = int)
        parser.add_argument("catalog",      location="args", type = int)
        parser.add_argument("page",         location="args", default = 1, type = int)
        parser.add_argument("page_size",    location="args", default = 10,type = int)
        try:
            args = parser.parse_args()
            params = []
            if args.tag != None:
                tags = Tag.query.filter(Tag.id == args.tag).first()
                articles = tags.articles
            else:
                articles = Article.query

            if args.status != None and args.status != "":
                params.append(Article.status == args.status) 
            if args.search != None and args.search != "":
                params.append(Article.title.contains(args.search))
            if args.catalog != None:
                #搜索子类型
                global descendantsIds
                descendantsIds = []
                get_descendants(args.catalog)
                params.append(Article.catalog_id.in_(descendantsIds))
            articles = articles.filter(and_(*params)).order_by(Article.id.asc())

            count = articles.count()
            if args.page != None and args.page_size != None:
                articles = articles.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
            else:
                articles = articles.all()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)

        catalog_infos = {}
        for art in articles:
            global ancestorIds
            ancestorIds = []
            get_ancestors(art.catalog_id)
            catalog_infos[art.id] = {"id":art.catalog_id,"name": art.catalog.name,"parents": ancestorIds}
            
        ret = {}
        ret["count"] = count
        ret["results"] = [{
                "id":           article.id,
                "title":        article.title,
                "excerpt":      article.excerpt,
                "cover":        article.cover,
                "status":       article.status,
                "created_at":   article.created_at,
                "modified_at":  article.modified_at,
                "tags_info":    [{"id": tag.id, "name": tag.name, 
                                 "created_at": tag.created_at,
                                 "modified_at":tag.modified_at
                                 } for tag in article.tags.all()],
                "catalog_info": catalog_infos.get(article.id, {}),
                "views":        article.views,
                "comments":     article.comments,
                "words":        article.words,
                "likes":        article.likes 
        } for article in articles] 
        return make_response(jsonify(ret))
        
    @jwt_required
    def post(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("title",    location="json")
        parser.add_argument("cover",    location="json", default = "")
        parser.add_argument("excerpt",  location="json", default = "")
        parser.add_argument("keyword",  location="json", default = "")
        parser.add_argument("markdown", location="json", default = "")
        parser.add_argument("tags",     location="json", type = list)
        parser.add_argument("catalog",  location="json", type = int)
        try:
            args = parser.parse_args()
            ret = Article.query.filter(Article.title == args.title).first()
            if ret != None:
                return make_response({"detail": "标题已经存在！"}, 500)

            article = Article(title = args.title, cover = args.cover, excerpt = args.excerpt, keyword = args.keyword,
                              markdown = args.markdown, catalog_id = args.catalog, author_id = current_identity.get("id", 1),
                              creator  = current_identity.get("id", 1), modifier = current_identity.get("id", 1),
                              created_at = datetime.utcnow()) 

            if args.tags != None:
                tags = Tag.query.filter(Tag.id.in_(args.tags)).all()
                if tags != None and len(tags) != 0:
                    article.tags = tags
            
            db.session.add(article)
            db.session.commit()
            ESUpdateIndex(article)
            return make_response({"detail": "保存文章成功！"}, 201)   
        except Exception as ex:
            print('ex,',ex)
            return make_response({"detail": "内部错误！"}, 500)
 
class ArticleResource(Resource):
    def get(self, article_id):
        try:
            article = Article.query.filter(Article.id == article_id).first()
            if article == None:
                return make_response({"detail": "内部错误"}, 500)
            
            global ancestorIds
            ancestorIds = []
            get_ancestors(article.catalog_id)
            catalog_infos = {"id":article.catalog_id,"name": article.catalog.name,"parents": ancestorIds}

            ret = {
                    "id":           article.id,
                    "title":        article.title,
                    "excerpt":      article.excerpt,
                    "keyword":      article.keyword,
                    "cover":        article.cover,
                    "markdown":     article.markdown,
                    "status":       article.status,
                    "created_at":   article.created_at,
                    "modified_at":  article.modified_at,
                    "tags_info":    [{"id": tag.id, "name": tag.name, 
                                     "created_at": tag.created_at,
                                     "modified_at":tag.modified_at
                                     } for tag in article.tags.all()],
                    "catalog_info": catalog_infos,
                    "views":        article.views,
                    "comments":     article.comments,
                    "words":        article.words,
                    "likes":        article.likes } 
            article.views += 1
            db.session.commit()
            return make_response(jsonify(ret))
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)

    @jwt_required
    def put(self, article_id):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("title",    location="json")
        parser.add_argument("cover",    location="json", default = "")
        parser.add_argument("excerpt",  location="json", default = "")
        parser.add_argument("keyword",  location="json", default = "")
        parser.add_argument("markdown", location="json", default = "")
        parser.add_argument("tags",     location="json", type = list)
        parser.add_argument("catalog",  location="json", type = int)
        try:
            args = parser.parse_args()
            article = Article.query.filter(Article.id == article_id).first()
            if article == None:
                return make_response({"detail": "文章不存在！"}, 500)
            article.modified = current_identity.get("id", 1) 
            article.title      = args.title 
            article.cover      = args.cover
            article.excerpt    = args.excerpt
            article.keyword    = args.keyword 
            article.markdown   = args.markdown
            article.catalog_id = args.catalog

            if args.tags != None:
                tags = Tag.query.filter(Tag.id.in_(args.tags)).all()
                if tags != None and len(tags) != 0:
                    article.tags = tags
            db.session.commit()
            ESUpdateIndex(article)
            return make_response({"detail": "保存文章成功！"}, 201) 
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

    @jwt_required
    def patch(self, article_id): #上线，下线文章
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("status",    location="json")
        try:
            args = parser.parse_args()
            article = Article.query.filter(Article.id == article_id).first()
            if article == None:
                return make_response({"detail": "文章不存在！"}, 500)
            article.status = args.status 
            db.session.commit()
            return make_response({"detail": "保存文章成功！"}, 201)     
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
   
class ArchiveListResource(Resource):
    def get(self):
        parser = RequestParser()
        parser.add_argument("page",         location="args", default = 1, type = int)
        parser.add_argument("page_size",    location="args", default = 10,type = int)
        try:
            args = parser.parse_args()
            articles = Article.query.filter(Article.status==Constant.ARTICLE_STATUS_PUBLISHED).order_by(Article.id.asc())
            total = articles.count()
            if args.page != None and args.page_size != None:
                page = articles.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
            else:
                page = articles.all()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
    
        if page is not None:
            ret = {
                "count": total,
                "next": None,
                "previous": None,
                "results": [] }
            if total != 0:
                years = {}
                for article in page:
                    year = article.created_at.year
                    articles_year = years.get(year)
                    if not articles_year:
                        articles_year = []
                        years[year] = articles_year
                    
                    articles_year.append({
                                          "id":         article.id,
                                          "title":      article.title,
                                          "created_at": article.created_at })
                
                for key, value in years.items():
                    ret["results"].append({
                        "year": key,
                        "list": value})
                ret["results"].sort(key=lambda i:i["year"], reverse=True)
    
        return make_response(jsonify(ret))
    
def getReplies(replies):
    comment_replies = []
    if len(replies)==0:
        return []
    for reply in replies:
        user_rep = User.query.filter(User.id == reply.user_id).first()
        if user_rep != None:
            comment_replies.append({
                "id":              reply.id,
                "content":         reply.content,
                "user_info":       {
                                       "id":     user_rep.id,
                                       "name":   user_rep.nickname or user_rep.username,
                                       "avatar": user_rep.avatar,   
                                       "role":   "Admin" if user_rep.is_superuser else "" 
                                   },
                "created_at":      reply.created_at,
                "comment_replies": getReplies(reply.replies) })
    return comment_replies   

class CommentListResource(Resource):
    def get(self):
        parser = RequestParser()
        parser.add_argument("user",       location="args", default = None, type = int)
        parser.add_argument("search",     location="args", default = "")
        parser.add_argument("article",    location="args", default = None, type = int)
        parser.add_argument("page",       location="args", type = int)
        parser.add_argument("page_size",  location="args", type = int)
        try:
            args = parser.parse_args()
            params = []        
            if args.user != None:
                params.append(Comment.user_id == args.user) 
            if args.search != None and args.search != "":
                params.append(Comment.content.contains(args.search))
            if args.article != None:
                params.append(Comment.article_id == args.article)
            comments = Comment.query.filter(and_(*params)).order_by(Comment.id.asc())
            count = comments.count()
            if args.page != None and args.page_size != None:
                comments = comments.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
            else:
                comments = comments.all()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
            
        ret = {};
        ret["count"] = count
        ret["results"] = []
        for comment in comments:
            user_info = {
                "id":    comment.user.id,
                "name":  comment.user.nickname or comment.user.username,
                "avatar":comment.user.avatar,
                "role"  :"Admin" if comment.user.is_superuser==True else ""
            } 
            article_info = {
                "id":    comment.article.id, 
                "title": comment.article.title }

            comment_replies = getReplies(comment.replies)
            ret["results"].append({
                "id":              comment.id,
                "user":            comment.user_id,
                "user_info":       user_info,
                "article":         comment.article_id, 
                "article_info":    article_info,
                "created_at":      comment.created_at, 
                "reply":           comment.reply_id, 
                "content":         comment.content,
                "comment_replies": comment_replies })
        print("comment,ret=",ret)
        return make_response(jsonify(ret))
        
    @jwt_required
    def post(self):
        if not current_identity:
            return make_response({"detail": "没有登陆！"}, 400)

        parser = RequestParser()
        parser.add_argument("article",  location="json", type = int)
        parser.add_argument("user",     location="json", type = int)
        parser.add_argument("reply",    location="json", type = int)
        parser.add_argument("content",  location="json")
        try:
            args = parser.parse_args()
            comment = Comment(creator = args.user, modifier = args.user, user_id = args.user,article_id = args.article,
                              reply_id = args.reply, content = args.content,created_at = datetime.utcnow())
            db.session.add(comment)
            article = Article.query.filter(Article.id == args.article).first()
            article.comments += 1
            db.session.commit()
            return make_response({"detail": "评论成功！"}, 201) 
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

class LikeListResource(Resource):
    @jwt_required
    def post(self):
        if not current_identity:
            return make_response({"detail": "没有登陆！"}, 400)

        parser = RequestParser()
        parser.add_argument("article",  location="json", type = int)
        parser.add_argument("user",     location="json", type = int)
        try:
            args = parser.parse_args()
            like = Like(creator = args.user, modifier = args.user, user_id = args.user,article_id = args.article,
                        created_at = datetime.utcnow())
            db.session.add(like)
            article = Article.query.filter(Article.id == args.article).first()
            article.likes += 1
            db.session.commit()
            return make_response({"detail": "点赞成功！"}, 201) 
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

class MessageListResource(Resource):
    @jwt_required
    def get(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)
        parser = RequestParser()
        parser.add_argument("search",     location="args", default = "")
        parser.add_argument("page",       location="args", type = int)
        parser.add_argument("page_size",  location="args", type = int)
        try:
            args = parser.parse_args()      
            params = []        
            if args.search != None and args.search != "":
                params = [Message.content.contains(args.search),
                          Message.name.contains(args.search),
                          Message.email.contains(args.search),
                          Message.phone.contains(args.search)]
            msgs = Message.query.filter(or_(*params))
            count = msgs.count()
            if args.page != None and args.page_size != None:
                msgs = msgs.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
            else:
                msgs = msgs.all()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
       
        ret = {}
        ret["count"] = count
        ret["results"] = [{
            "id":         msg.id,
            "email":      msg.email,
            "content":    msg.content,
            "phone":      msg.phone,
            "name":       msg.name,
            "created_at": msg.created_at } for msg in msgs]
        return make_response(jsonify(ret))
        
    def post(self):
        parser = RequestParser()
        parser.add_argument("email",   location="json")
        parser.add_argument("content", location="json")
        parser.add_argument("phone",   location="json")
        parser.add_argument("name",    location="json")
        try:
            args = parser.parse_args()
            msg = Message(creator = 0, modifier = 0, email = args.email, content = args.content, 
                          phone = args.phone, name = args.name, created_at = datetime.utcnow())
            db.session.add(msg)
            db.session.commit()
            return make_response({"detail": "留言成功！"}, 201)
        except Exception as ex: 
            print("ex,",ex)
            return make_response({"detail": "内部错误11"}, 500)

class TagListResource(Resource):
    @jwt_required
    def get(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("name",       location="args", default = "")
        parser.add_argument("page",       location="args", type = int)
        parser.add_argument("page_size",  location="args", type = int)
        try:
            args = parser.parse_args()            
            params = []        
            if args.name != None and args.name != "":
                params.append(Tag.name.contains(args.name))
            tags = Tag.query.filter(and_(*params))
            count = tags.count()
            if args.page != None and args.page_size != None:
                tags = tags.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
            else:
                tags = tags.all()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
            
        ret = {}
        ret["count"] = count
        ret["results"] = [{
            "id":          tag.id,
            "name":        tag.name,
            "created_at":  tag.created_at,
            "modified_at": tag.modified_at } for tag in tags]
        return make_response(jsonify(ret))
        
    @jwt_required
    def post(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("name",  location="json")
        try:
            args = parser.parse_args()
            tag = Tag(creator = current_identity.get("id", 1), modifier = current_identity.get("id", 1), 
                      name = args.name, created_at = datetime.utcnow())
            db.session.add(tag)
            db.session.commit()
            return make_response({"detail": "新增标签成功！"}, 201) 
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
    
class TagResource(Resource):
    @jwt_required
    def put(self, tag_id):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("name",  location="json")
        try:
            args = parser.parse_args()
            tag = Tag.query.filter(Tag.id == tag_id).first()
            if tag == None:
                return make_response({"detail": "内部错误"}, 500)                
            tag.name = args.name
            db.session.commit()
            return make_response({"detail": "修改标签成功！"}, 201)
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

    @jwt_required
    def delete(self, tag_id): #DeleteTag
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        try:
            Tag.query.filter(Tag.id == tag_id).delete()             
            db.session.commit()
            return make_response({"detail": "删除标签成功！"}, 201)
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

def is_leaf_node(catalog):
    hasDescendants = Catalog.query.filter(Catalog.parent_id == catalog.id).all()
    if hasDescendants==None or len(hasDescendants)==0:
        return True
    return False
    
class CatalogListResource(Resource):
    @jwt_required            
    def get(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        try:
            catas = Catalog.query.all()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail", "内部错误!"}, 500)
            
        ret = []
        descendants = []
        for cata in catas:
            if cata.parent_id == 0:
                root = cata
            else:
                descendants.append(cata)
        
        root_dict = {
                     "id":        root.id,  
                     "name":      root.name,
                     "parent_id": None }
        root_dict['children'] = []
        ret.append(root_dict)
        parent_dict = {root.id:root_dict}
        for cls in descendants:
            data = {
                     "id":        cls.id,  
                     "name":      cls.name,
                     "parent_id": cls.parent_id }
            parent_id = data.get('parent_id')
            parent = parent_dict.get(parent_id)
            parent['children'].append(data) 
            if not is_leaf_node(cls) and cls.id not in parent_dict:
                data['children'] = []
                parent_dict[cls.id] = data
        print(ret)
        return make_response(jsonify(ret))
        
    @jwt_required
    def post(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("name",    location="json")
        parser.add_argument("parent",  location="json", type = int, default = 0)
        try:
            args = parser.parse_args()
            if args.parent == None:
                parent_id = 0            
            catalog = Catalog(creator = current_identity.get("id", 1), modifier = current_identity.get("id", 1), 
                              name = args.name, parent_id = parent_id, created_at = datetime.utcnow())
            db.session.add(catalog)
            db.session.commit()
            return make_response({"detail": "新增分类成功！"}, 201) 
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)

 
class CatalogResource(Resource):
    @jwt_required
    def patch(self, catalog_id):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        parser = RequestParser()
        parser.add_argument("name",  location="json")
        try:
            args = parser.parse_args()
            catalog = Catalog.query.filter(Catalog.id == catalog_id).first()
            if catalog == None:
                return make_response({"detail": "内部错误"}, 500)                
            catalog.name = args.name
            db.session.commit()
            return make_response({"detail": "修改类型成功！"}, 201)
        except Exception as ex:
            print("exn",ex)
            return make_response({"detail": "内部错误"}, 500)

    @jwt_required
    def delete(self, catalog_id):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)

        try:
            Catalog.query.filter(Catalog.id == catalog_id).delete()             
            db.session.commit()
            return make_response({"detail": "删除类型成功！"}, 201)   
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
    
class NumberListResource(Resource):
    def get(self):
        ret = {
            "views":    db.session.query(func.sum(Article.views)).first()[0],
            "likes":    db.session.query(func.sum(Article.likes)).first()[0],
            "comments": db.session.query(func.sum(Article.comments)).first()[0],
            "messages": Message.query.count()
        }
        
        return make_response(jsonify(ret))    
    
class TopListResource(Resource):
    def get(self):
        try:
            articles = Article.query.order_by(Article.views.desc()).offset(0).limit(10)
            total = articles.count()
        except Exception as ex:
            print("ex,", ex)
            return make_response({"detail": "内部错误"}, 500)
        ret = {}
        ret["count"] = total
        ret["results"] = [{
            "id":     article.id,
            "title":  article.title,
            "views":  article.views,
            "likes":  article.likes } for article in articles]
        
        return make_response(jsonify(ret))
        
class EsListResource(Resource):
    def get(self):  #GetElasticSearch
        parser = RequestParser()
        parser.add_argument("text",       location="args", default = "")
        parser.add_argument("page",       location="args", type = int)
        parser.add_argument("page_size",  location="args", type = int)
        args = parser.parse_args()
        ret = ESSearchIndex(args.page, args.page_size, args.text);
        return make_response(jsonify(ret))
        
        
blog_api.add_resource(ArticleListResource,   '/api/article/')
blog_api.add_resource(ArticleResource,       '/api/article/<int:article_id>/')
blog_api.add_resource(ArchiveListResource,   '/api/archive/')
blog_api.add_resource(CommentListResource,   '/api/comment/')
blog_api.add_resource(LikeListResource,      '/api/like/')
blog_api.add_resource(MessageListResource,   '/api/message/')
blog_api.add_resource(TagListResource,       '/api/tag/')
blog_api.add_resource(TagResource,           '/api/tag/<int:tag_id>/')
blog_api.add_resource(CatalogListResource,   '/api/catalog/')
blog_api.add_resource(CatalogResource,       '/api/catalog/<int:catalog_id>/')
blog_api.add_resource(NumberListResource,    '/api/number/')
blog_api.add_resource(TopListResource,       '/api/top/')
blog_api.add_resource(EsListResource,        '/api/es/')
    