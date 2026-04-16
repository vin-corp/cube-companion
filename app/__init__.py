from flask import Flask
from flask_migrate import Migrate
from .extensions import db, login_manager
from .auth import auth
from .routes import main
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth)
    app.register_blueprint(main)

    migrate = Migrate(app, db)

    return app
