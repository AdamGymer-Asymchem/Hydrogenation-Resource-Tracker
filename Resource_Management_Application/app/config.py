import os
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = APP_ROOT / 'requests.db'
DEFAULT_PORT = '17001'
DEFAULT_PORTAL_PASSWORD = 'LotsOfBubbles'
ENV_FILE = APP_ROOT / 'deployment.env'


def load_deployment_env(env_file=ENV_FILE):
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        name, value = line.split('=', 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            os.environ.setdefault(name, value)


def get_db_path():
    configured_path = os.getenv('RESOURCE_TRACKER_DB_PATH')
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return DEFAULT_DB_PATH
