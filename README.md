# Project Description and Purpose

The purpose of this project is to create a comprehensive web-application for Magic The Gathering to allow users to create and manage cubes and custom cards.

Users are able to create cubes comprised of both official cards, sourced from Scryfall and custom cards created within the application.

Furthermore users can share any cubes or custom cards they create allowing authenticated users to create copies.

---

# Technologies, Frameworkds, and Dependencies

## Backend
- Python 3.12 - primary language
- Flask 3.1.3 - web framework
- Flask-Login 0.6.3 - user session managment
- Flask-SQLAlchemy 3.1.1 - ORM layer for database
- Flask-Migrate 4.1.0 - database migrations
- Werkzeug 3.1.7 - password hashing
- requests 2.32.3 - HTTP client to call Scryfall API
- python-dotenv 1.2.2 - loads secrets from .env file

## Database
- PostgreSQLL - production database
- psycopg2-binary 2.9.11 PostgreSQL driver for Python
- SQLAlchemy 2.0.48 - ORM toolkit
- Alembiic 1.18.4 - migration engine

## Frontend
- Jinja2 3.1.6 - server-side html templating
- Plain CSS - UI styling

## External Services
- Scryfall API - Official MTG card API

---

# Setup

## Prerequisites

Make sure the following are installed before you begin:

- **Python 3.12 or newer** - [python.org/downloads](https://www.python.org/downloads/)
- **PostgreSQL 14 or newer** - [postgresql.org/download](https://www.postgresql.org/download/)
- **Git** - [git-scm.com](https://git-scm.com/)

To verify your versions:

```bash
python --version
psql --version
git --version
```

---

## Step 1 - Clone the Repository

```bash
git clone <repository-url>
cd cube-companion
```

---

## Step 2 - Create and Activate a Virtual Environment

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```bat
python -m venv .venv
.venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your terminal prompt should show `(.venv)` to confirm the environment is active.

---

## Step 3 - Install Dependencies

With the virtual environment active:

```bash
pip install -r requirements.txt
```

---

## Step 4 - Set Up PostgreSQL

### Start the PostgreSQL service

**Mac (Homebrew):**
```bash
brew services start postgresql
```

**Linux (systemd):**
```bash
sudo systemctl start postgresql
```

**Windows:** PostgreSQL runs as a Windows Service automatically after installation. You can also start it from **pgAdmin** or the **Services** panel.

### Create the database

Run the following from the project root directory:

```bash
psql -U postgres -f create_db.sql
```

If your PostgreSQL username is not `postgres`, substitute it:

```bash
psql -U <your-postgres-username> -f create_db.sql
```

---

## Step 5 - Configure Environment Variables

Create a file named `.env` in the project root (same folder as `README.md`):

```
SECRET_KEY=replace_with_a_long_random_string
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/flask_auth_db
```

- **`SECRET_KEY`** - any long, random string. On Mac/Linux you can generate one with `openssl rand -hex 32`.
- **`DATABASE_URL`** - replace `yourpassword` with your PostgreSQL user's password. Update `postgres` if your username differs.

---

## Step 6 - Run the Application

With the virtual environment still active:

```bash
python run.py
```

On first launch this automatically creates all required database tables. You should see:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

---

## Step 7 —- Open the App

Navigate to `http://127.0.0.1:5000` in your browser.

- Register a new account at `/register`
- Log in at `/login`
- Manage your cubes from the dashboard at `/dashboard`

---

## Stopping the App

Press `Ctrl + C` in the terminal to stop the server. To deactivate the virtual environment:

```bash
deactivate
```

---

## Database Migrations (for developers)

If you pull changes that modify the database schema, apply them with:

```bash
flask db upgrade
```

To generate a new migration after editing `app/models.py`:

```bash
flask db migrate -m "describe your change"
flask db upgrade
```
