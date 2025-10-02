VIGILANTEye – AI Live Video Monitoring (Flask)

Overview
VIGILANTEye is an AI-focused authentication and monitoring UI scaffold. It ships with two runnable modes:

- Demo (file storage): No database required. Fastest way to try the app.
- MySQL-backed: Production-ready structure using MySQL via PyMySQL.

Quick start (Demo)
Requirements: Python 3.9+

1) Install dependencies (minimum needed)
   - python -m pip install Flask bcrypt python-dotenv

2) Run the demo
   - python demo_app.py

3) Open the app
   - http://localhost:8080

Demo notes
- Demo stores users in users.json in the project root.
- You can Sign Up, then Log In, and you’ll be redirected to the dashboard.

MySQL mode (app.py)
Requirements: Running MySQL 8 (or compatible), PyMySQL

1) Install driver
   - python -m pip install PyMySQL

2) Configure credentials in config.py (or via environment variables)
   - SECRET_KEY, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

3) Initialize the database
   - python -c "from database import create_database, init_database; create_database(); init_database()"

4) Run the app
   - python app.py
   - Open http://localhost:5000

Troubleshooting
- Unicode in terminal: If your terminal can’t render emoji, remove emoji prints in demo_app.py’s main block or run with UTF-8 enabled.
- Port busy: Change the port in demo_app.py or app.py (app.run(..., port=NEW_PORT)).
- MySQL connection refused: Ensure MySQL service is running and credentials in config.py are correct.

Project structure
- app.py                # Flask app (MySQL-backed)
- demo_app.py           # Flask app (file-based demo)
- database.py           # DB helpers (PyMySQL)
- models.py             # User model (MySQL mode)
- templates/            # Jinja templates
- static/               # CSS/JS assets
- requirements.txt      # Pinned deps (includes PyMySQL)

Branding & UI
- Light, low-contrast color palette with subtle teal accents
- AI monitoring hero, feature cards, dashboard live-feed placeholder, alerts, automations
- Login/Sign Up aligned with homepage style

License
Proprietary – internal use for the VigilantEye project unless stated otherwise.


