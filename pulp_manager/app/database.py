"""Sets up database engine for interacting with SQL.
Sets up the Base object which all other SQLAlchemy models inherit from
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


env_vars = ["DB_HOSTNAME", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing_env_vars = []
for var in env_vars:
    if var not in os.environ:
        missing_env_vars.append(var)

if len(missing_env_vars) > 0:
    raise EnvironmentError(
        (
            "The following environment variables are missing for the db connection "
            f"{', '.join(missing_env_vars)}"
        )
    )

#pylint: disable=line-too-long
DB_URL = f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOSTNAME')}/{os.getenv('DB_NAME')}"
SQLALCHEMY_DATABASE_URL=f"mysql+pymysql://{DB_URL}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={}, pool_pre_ping=True, pool_recycle=300
)

session = sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)


def get_session():
    """Creates a connection to the database, closes when finished
    """

    try:
        db = session()
        yield db
    finally:
        db.close()
