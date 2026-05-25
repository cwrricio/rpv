import os
import firebase_admin
from firebase_admin import credentials, db

def _ensure_firebase():
    if not firebase_admin._apps:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        rtdb_url = os.getenv("RTDB_URL")

        if not cred_path or not rtdb_url:
            raise RuntimeError("Variáveis de ambiente do Firebase não configuradas corretamente")

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": rtdb_url
        })

def ref(path: str):
    _ensure_firebase()
    return db.reference(path)
