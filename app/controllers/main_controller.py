from flask import request, redirect, url_for, flash
from flask import Blueprint, render_template
from .uploadImage import save_image
from datetime import datetime
from app.db import get_db 
import pymysql

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')  # Busca en app/templates/index.html

@main_bp.route('/imagenes')
def images():
    # Establecer conexión con la base de datos
    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Realizar consulta para obtener las imágenes
            cursor.execute("SELECT * FROM mod_images")
            # Obtener todas las filas de la consulta
            images = cursor.fetchall()
    finally:
        connection.close()
    return render_template('images.html', images=images)  # Busca en app/templates/images.html

@main_bp.route('/uploadImage', methods=['GET'])
def uploadImage():
    return render_template('uploadImage.html')  # Busca en app/templates/uploadImage.html

@main_bp.route('/buscar')
def search():
    return render_template('search.html') 

@main_bp.route('/perfil')
def profile():
    return render_template('profile.html')  # Busca en app/templates/profile.html

@main_bp.route('/subir_imagen', methods=['POST'])
def subir_imagen():
    if 'imagen' not in request.files:
        flash('No se encontró el archivo.')
        return redirect(url_for('main.images'))

    file = request.files['imagen']

    if file.filename == '':
        flash('No se seleccionó ninguna imagen.')
        return redirect(url_for('main.images'))

    try:
        # Guardar la imagen usando la función save_image
        filename = save_image(file)
        flash('Imagen guardada correctamente: ' + filename)

        # Construir la URL del archivo, considerando la nueva ruta 'static/media/uploads/'
        file_url = url_for('static', filename='media/uploads/' + filename, _external=True)

        # Obtener la fecha actual
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print("📁 Imagen guardada:")
        print("🔗 URL:", file_url)
        print("📄 Nombre del archivo:", filename)
        print("📅 Fecha:", fecha_actual)

        # Guardar la imagen en la base de datos
        db = get_db()
        with db.cursor() as cursor:
            sql = """
                INSERT INTO mod_images (mod_img_name, mod_img_path, mod_img_date)
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (filename, 'media/uploads/' + filename, fecha_actual))  # Cambiar a 'media/uploads/'
            db.commit()

    except Exception as e:
        flash(f'Error al subir la imagen: {str(e)}')

    return redirect(url_for('main.images'))
    

