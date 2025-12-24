import os
import click
from sqlmodel import SQLModel, create_engine, Session

def get_db_path():
    app_dir = click.get_app_dir("kt")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    return os.path.join(app_dir, "kt.db")

db_url = f"sqlite:///{get_db_path()}"
engine = create_engine(db_url)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    init_db()
    return Session(engine)
