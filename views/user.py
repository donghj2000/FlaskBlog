#!/usr/bin/env python
# encoding: utf-8

from flask import Blueprint, jsonify, current_app, make_response,request
from flask_restful import Api,Resource
from flask_restful.reqparse import RequestParser
from sqlalchemy import and_,or_,not_,func
from datetime import datetime

from utils.util import jwt_required,jwt_encode,jwt_decode, current_identity,encrypt,decrypt,\
    get_sha256,send_mail, get_random_password, get_upload_file_path
    
from app import db
from models.user import User

user_bp = Blueprint("user", __name__) 
user_api = Api(user_bp)

class UserListResource(Resource):
    @jwt_required
    def get(self):
        if not current_identity or not current_identity.get("is_superuser", None):
            return make_response({"detail": "没有管理员权限！"}, 400)
            
        parser = RequestParser()
        parser.add_argument("username",     location="args", default = "")
        parser.add_argument("is_active",    location="args")
        parser.add_argument("is_superuser", location="args")
        parser.add_argument("page",         location="args", default = 1, type = int)
        parser.add_argument("page_size",    location="args", default = 10,type = int)
        try:
            args = parser.parse_args()
            params = []
            if args.username != None and args.username != "":
                params.append(User.username.contains(args.username)) 
            if args.is_active != None and args.is_active != "":
                if args.is_active == "true":
                    params.append(User.is_active == True)
                else:
                    params.append(User.is_active == False)
            if args.is_superuser != None and args.is_superuser != "":
                if args.is_superuser == "true":
                    params.append(User.is_superuser == True)
                else:
                    params.append(User.is_superuser == False)
            users = User.query.filter(and_(*params))
            count = users.count()
            users = users.offset((args.page - 1) * args.page_size).limit(args.page_size).all()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
         
        resp = make_response({
            "count": count,
            "results": [{"id":user.id, 
                     "username":     user.username, 
                     "last_login":   user.last_login, 
                     "email":        user.email,
                     "avatar":       user.avatar,
                     "nickname":     user.nickname,
                     "is_active":    user.is_active, 
                     "is_superuser": user.is_superuser,
                     "created_at":   user.created_at} for user in users]
        })
        return resp

    def post(self):
        parser = RequestParser()
        parser.add_argument("username", location="json")
        parser.add_argument("password", location="json")
        parser.add_argument("nickname", location="json")
        parser.add_argument("avatar",   location="json")
        parser.add_argument("email",    location="json")
        parser.add_argument("desc",     location="json")
        try:
            args = parser.parse_args()
            encryptPass = encrypt(args.password)
            user = User(username = args.username, password = encryptPass, nickname = args.nickname,
                        avatar = args.avatar, email = args.email, desc = args.desc,created_at = datetime.utcnow())
            db.session.add(user)
            db.session.commit()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "保存数据库失败"}, 500)
            
        sign = get_sha256(get_sha256(current_app.config['SECRET_KEY'] + str(user.id)))
        site = current_app.config['HOST_SITE']
        if current_app.config['DEBUG']:
            site = '127.0.0.1:8000'
        path = '/account/result'
        url = "http://{site}{path}?type=validation&id={id}&sign={sign}".format(
            site=site, path=path, id=user.id, sign=sign)
        content = """
                        <p>请点击下面链接验证您的邮箱</p>
                        <a href="{url}" rel="bookmark">{url}</a>
                        再次感谢您！
                        <br />
                        如果上面链接无法打开，请将此链接复制至浏览器。
                        {url}
                        """.format(url=url)
        try:
            send_mail(subject="验证您的电子邮箱",
                      message=content,
                      recipient_list=[user.email])
                    
            resp = make_response({"detail": "向你的邮箱发送了一封邮件，请打开验证，完成注册。"})
        except Exception as e:
            print("exception:", e)
            resp = make_response({"detail": "发送验证邮箱失败，请检查邮箱是否正确。"}, 500)
          
        return resp

class UserResource(Resource):
    @jwt_required
    def get(self, user_id):
        if not current_identity :
            return make_response({"detail": "未登陆！"}, 400)
            
        if not current_identity.get("is_superuser", None) and current_identity.get("id", None) != user_id:
            return make_response({"detail": "只能获取自己的个人信息"}, 400)
            
        try:
            user = User.query.filter_by(id = user_id).first()
            if not user:
                return make_response({"detail": "用户不存在"}, 500)
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
            
        resp = make_response({"id":user.id, 
                     "username":     user.username, 
                     "last_login":   user.last_login, 
                     "email":        user.email,
                     "avatar":       user.avatar,
                     "nickname":     user.nickname,
                     "is_active":    user.is_active, 
                     "is_superuser": user.is_superuser,
                     "created_at":   user.created_at})
        return resp
    @jwt_required
    def put(self, user_id):
        if not current_identity :
            return  make_response({"detail": "未登陆！"}, 400)
            
        if not current_identity.get("is_superuser", None) and current_identity.get("id", None) != user_id:
            return make_response({"detail": "只能获取自己的个人信息"}, 400)
            
        try:
            user = User.query.filter_by(id = user_id).first()
            if not user:
                return make_response({"detail": "用户不存在"}, 500)
               
            parser = RequestParser()
            parser.add_argument("nickname", location="json",default = None)
            parser.add_argument("email",    location="json",default = None)
            parser.add_argument("desc",     location="json",default = None)
            parser.add_argument("avatar",   location="json",default = None)
            parser.add_argument("is_active",location="json",type = bool, default = None)
            args = parser.parse_args()
            
            if args.nickname != None and args.nickname != "":
                user.nickname = args.nickname
            if args.email != None and args.email != "":
                user.email    = args.email
            if args.desc != None and args.desc != "":
                user.desc     = args.desc
            if args.avatar != None and args.avatar != "":
                user.avatar   = args.avatar
            if args.is_active != None:
                user.is_active = args.is_active
            
            db.session.commit()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)
           
        return make_response({"detail": "修改个人信息成功"}) 
        
    @jwt_required
    def patch(self, user_id):
        return self.put(user_id)
        
class JwtLoginResource(Resource):
    def post(self):  #JwtLogin
        parser = RequestParser()
        parser.add_argument("username", location="json")
        parser.add_argument("password", location="json")
        args = parser.parse_args()
        try:
            user = User.query.filter(User.username == args.username).first()
            if not user:
                return make_response({"detail": "用户名或密码错误！"},400)
            if user.is_active == False: 
                return make_response({"detail": "未完成用户验证！"}, 400)
            passwordOk = decrypt(user.password, args.password);
            if passwordOk != True:
                return make_response({"detail": "用户名或密码错误。"}, 400)
            user.last_login = datetime.utcnow()
            db.session.commit()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 400)
    
        token = jwt_encode({"username": args.username, "id": user.id, "is_superuser": user.is_superuser})       
        resp = make_response({
            "expire_days": current_app.config["JWT_EXPIRATION_DAYS"], 
            "token": token,
            "user": {"id": user.id, 
                     "username":     args.username, 
                     "last_login":   "", 
                     "email":        user.email,
                     "avatar":       user.avatar,
                     "nickname":     user.nickname,
                     "is_active":    user.is_active, 
                     "is_superuser": user.is_superuser,
                     "create_at":    ""}
        })
        resp.set_cookie(current_app.config["JWT_AUTH_COOKIE"], token, max_age=current_app.config["JWT_EXPIRATION_DAYS"]*24*3600)
        return resp
        
class PasswordResource(Resource):
    def put(self):
        parser = RequestParser()
        parser.add_argument("username", location="json", default = None)
        args = parser.parse_args()
        try:
            user = User.query.filter_by(username = args.username).first()
            if not user:
                return make_response({"detail": "内部错误"}, 500)
            if user.is_active == False:            
                return make_response({'detail': '账号未激活.'}, 400)
         
            password = get_random_password()
            send_mail(subject="您在博客FlaskBlog上的新密码",
                      message="""HI, 您的新密码:\n{password}""".format(password=password),
                      recipient_list=[user.email])
                    
            user.password = encrypt(password)
            db.session.commit()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 500)            
        return make_response({'detail': 'Send New email failed, Please check your email address'})
   
    @jwt_required
    def post(self):
        if not current_identity :
            return  make_response({"detail": "未登陆！"}, 400)
        
        try:
            user_id = current_identity.get("id", None)
            user = User.query.filter_by(id = user_id).first()
            if not user:
                return make_response({"detail": '用户不存在！'}, 400)
            parser = RequestParser()
            parser.add_argument("password",     location="json",default = None)
            parser.add_argument("new_password", location="json",default = None)
            args = parser.parse_args()
            passwordOk = decrypt(user.password, args.password)
            if not passwordOk:
                return make_response({ "detail": "密码错误！" }, 400)
            user.password = encrypt(args.new_password);       
            db.session.commit()
        except Exception as ex:
            print("ex,",ex)
            return make_response({"detail": "内部错误"}, 400)
            
        return make_response({"detail": "修改密码成功"})
        
class ConstantResource(Resource):
    def get(self):
        return  
        
class UploadImgResource(Resource):
    def post(self, path):
        uploaded_file = request.files.get("file")
        full_file_path, file_path = get_upload_file_path(path,uploaded_file.filename)
        uploaded_file.save(full_file_path)
        return make_response({'url': file_path})
        
class AccountRetResource(Resource):
    def get(self):
        parser = RequestParser()
        parser.add_argument("type", location="args",default = None)
        parser.add_argument("id", location="args",type = int, default = None)
        parser.add_argument("sign", location="args", default = None)
        args = parser.parse_args()
                   
        if args.type and args.type == 'validation':
            try:
                user = User.query.filter_by(id = args.id).first()
                if user and user.is_active:
                    return "已经验证成功，请登录。"
                    
                c_sign = get_sha256(get_sha256(current_app.config['SECRET_KEY'] + str(user.id)))
                if args.sign != c_sign:
                    return "Verify Err. 验证失败! "
                
                user.is_active = True
                db.session.commit()
            except Exception as ex:
                print("ex,",ex)
                return "内部错误。"
            
            return "Verify OK.验证成功。恭喜您已经成功的完成邮箱验证，您现在可以使用您的账号来登录本站"
        else:
            return "Verify OK.验证成功。"
   
user_api.add_resource(UserListResource,   '/api/user/')
user_api.add_resource(UserResource,       '/api/user/<int:user_id>/')
user_api.add_resource(JwtLoginResource,   '/api/jwt_login')
user_api.add_resource(PasswordResource,   '/api/user/pwd')
user_api.add_resource(ConstantResource,   '/api/constant') 
user_api.add_resource(UploadImgResource,  '/api/upload/<path>')
user_api.add_resource(AccountRetResource, '/account/result')