# decorator.py
import jwt
from datetime import datetime,timedelta
from functools import wraps
from werkzeug.local import LocalProxy
from flask import request, jsonify, _request_ctx_stack, current_app
from flask_mail import Message
from werkzeug.security import generate_password_hash,check_password_hash
from hashlib import sha256
from app import db, mail
    
import os
import random
import string
from slugify import slugify


# LocalProxy的使用说明，很好的一篇文章:https://www.jianshu.com/p/3f38b777a621
current_identity = LocalProxy(lambda: getattr(_request_ctx_stack.top, 'current_identity', None))

def jwt_payload(identity):
    iat = datetime.utcnow()
    exp = iat + timedelta(days=current_app.config.get('JWT_EXPIRATION_DAYS'))
    return {'exp': exp, 'iat': iat, 'identity': identity }


def jwt_encode(identity):
    secret = current_app.config['JWT_SECRET_KEY']
    algorithm = current_app.config['JWT_ALGORITHM']
    required_claims = current_app.config['JWT_REQUIRED_CLAIMS']

    payload = jwt_payload(identity)
    missing_claims = list(set(required_claims) - set(payload.keys()))

    if missing_claims:
        raise RuntimeError('Payload is missing required claims: %s' % ', '.join(missing_claims))

    return jwt.encode(payload, secret, algorithm=algorithm, headers=None)

def jwt_decode(token):
    secret = current_app.config['JWT_SECRET_KEY']
    algorithm = current_app.config['JWT_ALGORITHM']
    leeway = current_app.config['JWT_LEEWAY']

    verify_claims = current_app.config['JWT_VERIFY_CLAIMS']
    required_claims = current_app.config['JWT_REQUIRED_CLAIMS']

    options = {
        'verify_' + claim: True
        for claim in verify_claims
    }
    options.update({
        'require_' + claim: True
        for claim in required_claims
    })

    return jwt.decode(token, secret, options=options, algorithms=[algorithm], leeway=leeway)

def jwt_required(fn):
    @wraps(fn)
    def wapper(*args, **kwargs):
        token = request.cookies.get(current_app.config['JWT_AUTH_COOKIE'],None)
        if not token:
            return jsonify(code='2100', msg='Authorization缺失')

        try:
            payload = jwt_decode(token)
        except jwt.InvalidTokenError as e:
            return jsonify(code='2100', msg=str(e))

        _request_ctx_stack.top.current_identity = payload.get('identity')

        if payload.get('identity') is None:
            return jsonify(code='2100', msg='用户不存在')

        print("jwt_required", payload)
        return fn(*args, **kwargs)
    return wapper


def encrypt(password):
    hash=generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    return hash

def decrypt(hash, password):
    return check_password_hash(hash, password)

def get_sha256(str):
    m = sha256(str.encode('utf-8'))
    return m.hexdigest()
    
def send_mail(subject, message, recipient_list):
    msg = Message(subject, sender = current_app.config['MAIL_USERNAME'],
        recipients = recipient_list)
    msg.html = message
    mail.send(msg)
    return "OK"
    
def get_random_password():
    return ''.join(random.sample(string.ascii_letters+string.digits, 8))
    
def get_upload_file_path(path, upload_name):
    # Generate date based path to put uploaded file.
    date_path = datetime.now().strftime('%Y/%m/%d')

    # Complete upload path (upload_path + date_path).
    upload_path = os.path.join(current_app.config["UPLOAD_URL"], path, date_path)
    full_path = os.path.join(current_app.config["BASE_DIR"], upload_path)
    print(upload_path)
    print(full_path)
    make_sure_path_exist(full_path)
    file_name = slugify_filename(upload_name)
    return os.path.join(full_path, file_name).replace('\\', '/'), os.path.join('/', upload_path, file_name).replace('\\', '/')

def slugify_filename(filename):
    """ Slugify filename """
    name, ext = os.path.splitext(filename)
    slugified = get_slugified_name(name)
    return slugified + ext
    
def get_slugified_name(filename):
    slugified = slugify(filename)
    return slugified or get_random_string()

def get_random_string():
    return ''.join(random.sample(string.ascii_lowercase * 6, 6))

def make_sure_path_exist(path):
    if os.path.exists(path):
        return
    os.makedirs(path, exist_ok=True)