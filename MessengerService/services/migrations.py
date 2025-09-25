# quick script to create tables
from services.db import engine, Base
from services.models import *
Base.metadata.create_all(bind=engine)