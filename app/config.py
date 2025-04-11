import os

class Config:
    SECRET_KEY = 'llave_secreta'
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASEDIR, '..', 'static', 'media', 'uploads')  # ruta a /static/uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Límite de 16 MB si lo deseas

    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'root'
    DB_NAME = 'EndoRayo'
