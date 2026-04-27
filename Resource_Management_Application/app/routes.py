from functools import wraps
import csv
from io import BytesIO, StringIO

from flask import (
    Blueprint,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .models import get_conn

bp = Blueprint('main', __name__)

STATUS_OPTIONS = ['Submitted', 'In Progress', 'Completed']


def _get_project_options():
    with get_conn() as conn:
        return conn.execute(
            '''
            SELECT id, name, project_name
            FROM project_options
            WHERE is_active = 1
            ORDER BY name COLLATE NOCASE
            '''
        ).fetchall()


def _get_active_users():
    with get_conn() as conn:
        return conn.execute(
            '''
            SELECT id, name, email, is_operator
            FROM users
            WHERE is_active = 1
            ORDER BY name COLLATE NOCASE
            '''
        ).fetchall()


def _get_active_equipment_options():
    with get_conn() as conn:
        return conn.execute(
            '''
            SELECT id, name, description
            FROM equipment_options
            WHERE is_active = 1
            ORDER BY name COLLATE NOCASE
            '''
        ).fetchall()


def _portal_authenticated() -> bool:
    return bool(session.get('portal_authenticated'))


def require_portal_password(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not _portal_authenticated():
            return redirect(url_for('main.portal_login', next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def _csv_response(rows, filename):
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=['request_id', 'field', 'value'])
    writer.writeheader()

    for row in rows:
        request_id = row['id']
        for field in row.keys():
            writer.writerow(
                {
                    'request_id': request_id,
                    'field': field,
                    'value': row[field],
                }
            )

    response = make_response(out.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _rtf_escape(value):
    text = '' if value is None else str(value)
    return (
        text.replace('\\', r'\\')
        .replace('{', r'\{')
        .replace('}', r'\}')
        .replace('\n', r'\line ')
    )


def _completed_rtf_response(rows, filename):
    lines = [
        r'{\rtf1\ansi\deff0',
        r'{\fonttbl{\f0 Arial;}}',
        r'\fs22',
        r'\b Completed Submission Export\b0\par',
        r'\par',
    ]

    if not rows:
        lines.extend([r'No completed submissions found.\par', r'}'])
    else:
        for row in rows:
            lines.extend(
                [
                    rf'\b Request #{row["id"]}\b0\par',
                    rf'Requestor: {_rtf_escape(row["requester_name"])}\par',
                    rf'Project: {_rtf_escape(row["project_code"])}\par',
                    rf'Timesheet Code: {_rtf_escape(row["timesheet_code"])}\par',
                    rf'Status: {_rtf_escape(row["status"])}\par',
                    rf'Required Date: {_rtf_escape(row["required_date"])}\par',
                    rf'Equipment: {_rtf_escape(row["equipment_selected"])}\par',
                    rf'Chemical Transformation: {_rtf_escape(row["chemical_transformation"])}\par',
                    rf'Reagents/Solvents: {_rtf_escape(row["reagents_solvents"])}\par',
                    rf'Gas: {_rtf_escape(row["gas"])}\par',
                    rf'Theory Uptake: {_rtf_escape(row["theory_uptake"])}\par',
                    rf'Sample Schedule: {_rtf_escape(row["sample_schedule"])}\par',
                    rf'Sample Size: {_rtf_escape(row["sample_size"])}\par',
                    rf'Diluent: {_rtf_escape(row["diluent"])}\par',
                    rf'Diluent Volume: {_rtf_escape(row["diluent_volume"])}\par',
                    rf'Analytical Method: {_rtf_escape(row["analytical_method"])}\par',
                    rf'Cleaning Protocol: {_rtf_escape(row["cleaning_protocol"])}\par',
                    rf'Updated: {_rtf_escape(row["updated_at"])}\par',
                    r'\par',
                    r'\line',
                    r'\par',
                ]
            )
        lines.append(r'}')

    response = make_response('\n'.join(lines))
    response.headers['Content-Type'] = 'application/rtf; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _single_request_rtf_response(row, filename):
    def v(key):
        return _rtf_escape(row[key] if key in row.keys() else '')

    sample_lines = (row['sample_schedule'] or '').splitlines()
    if not sample_lines:
        sample_lines = ['Sample 1: ']

    lines = [
        r'{\rtf1\ansi\deff0',
        r'{\fonttbl{\f0 Arial;}}',
        r'\fs22',
        r'\b Hydrogenation Submission Form (Lab Copy)\b0\par',
        r'\par',
        r'\b Request Details\b0\par',
        rf'Requestor:\tab {v("requester_name")}\tab\tab Request Date:\tab {v("request_date")}\par',
        rf'ELN Reference:\tab {v("eln_reference")}\tab\tab Timesheet Code:\tab {v("timesheet_code")}\par',
        rf'Project Code:\tab {v("project_code")}\tab\tab Required Date:\tab {v("required_date")}\par',
        rf'Time / Duration:\tab {v("time_duration")}\par',
        r'\par',
        r'\b Equipment\b0\par',
        rf'{v("equipment_selected")}\par',
        r'\par',
        r'\b Chemistry\b0\par',
        rf'Chemical transformation:\par {v("chemical_transformation")}\par',
        rf'Reagents / Solvents:\par {v("reagents_solvents")}\par',
        rf'Catalyst and amount:\tab {v("catalyst_amount")}\par',
        rf'Gas and theory uptake:\tab {v("gas")} \tab {v("theory_uptake")}\par',
        r'\par',
        r'\b Safety\b0\par',
        rf'H phrases:\par {v("h_phrases")}\par',
        rf'COSHH:\par {v("coshh")}\par',
        r'\par',
        r'\b Sampling\b0\par',
        r'Samples (Sample No. / Time):\par',
    ]

    for item in sample_lines:
        lines.append(rf'- { _rtf_escape(item) }\par')

    lines.extend(
        [
            rf'Sample preparation:\tab Sample Size {v("sample_size")}\par',
            rf'Diluent:\tab {v("diluent")}\tab Volume:\tab {v("diluent_volume")}\par',
            rf'Analytical method:\par {v("analytical_method")}\par',
            r'\par',
            r'\b Cleaning\b0\par',
            rf'Cleaning solvents / protocol:\par {v("cleaning_protocol")}\par',
            r'\par',
            r'\b Portal Fields\b0\par',
            rf'Status:\tab {v("status")}\tab Assigned Operator:\tab {v("assigned_operator")}\par',
            rf'Last Updated:\tab {v("updated_at")}\par',
            r'}',
        ]
    )

    response = make_response('\n'.join(lines))
    response.headers['Content-Type'] = 'application/rtf; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _single_request_pdf_response(row, filename):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    def value(key):
        raw = row[key] if key in row.keys() else ''
        return '' if raw is None else str(raw)
    eln = value("eln_reference").strip() or f"Request-{value('id')}"

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40

    def section(title):
        nonlocal y
        if y < 80:
            c.showPage()
            y = height - 40
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, title)
        y -= 16

    def line(label, text):
        nonlocal y
        if y < 70:
            c.showPage()
            y = height - 40
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, f"{label}:")
        c.setFont("Helvetica", 10)
        max_chars = 95
        content = text or "N/A"
        chunks = [content[i:i + max_chars] for i in range(0, len(content), max_chars)] or ["N/A"]
        c.drawString(140, y, chunks[0])
        for chunk in chunks[1:]:
            y -= 12
            c.drawString(140, y, chunk)
        y -= 14

    c.setFont("Helvetica-Bold", 15)
    c.drawString(40, y, f"Hydrogenation Submission - ELN {eln}")
    y -= 22

    section("Request Details")
    line("Requestor", value("requester_name"))
    line("Request Date", value("request_date"))
    line("ELN Reference", value("eln_reference"))
    line("Timesheet Code", value("timesheet_code"))
    line("Project Code", value("project_code"))
    line("Required Date", value("required_date"))
    line("Time / Duration", value("time_duration"))

    section("Equipment")
    line("Selected Equipment", value("equipment_selected"))

    section("Chemistry")
    line("Chemical Transformation", value("chemical_transformation"))
    line("Reagents / Solvents", value("reagents_solvents"))
    line("Catalyst and Amount", value("catalyst_amount"))
    line("Gas", value("gas"))
    line("Theory Uptake", value("theory_uptake"))

    section("Safety")
    line("H Phrases", value("h_phrases"))
    line("COSHH", value("coshh"))

    section("Sampling")
    line("Sample Schedule", value("sample_schedule").replace("\n", " | "))
    line("Sample Size", value("sample_size"))
    line("Diluent", value("diluent"))
    line("Diluent Volume", value("diluent_volume"))
    line("Analytical Method", value("analytical_method"))

    section("Cleaning")
    line("Cleaning Protocol", value("cleaning_protocol"))

    section("Portal Fields")
    line("Status", value("status"))
    line("Assigned Operator", value("assigned_operator"))
    line("Updated", value("updated_at"))

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@bp.get('/')
def home():
    return redirect(url_for('main.submit_request'))


@bp.route('/portal/login', methods=['GET', 'POST'])
def portal_login():
    error = None
    next_url = request.args.get('next') or request.form.get('next') or url_for('main.portal')

    if request.method == 'POST':
        submitted_password = request.form.get('password', '')
        if submitted_password == current_app.config.get('PORTAL_PASSWORD'):
            session['portal_authenticated'] = True
            return redirect(next_url)
        error = 'Incorrect password.'

    return render_template('portal_login.html', error=error, next_url=next_url)


@bp.post('/portal/logout')
def portal_logout():
    session.pop('portal_authenticated', None)
    return redirect(url_for('main.portal_login'))


@bp.route('/submit', methods=['GET', 'POST'])
def submit_request():
    if request.method == 'POST':
        form = request.form
        equipment_selected = form.get('equipment_selected', '').strip()
        sample_numbers = [value.strip() for value in form.getlist('sample_numbers[]')]
        sample_times = [value.strip() for value in form.getlist('sample_times[]')]

        requester_name = form.get('requester_name', '').strip()
        chemical_transformation = form.get('chemical_transformation', '').strip()
        project_code = form.get('project_code', '').strip()
        timesheet_code = form.get('timesheet_code', '').strip()
        catalyst_name = form.get('catalyst_name', '').strip()
        catalyst_amount_value = form.get('catalyst_amount_value', '').strip()
        catalyst_amount_unit = form.get('catalyst_amount_unit', '').strip()
        gas_name = form.get('gas_name', '').strip()
        theory_uptake_value = form.get('theory_uptake_value', '').strip()
        theory_uptake_unit = form.get('theory_uptake_unit', '').strip()
        sample_size_value = form.get('sample_size', '').strip()
        sample_size_unit = form.get('sample_size_unit', '').strip()
        diluent_volume_value = form.get('diluent_volume', '').strip()
        diluent_volume_unit = form.get('diluent_volume_unit', '').strip()
        max_rows = max(len(sample_numbers), len(sample_times))
        sample_pairs = []
        for idx in range(max_rows):
            sample_no = sample_numbers[idx] if idx < len(sample_numbers) else ''
            sample_time = sample_times[idx] if idx < len(sample_times) else ''
            if sample_no or sample_time:
                sample_pairs.append((sample_no, sample_time))
        sample_schedule = '\n'.join(
            f"Sample {sample_no or '-'}: {sample_time or '-'}"
            for sample_no, sample_time in sample_pairs
        )
        first_sample_time = sample_pairs[0][1] if len(sample_pairs) > 0 else ''
        additional_sample_time = sample_pairs[1][1] if len(sample_pairs) > 1 else ''
        catalyst_amount = ''
        if catalyst_name or catalyst_amount_value:
            catalyst_amount = (
                f"{catalyst_name or 'Catalyst'}: "
                f"{catalyst_amount_value or '-'} {catalyst_amount_unit or ''}"
            ).strip()
        theory_uptake = ''
        if theory_uptake_value:
            theory_uptake = f"{theory_uptake_value} {theory_uptake_unit or ''}".strip()
        sample_size = ''
        if sample_size_value:
            sample_size = f"{sample_size_value} {sample_size_unit or ''}".strip()
        diluent_volume = ''
        if diluent_volume_value:
            diluent_volume = f"{diluent_volume_value} {diluent_volume_unit or ''}".strip()

        title = chemical_transformation or project_code or timesheet_code or 'Hydrogenation Request'

        with get_conn() as conn:
            conn.execute(
                '''
                INSERT INTO experiment_requests (
                    title, requester_name, requester_email, department,
                    experiment_type, priority, description, requested_by_date,
                    request_date, eln_reference, timesheet_code, project_code,
                    required_date, time_duration, equipment_selected,
                    chemical_transformation, reagents_solvents, h_phrases, coshh,
                    catalyst_amount, gas, theory_uptake,
                    time_first_sample_hours, time_additional_samples_hours, sample_schedule,
                    sample_size, diluent, diluent_volume, analytical_method, cleaning_protocol
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    title,
                    requester_name,
                    form.get('requester_email', ''),
                    form.get('department', ''),
                    'Hydrogenation',
                    'Medium',
                    chemical_transformation,
                    form.get('required_date', ''),
                    form.get('request_date', ''),
                    form.get('eln_reference', ''),
                    timesheet_code,
                    project_code,
                    form.get('required_date', ''),
                    form.get('time_duration', ''),
                    equipment_selected,
                    chemical_transformation,
                    form.get('reagents_solvents', ''),
                    form.get('h_phrases', ''),
                    form.get('coshh', ''),
                    catalyst_amount,
                    gas_name,
                    theory_uptake,
                    first_sample_time,
                    additional_sample_time,
                    sample_schedule,
                    sample_size,
                    form.get('diluent', ''),
                    diluent_volume,
                    form.get('analytical_method', ''),
                    form.get('cleaning_protocol', ''),
                ),
            )
        return redirect(url_for('main.submit_success'))

    return render_template(
        'submit.html',
        equipment_options=_get_active_equipment_options(),
        project_options=_get_project_options(),
        user_options=_get_active_users(),
    )


@bp.get('/submit/success')
def submit_success():
    return render_template('submit_success.html')


@bp.get('/portal')
@require_portal_password
def portal():
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM experiment_requests ORDER BY datetime(created_at) DESC, id DESC'
        ).fetchall()
        project_options = conn.execute(
            '''
            SELECT id, name, project_name, is_active
            FROM project_options
            ORDER BY is_active DESC, name COLLATE NOCASE
            '''
        ).fetchall()
        user_options = conn.execute(
            '''
            SELECT id, name, email, is_operator, is_active
            FROM users
            ORDER BY is_active DESC, name COLLATE NOCASE
            '''
        ).fetchall()
        equipment_options = conn.execute(
            '''
            SELECT id, name, description, is_active
            FROM equipment_options
            ORDER BY is_active DESC, name COLLATE NOCASE
            '''
        ).fetchall()
    return render_template(
        'portal.html',
        submissions=rows,
        status_options=STATUS_OPTIONS,
        project_options=project_options,
        user_options=user_options,
        equipment_options=equipment_options,
        active_user_options=[row['name'] for row in user_options if row['is_active']],
        active_operator_options=[
            row['name'] for row in user_options if row['is_active'] and row['is_operator']
        ],
    )


@bp.post('/portal/projects/add')
@require_portal_password
def add_project_option():
    project_code = request.form.get('project_code', '').strip()
    project_name = request.form.get('project_name', '').strip()
    if project_code:
        with get_conn() as conn:
            conn.execute(
                '''
                INSERT INTO project_options (name, project_name, is_active)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE
                SET is_active = 1,
                    project_name = CASE
                        WHEN excluded.project_name <> '' THEN excluded.project_name
                        ELSE project_options.project_name
                    END
                ''',
                (project_code, project_name),
            )
    return redirect(url_for('main.portal'))


@bp.post('/portal/projects/<int:project_id>/deactivate')
@require_portal_password
def deactivate_project_option(project_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE project_options SET is_active = 0 WHERE id = ?',
            (project_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/projects/<int:project_id>/activate')
@require_portal_password
def activate_project_option(project_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE project_options SET is_active = 1 WHERE id = ?',
            (project_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/projects/<int:project_id>/delete')
@require_portal_password
def delete_project_option(project_id: int):
    with get_conn() as conn:
        conn.execute(
            'DELETE FROM project_options WHERE id = ?',
            (project_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/equipment/add')
@require_portal_password
def add_equipment_option():
    equipment_name = request.form.get('equipment_name', '').strip()
    equipment_description = request.form.get('equipment_description', '').strip()
    if equipment_name:
        with get_conn() as conn:
            conn.execute(
                '''
                INSERT INTO equipment_options (name, description, is_active)
                VALUES (?, ?, 1)
                ON CONFLICT(name) DO UPDATE
                SET is_active = 1,
                    description = CASE
                        WHEN excluded.description <> '' THEN excluded.description
                        ELSE equipment_options.description
                    END
                ''',
                (equipment_name, equipment_description),
            )
    return redirect(url_for('main.portal'))


@bp.post('/portal/equipment/<int:equipment_id>/deactivate')
@require_portal_password
def deactivate_equipment_option(equipment_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE equipment_options SET is_active = 0 WHERE id = ?',
            (equipment_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/equipment/<int:equipment_id>/activate')
@require_portal_password
def activate_equipment_option(equipment_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE equipment_options SET is_active = 1 WHERE id = ?',
            (equipment_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/add')
@require_portal_password
def add_user_option():
    user_name = request.form.get('user_name', '').strip()
    user_email = request.form.get('user_email', '').strip()
    is_operator = 1 if request.form.get('is_operator') == 'on' else 0
    if user_name:
        with get_conn() as conn:
            conn.execute(
                '''
                INSERT INTO users (name, email, is_operator, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(name) DO UPDATE
                SET is_active = 1,
                    is_operator = excluded.is_operator,
                    email = CASE
                        WHEN excluded.email <> '' THEN excluded.email
                        ELSE users.email
                    END
                ''',
                (user_name, user_email, is_operator),
            )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/<int:user_id>/email')
@require_portal_password
def update_user_email(user_id: int):
    user_email = request.form.get('user_email', '').strip()
    with get_conn() as conn:
        conn.execute(
            'UPDATE users SET email = ? WHERE id = ?',
            (user_email, user_id),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/<int:user_id>/operator')
@require_portal_password
def update_user_operator(user_id: int):
    is_operator = 1 if request.form.get('is_operator') == 'on' else 0
    with get_conn() as conn:
        conn.execute(
            'UPDATE users SET is_operator = ? WHERE id = ?',
            (is_operator, user_id),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/<int:user_id>/deactivate')
@require_portal_password
def deactivate_user_option(user_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE users SET is_active = 0 WHERE id = ?',
            (user_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/<int:user_id>/activate')
@require_portal_password
def activate_user_option(user_id: int):
    with get_conn() as conn:
        conn.execute(
            'UPDATE users SET is_active = 1 WHERE id = ?',
            (user_id,),
        )
    return redirect(url_for('main.portal'))


@bp.post('/portal/users/<int:user_id>/delete')
@require_portal_password
def delete_user_option(user_id: int):
    with get_conn() as conn:
        conn.execute(
            'DELETE FROM users WHERE id = ?',
            (user_id,),
        )
    return redirect(url_for('main.portal'))


@bp.get('/portal/export')
@require_portal_password
def export_all_submissions():
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM experiment_requests ORDER BY datetime(created_at) DESC, id DESC'
        ).fetchall()
    return _csv_response(rows, 'portal_submissions.csv')


@bp.get('/portal/export/completed')
@require_portal_password
def export_completed_submissions():
    with get_conn() as conn:
        rows = conn.execute(
            '''
            SELECT *
            FROM experiment_requests
            WHERE status = 'Completed'
            ORDER BY datetime(updated_at) DESC, id DESC
            '''
        ).fetchall()
    return _completed_rtf_response(rows, 'portal_submissions_completed.rtf')


@bp.get('/portal/<int:request_id>/export')
@require_portal_password
def export_submission(request_id: int):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM experiment_requests WHERE id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        return redirect(url_for('main.portal'))

    return _csv_response([row], f'request_{request_id}.csv')


@bp.get('/portal/<int:request_id>/export/word')
@require_portal_password
def export_submission_word(request_id: int):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM experiment_requests WHERE id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        return redirect(url_for('main.portal'))

    return _single_request_rtf_response(row, f'request_{request_id}.rtf')


@bp.get('/portal/<int:request_id>/print')
@require_portal_password
def print_submission(request_id: int):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM experiment_requests WHERE id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        return redirect(url_for('main.portal'))

    sample_lines = [line for line in (row['sample_schedule'] or '').splitlines() if line.strip()]
    return render_template(
        'print_request.html',
        row=row,
        sample_lines=sample_lines,
    )


@bp.get('/portal/<int:request_id>/pdf')
@require_portal_password
def render_submission_pdf(request_id: int):
    with get_conn() as conn:
        row = conn.execute(
            'SELECT * FROM experiment_requests WHERE id = ?',
            (request_id,),
        ).fetchone()

    if row is None:
        return redirect(url_for('main.portal'))

    try:
        import reportlab  # noqa: F401
    except Exception:
        sample_lines = [line for line in (row['sample_schedule'] or '').splitlines() if line.strip()]
        return render_template(
            'print_request.html',
            row=row,
            sample_lines=sample_lines,
        )

    eln = (row['eln_reference'] or '').strip() if 'eln_reference' in row.keys() else ''
    safe_eln = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in eln) or f"request_{request_id}"
    return _single_request_pdf_response(row, f'{safe_eln}.pdf')


@bp.post('/portal/<int:request_id>/update')
@require_portal_password
def update_submission(request_id: int):
    new_status = request.form.get('status', 'Submitted')
    assigned_operator = request.form.get('assigned_operator', '')

    with get_conn() as conn:
        conn.execute(
            '''
            UPDATE experiment_requests
            SET status = ?,
                assigned_operator = ?,
                updated_at = datetime('now')
            WHERE id = ?
            ''',
            (new_status, assigned_operator, request_id),
        )

    return redirect(url_for('main.portal'))


@bp.post('/portal/<int:request_id>/delete')
@require_portal_password
def delete_submission(request_id: int):
    with get_conn() as conn:
        conn.execute(
            'DELETE FROM experiment_requests WHERE id = ?',
            (request_id,),
        )
    return redirect(url_for('main.portal'))
