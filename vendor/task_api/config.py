import os
from dotenv import load_dotenv

load_dotenv()

environment = os.environ.get("APP_ENV", "dev")

def get_db_url():
    # Portfolio integration: always use its own database, outside the source API.
    if os.environ.get("PORTFOLIO_DB_URL"):
        return os.environ["PORTFOLIO_DB_URL"]
    if environment == "dev":
        return "sqlite:///app/database.db"
    elif environment == "test":
        return "sqlite:///test.db"

    return ""
