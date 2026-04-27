import os
from app import create_app
from app.config import DEFAULT_PORT, load_deployment_env


load_deployment_env()

app = create_app()

if __name__ == '__main__':
    app.run(
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', DEFAULT_PORT)),
        debug=os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'},
    )
