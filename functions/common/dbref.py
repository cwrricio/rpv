from config.firebase_admin_init import init_firebase


def _db():
    return init_firebase()


def ref(path: str):
    return _db().reference(path)
