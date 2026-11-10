# ReadyZone – Community Disaster Preparedness

Flask app with emergency announcements, evacuation centers, supply inventory, preparedness checklists and relief coordination.

## Run on Windows
Double-click `run.bat`. It creates a virtual environment, installs requirements, opens the browser and starts the app at http://127.0.0.1:5000.

## Run manually
```
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Deploy on Render
1. Push this folder to GitHub.
2. On Render choose **New > Blueprint** (uses `render.yaml`) or **New > Web Service** with
   build command `pip install -r requirements.txt` and start command `gunicorn app:app`.

Note: Render's free tier has no persistent disk, so the SQLite data resets on redeploy or restart.
For permanent data, add a Render Disk and set `DB_PATH=/var/data/readyzone.db`, or move to PostgreSQL.
The app has no login: anyone with the link can post or delete. Add authentication before real-world use.
