import os
from flask import Flask
from .models import init_db


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'wireframe-secret-key'
    app.config['PORTAL_PASSWORD'] = os.getenv('PORTAL_PASSWORD', 'change-this-password')

    init_db()

    from .routes import bp
    app.register_blueprint(bp)

    return app
