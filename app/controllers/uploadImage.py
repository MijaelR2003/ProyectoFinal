import os
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    """
    Guarda una imagen en la carpeta configurada y retorna el nombre del archivo guardado.
    Lanza ValueError si el archivo no es válido.
    """
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = current_app.config['UPLOAD_FOLDER']
        
        # Crea la carpeta si no existe
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)

        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        return filename
    else:
        raise ValueError("Archivo no permitido.")
