import redis
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO()
cors = CORS()
redis_client = None

def init_redis(app):
    global redis_client
    redis_client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)
    return redis_client
