import firebase_admin
from firebase_admin import credentials, db
from config.settings import settings

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred, {
            "projectId": settings.PROJECT_ID,
            "databaseURL": settings.RTDB_URL
        })
    return db
