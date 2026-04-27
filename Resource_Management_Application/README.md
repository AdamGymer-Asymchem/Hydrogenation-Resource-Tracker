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

## Deployment configuration

Generate local deployment settings:

```powershell
.\configure_deployment.ps1
```

Defaults:
- Database: `requests.db` in this folder
- Port: `17001`
- Portal password: `LotsOfBubbles`

Override any value when needed:

```powershell
.\configure_deployment.ps1 -DbPath "D:\HydrogenationTracker\requests.db" -Port 17001 -PortalPassword "LotsOfBubbles"
```

The script writes `deployment.env`, which is ignored by git. Start the production server with:

```powershell
.\start_app.bat
```

## Notes

- This is intentionally a wireframe for rapid iteration.
- Data is stored in the SQLite file configured by `RESOURCE_TRACKER_DB_PATH`.
- Next step is to define exact fields, roles, and workflow transitions.
