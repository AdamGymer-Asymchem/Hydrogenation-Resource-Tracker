import os
from flask import Flask
from .config import DEFAULT_PORTAL_PASSWORD, load_deployment_env
from .models import init_db


def create_app():
    load_deployment_env()
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'wireframe-secret-key')
    app.config['PORTAL_PASSWORD'] = os.getenv('PORTAL_PASSWORD', DEFAULT_PORTAL_PASSWORD)

    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    return app
