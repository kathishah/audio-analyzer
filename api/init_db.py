from api.database import engine, Base
from api.models import RecordingSession

def init_db():
    Base.metadata.create_all(bind=engine)
