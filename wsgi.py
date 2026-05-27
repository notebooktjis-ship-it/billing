import os
from dotenv import load_dotenv
load_dotenv()

from app import app as application

if __name__ == '__main__':
    application.run()
