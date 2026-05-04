# DATABASE SETUP

1) Install PostgreSQL and make sure it is running.

2) Create database  
   In the terminal, run the following command in the same directory as the README:

       psql -U postgres -f create_db.sql

3) Create a `.env` file with `SECRET_KEY` and `DATABASE_URL` in the same directory as the README.  
   Put the following in the `.env` file:

       SECRET_KEY=some_secret_key_you_make
       DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/flask_auth_db

   - In `SECRET_KEY`, put a secret unique key  
   - In `DATABASE_URL`, replace `yourpassword` with your PostgreSQL user password

---

# RUNNING THE APP

1) Create and activate a Python virtual environment, and install required packages.  
   In the terminal, run the following commands in the same directory as the README:

       python -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt

2) Execute the `run.py` file with Python to run the app.  
   In the terminal, run the following command in the same directory as the README:

       python run.py

3) In a browser, visit `http://127.0.0.1:5000/{location}` where `{location}` is one of the available routes such as `/login` and `/register`.
