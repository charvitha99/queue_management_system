
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from the .env file")

engine = create_engine(database_url)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        print("Database connection successful!")
        print(result.scalar())
except Exception as error:
    print("Database connection failed.")
    print(f"Error: {error}")
finally:
    engine.dispose()
