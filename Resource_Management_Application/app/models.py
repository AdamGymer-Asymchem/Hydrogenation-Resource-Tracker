import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'requests.db'
DEFAULT_EQUIPMENT = [
    (
        '96 parallel reactor',
        '100uL - 400uL, RT - 200C, up to 20 bar',
    ),
    (
        'Endeavour',
        '2mL - 4mL, RT - 200C, up to 30 bar',
    ),
    (
        'Miniclave 1 (20mL - 50mL)',
        '-20C - 100C, up to 12 bar',
    ),
    (
        'Miniclave 1 (50mL - 250mL)',
        '-20C - 100C, up to 12 bar',
    ),
    (
        'Miniclave 2 (20mL - 50mL)',
        '-20C - 100C, up to 12 bar',
    ),
    (
        'Miniclave 2 (50mL - 250mL)',
        '-20C - 100C, up to 12 bar',
    ),
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, name, column_type):
    existing = {
        row['name']
        for row in conn.execute("PRAGMA table_info(experiment_requests)").fetchall()
    }
    if name not in existing:
        conn.execute(f"ALTER TABLE experiment_requests ADD COLUMN {name} {column_type}")


def _ensure_table_column(conn, table_name, name, column_type):
    existing = {
        row['name']
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {column_type}")


def init_db():
    with get_conn() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS experiment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                requester_name TEXT NOT NULL,
                requester_email TEXT,
                department TEXT,
                experiment_type TEXT,
                priority TEXT DEFAULT 'Medium',
                description TEXT,
                requested_by_date TEXT,
                status TEXT DEFAULT 'Submitted',
                additional_metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )

        extra_columns = {
            'request_date': 'TEXT',
            'eln_reference': 'TEXT',
            'timesheet_code': 'TEXT',
            'project_code': 'TEXT',
            'required_date': 'TEXT',
            'time_duration': 'TEXT',
            'equipment_selected': 'TEXT',
            'chemical_transformation': 'TEXT',
            'reagents_solvents': 'TEXT',
            'h_phrases': 'TEXT',
            'coshh': 'TEXT',
            'catalyst_amount': 'TEXT',
            'gas': 'TEXT',
            'theory_uptake': 'TEXT',
            'time_first_sample_hours': 'TEXT',
            'time_additional_samples_hours': 'TEXT',
            'sample_schedule': 'TEXT',
            'sample_size': 'TEXT',
            'diluent': 'TEXT',
            'diluent_volume': 'TEXT',
            'analytical_method': 'TEXT',
            'cleaning_protocol': 'TEXT',
            'assigned_user': 'TEXT',
            'assigned_operator': 'TEXT',
        }

        for name, column_type in extra_columns.items():
            _ensure_column(conn, name, column_type)

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS project_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                project_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )
        _ensure_table_column(conn, 'project_options', 'project_name', 'TEXT')

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS user_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )
        _ensure_table_column(conn, 'user_options', 'email', 'TEXT')

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS operator_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )
        _ensure_table_column(conn, 'operator_options', 'email', 'TEXT')

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                is_operator INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )

        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS equipment_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            '''
        )
        _ensure_table_column(conn, 'equipment_options', 'description', 'TEXT')

        # Seed project dropdown from existing requests (if any).
        conn.execute(
            '''
            INSERT OR IGNORE INTO project_options (name)
            SELECT DISTINCT TRIM(project_code)
            FROM experiment_requests
            WHERE project_code IS NOT NULL AND TRIM(project_code) <> ''
            '''
        )
        conn.execute(
            '''
            UPDATE project_options
            SET project_name = name
            WHERE project_name IS NULL OR TRIM(project_name) = ''
            '''
        )

        conn.execute(
            '''
            INSERT OR IGNORE INTO user_options (name, email)
            SELECT
                TRIM(requester_name) AS name,
                MAX(NULLIF(TRIM(requester_email), '')) AS email
            FROM experiment_requests
            WHERE requester_name IS NOT NULL AND TRIM(requester_name) <> ''
            GROUP BY TRIM(requester_name)
            '''
        )

        conn.execute(
            '''
            UPDATE user_options
            SET email = (
                SELECT MAX(NULLIF(TRIM(er.requester_email), ''))
                FROM experiment_requests er
                WHERE TRIM(er.requester_name) = user_options.name
            )
            WHERE (email IS NULL OR TRIM(email) = '')
              AND EXISTS (
                  SELECT 1
                  FROM experiment_requests er2
                  WHERE TRIM(er2.requester_name) = user_options.name
              )
            '''
        )

        # Seed global users from legacy user list.
        conn.execute(
            '''
            INSERT OR IGNORE INTO users (name, email, is_operator, is_active)
            SELECT name, email, 0, is_active
            FROM user_options
            '''
        )
        conn.execute(
            '''
            UPDATE users
            SET email = COALESCE(
                    NULLIF((SELECT uo.email FROM user_options uo WHERE uo.name = users.name), ''),
                    users.email
                ),
                is_active = COALESCE(
                    (SELECT MAX(uo2.is_active) FROM user_options uo2 WHERE uo2.name = users.name),
                    users.is_active
                )
            WHERE EXISTS (
                SELECT 1
                FROM user_options uo3
                WHERE uo3.name = users.name
            )
            '''
        )

        # Seed equipment list if not already present.
        for name, description in DEFAULT_EQUIPMENT:
            conn.execute(
                '''
                INSERT OR IGNORE INTO equipment_options (name, description, is_active)
                VALUES (?, ?, 1)
                ''',
                (name, description),
            )

        # Seed/update operator users from legacy operator list.
        conn.execute(
            '''
            INSERT OR IGNORE INTO users (name, email, is_operator, is_active)
            SELECT name, email, 1, is_active
            FROM operator_options
            '''
        )
        conn.execute(
            '''
            UPDATE users
            SET email = COALESCE(
                    NULLIF((SELECT oo.email FROM operator_options oo WHERE oo.name = users.name), ''),
                    users.email
                ),
                is_operator = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM operator_options oo2 WHERE oo2.name = users.name
                    ) THEN 1
                    ELSE users.is_operator
                END,
                is_active = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM operator_options oo3
                        WHERE oo3.name = users.name AND oo3.is_active = 1
                    ) OR users.is_active = 1 THEN 1
                    ELSE 0
                END
            WHERE EXISTS (
                SELECT 1
                FROM operator_options oo4
                WHERE oo4.name = users.name
            )
            '''
        )
