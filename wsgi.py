import os
from dotenv import load_dotenv
load_dotenv()

from app import app, init_db, migrate_database

init_db()
try:
    migrate_database()
except Exception:
    pass

application = app

if __name__ == '__main__':
    application.run()
