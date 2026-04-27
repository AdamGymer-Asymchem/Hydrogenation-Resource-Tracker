# Experiment Request Wireframe

Fast starter app for:
- Requesters submitting experiment requests through a browser form.
- Internal users viewing all submissions in a portal.
- Internal users updating request status and adding metadata.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open:
- Submit form: http://127.0.0.1:5000/submit
- Portal: http://127.0.0.1:5000/portal

## Notes

- This is intentionally a wireframe for rapid iteration.
- Data is stored in local SQLite file `requests.db`.
- Next step is to define exact fields, roles, and workflow transitions.
