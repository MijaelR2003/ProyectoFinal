from flask import request, redirect, url_for, flash
from flask import Blueprint, render_template, abort
from .uploadImage import save_image
from datetime import datetime
from app.db import get_db 
import pymysql
from flask import current_app
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/image/<int:image_id>')
def image_detail(image_id):
    connection = get_db()
    paciente_id = None
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM mod_images WHERE mod_img_id = %s", (image_id,))
            image = cursor.fetchone()
            # Buscar paciente asociado a la imagen
            cursor.execute("SELECT paciente_id FROM paciente_imagen WHERE imagen_id = %s LIMIT 1", (image_id,))
            rel = cursor.fetchone()
            if rel:
                paciente_id = rel['paciente_id']
    finally:
        connection.close()
    if image is None:
        abort(404)
    return render_template('image_detail.html', image=image, paciente_id=paciente_id)

@main_bp.route('/')
def index():
    return render_template('index.html')  # Busca en app/templates/index.html

@main_bp.route('/paciente/form', methods=['GET'])
def patient_form():
    # Formulario vacío para registrar paciente nuevo
    return render_template('patient_form.html', paciente=None)

@main_bp.route('/paciente/form/<int:paciente_id>', methods=['GET'])
def patient_form_id(paciente_id):
    connection = get_db()
    paciente = None
    revision = None
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM mod_paciente WHERE mod_pac_id = %s', (paciente_id,))
            paciente = cursor.fetchone()
            if paciente and paciente.get('mod_pac_form_diag'):
                cursor.execute('SELECT * FROM mod_paciente_revision WHERE mod_pac_rev_id = %s', (paciente['mod_pac_form_diag'],))
                revision = cursor.fetchone()
    finally:
        connection.close()
    return render_template('patient_form.html', paciente=paciente, revision=revision)


@main_bp.route('/paciente/form/<int:image_id>', methods=['GET'])
def patient_form_image(image_id):
    connection = get_db()
    paciente = None
    revision = None
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Buscar paciente relacionado a la imagen (si existe)
            cursor.execute('''
                SELECT p.* FROM mod_paciente p
                JOIN paciente_imagen pi ON p.mod_pac_id = pi.paciente_id
                WHERE pi.imagen_id = %s
                LIMIT 1
            ''', (image_id,))
            paciente = cursor.fetchone()
            # Si hay paciente y tiene revisión asociada, buscar la revisión
            if paciente and paciente.get('mod_pac_form_diag'):
                cursor.execute('SELECT * FROM mod_paciente_revision WHERE mod_pac_rev_id = %s', (paciente['mod_pac_form_diag'],))
                revision = cursor.fetchone()
    finally:
        connection.close()
    return render_template('patient_form.html', paciente=paciente, image_id=image_id, revision=revision)

@main_bp.route('/paciente/save', methods=['POST'])
def save_patient():
    mod_pac_ci = request.form.get('mod_pac_ci')
    mod_pac_nombre = request.form.get('mod_pac_nombre')
    mod_pac_apellido = request.form.get('mod_pac_apellido')
    mod_pac_fecha_nacimiento = request.form.get('mod_pac_fecha_nacimiento')
    mod_pac_telefono = request.form.get('mod_pac_telefono')
    mod_pac_direccion = request.form.get('mod_pac_direccion')
    mod_pac_email = request.form.get('mod_pac_email')
    mod_pac_form_diag = request.form.get('mod_pac_form_diag')
    mod_pac_observaciones = request.form.get('mod_pac_observaciones')
    image_id = request.form.get('image_id')

    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Verifica si el paciente ya existe (por CI)
            cursor.execute("SELECT mod_pac_id FROM mod_paciente WHERE mod_pac_ci = %s", (mod_pac_ci,))
            result = cursor.fetchone()
            if result:
                paciente_id = result['mod_pac_id']
                cursor.execute('''
                    UPDATE mod_paciente SET
                        mod_pac_nombre=%s, mod_pac_apellido=%s, mod_pac_fecha_nacimiento=%s,
                        mod_pac_telefono=%s, mod_pac_direccion=%s, mod_pac_email=%s, mod_pac_form_diag=%s, mod_pac_observaciones=%s
                    WHERE mod_pac_id=%s
                ''', (mod_pac_nombre, mod_pac_apellido, mod_pac_fecha_nacimiento, mod_pac_telefono, mod_pac_direccion, mod_pac_email, mod_pac_form_diag, mod_pac_observaciones, paciente_id))
            else:
                cursor.execute('''
                    INSERT INTO mod_paciente (mod_pac_ci, mod_pac_nombre, mod_pac_apellido, mod_pac_fecha_nacimiento, mod_pac_telefono, mod_pac_direccion, mod_pac_email, mod_pac_form_diag, mod_pac_observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (mod_pac_ci, mod_pac_nombre, mod_pac_apellido, mod_pac_fecha_nacimiento, mod_pac_telefono, mod_pac_direccion, mod_pac_email, mod_pac_form_diag, mod_pac_observaciones))
                paciente_id = cursor.lastrowid

            # Relaciona el paciente con la imagen en la tabla intermedia
            if image_id:
                cursor.execute("SELECT id FROM paciente_imagen WHERE paciente_id=%s AND imagen_id=%s", (paciente_id, image_id))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO paciente_imagen (paciente_id, imagen_id) VALUES (%s, %s)", (paciente_id, image_id))
            connection.commit()
    finally:
        connection.close()

    flash('Datos del paciente guardados correctamente.')
    return redirect(url_for('main.patient_form_id', paciente_id=paciente_id))

@main_bp.route('/pacientes')
def patient_list():
    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM mod_paciente")
            pacientes = cursor.fetchall()
    finally:
        connection.close()
    return render_template('patient_list.html', pacientes=pacientes)

# Eliminar paciente
@main_bp.route('/paciente/eliminar/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 1. Obtener el id del formulario de revisión
            cursor.execute("SELECT mod_pac_form_diag FROM mod_paciente WHERE mod_pac_id=%s", (patient_id,))
            result = cursor.fetchone()
            revision_id = result['mod_pac_form_diag'] if result and result['mod_pac_form_diag'] else None

            # 2. Borrar de paciente_imagen todos los registros con ese paciente_id
            cursor.execute("DELETE FROM paciente_imagen WHERE paciente_id=%s", (patient_id,))

            # 3. Borrar de mod_paciente el paciente
            cursor.execute("DELETE FROM mod_paciente WHERE mod_pac_id=%s", (patient_id,))

            # 4. Si existe, borrar de mod_paciente_revision el registro con el id del formulario de revisión
            if revision_id:
                cursor.execute("DELETE FROM mod_paciente_revision WHERE mod_pac_rev_id=%s", (revision_id,))

            connection.commit()
        flash('Paciente y registros asociados eliminados correctamente.')
    finally:
        connection.close()
    return redirect(url_for('main.patient_list'))

# Editar paciente

@main_bp.route('/paciente/editar_form/<int:paciente_id>', methods=['GET', 'POST'])
def edit_patient_form(paciente_id):
    connection = get_db()
    paciente = None
    revision = None
    if request.method == 'POST':
        # Datos de paciente
        mod_pac_ci = request.form.get('mod_pac_ci')
        mod_pac_nombre = request.form.get('mod_pac_nombre')
        mod_pac_apellido = request.form.get('mod_pac_apellido')
        mod_pac_fecha_nacimiento = request.form.get('mod_pac_fecha_nacimiento')
        mod_pac_telefono = request.form.get('mod_pac_telefono')
        mod_pac_direccion = request.form.get('mod_pac_direccion')
        mod_pac_email = request.form.get('mod_pac_email')
        mod_pac_observaciones = request.form.get('mod_pac_observaciones')
        # Datos de revisión
        mod_pac_rev_dolor_persistente = 1 if request.form.get('mod_pac_rev_dolor_persistente') else 0
        mod_pac_rev_sensibilidad_prolongada = 1 if request.form.get('mod_pac_rev_sensibilidad_prolongada') else 0
        mod_pac_rev_hinchazon = 1 if request.form.get('mod_pac_rev_hinchazon') else 0
        mod_pac_rev_fistula = 1 if request.form.get('mod_pac_rev_fistula') else 0
        mod_pac_rev_cambio_color = 1 if request.form.get('mod_pac_rev_cambio_color') else 0
        mod_pac_rev_dolor_percusion = 1 if request.form.get('mod_pac_rev_dolor_percusion') else 0
        mod_pac_rev_movilidad = 1 if request.form.get('mod_pac_rev_movilidad') else 0
        mod_pac_rev_caries_profunda = 1 if request.form.get('mod_pac_rev_caries_profunda') else 0
        mod_pac_rev_lesion_radiografica = 1 if request.form.get('mod_pac_rev_lesion_radiografica') else 0
        mod_pac_rev_observaciones = request.form.get('mod_pac_rev_observaciones')
        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # Actualizar paciente
                cursor.execute('''
                    UPDATE mod_paciente SET
                        mod_pac_ci=%s,
                        mod_pac_nombre=%s,
                        mod_pac_apellido=%s,
                        mod_pac_fecha_nacimiento=%s,
                        mod_pac_telefono=%s,
                        mod_pac_direccion=%s,
                        mod_pac_email=%s,
                        mod_pac_observaciones=%s
                    WHERE mod_pac_id=%s
                ''', (mod_pac_ci, mod_pac_nombre, mod_pac_apellido, mod_pac_fecha_nacimiento, mod_pac_telefono, mod_pac_direccion, mod_pac_email, mod_pac_observaciones, paciente_id))
                # Obtener id de revisión
                cursor.execute('SELECT mod_pac_form_diag FROM mod_paciente WHERE mod_pac_id=%s', (paciente_id,))
                result = cursor.fetchone()
                revision_id = result['mod_pac_form_diag'] if result and result['mod_pac_form_diag'] else None
                if revision_id:
                    cursor.execute('''
                        UPDATE mod_paciente_revision SET
                            mod_pac_rev_dolor_persistente=%s,
                            mod_pac_rev_sensibilidad_prolongada=%s,
                            mod_pac_rev_hinchazon=%s,
                            mod_pac_rev_fistula=%s,
                            mod_pac_rev_cambio_color=%s,
                            mod_pac_rev_dolor_percusion=%s,
                            mod_pac_rev_movilidad=%s,
                            mod_pac_rev_caries_profunda=%s,
                            mod_pac_rev_lesion_radiografica=%s,
                            mod_pac_rev_observaciones=%s
                        WHERE mod_pac_rev_id=%s
                    ''', (
                        mod_pac_rev_dolor_persistente, mod_pac_rev_sensibilidad_prolongada, mod_pac_rev_hinchazon,
                        mod_pac_rev_fistula, mod_pac_rev_cambio_color, mod_pac_rev_dolor_percusion, mod_pac_rev_movilidad,
                        mod_pac_rev_caries_profunda, mod_pac_rev_lesion_radiografica, mod_pac_rev_observaciones, revision_id
                    ))
                connection.commit()
            flash('Paciente y revisión actualizados correctamente.')
            return redirect(url_for('main.patient_list'))
        finally:
            connection.close()
    # Si GET, renderiza el formulario con datos actuales
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM mod_paciente WHERE mod_pac_id = %s', (paciente_id,))
            paciente = cursor.fetchone()
            if paciente and paciente.get('mod_pac_form_diag'):
                cursor.execute('SELECT * FROM mod_paciente_revision WHERE mod_pac_rev_id = %s', (paciente['mod_pac_form_diag'],))
                revision = cursor.fetchone()
    finally:
        connection.close()
    return render_template('patient_edit_form.html', paciente=paciente, revision=revision)

@main_bp.route('/paciente/editar/<int:paciente_id>', methods=['GET', 'POST'])
def edit_patient(paciente_id):
    connection = get_db()
    if request.method == 'POST':
        mod_pac_ci = request.form.get('mod_pac_ci')
        mod_pac_nombre = request.form.get('mod_pac_nombre')
        mod_pac_apellido = request.form.get('mod_pac_apellido')
        mod_pac_fecha_nacimiento = request.form.get('mod_pac_fecha_nacimiento')
        mod_pac_telefono = request.form.get('mod_pac_telefono')
        mod_pac_direccion = request.form.get('mod_pac_direccion')
        mod_pac_email = request.form.get('mod_pac_email')
        mod_pac_observaciones = request.form.get('mod_pac_observaciones')
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                    UPDATE mod_paciente SET
                        mod_pac_ci=%s,
                        mod_pac_nombre=%s,
                        mod_pac_apellido=%s,
                        mod_pac_fecha_nacimiento=%s,
                        mod_pac_telefono=%s,
                        mod_pac_direccion=%s,
                        mod_pac_email=%s,
                        mod_pac_observaciones=%s
                    WHERE mod_pac_id=%s
                ''', (
                    mod_pac_ci, mod_pac_nombre, mod_pac_apellido, mod_pac_fecha_nacimiento,
                    mod_pac_telefono, mod_pac_direccion, mod_pac_email, mod_pac_observaciones, paciente_id
                ))
                connection.commit()
            flash('Paciente actualizado correctamente.')
            return redirect(url_for('main.patient_form_id', paciente_id=paciente_id))
        finally:
            connection.close()
    else:
        revision = None
        paciente = None
        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # Obtener datos de paciente
                cursor.execute('SELECT * FROM mod_paciente WHERE mod_pac_id=%s', (paciente_id,))
                paciente = cursor.fetchone()
                # Obtener datos de revisión si existe
                if paciente and paciente.get('mod_pac_form_diag'):
                    cursor.execute('SELECT * FROM mod_paciente_revision WHERE mod_pac_rev_id = %s', (paciente['mod_pac_form_diag'],))
                    revision = cursor.fetchone()
        finally:
            connection.close()
        if not paciente:
            flash('Paciente no encontrado.')
            return redirect(url_for('main.patient_list'))
        # Pasar ambos diccionarios al formulario
        return render_template('patient_form.html', paciente=paciente, revision=revision)

# Ver imágenes de un paciente

@main_bp.route('/paciente/<int:paciente_id>/imagenes')
def patient_images(paciente_id):
    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Solo imágenes asociadas a ese paciente
            cursor.execute('''
                SELECT img.* FROM mod_images img
                JOIN paciente_imagen pi ON img.mod_img_id = pi.imagen_id
                WHERE pi.paciente_id = %s
            ''', (paciente_id,))
            images = cursor.fetchall()
    finally:
        connection.close()
    return render_template('images.html', images=images, paciente_id=paciente_id)


@main_bp.route('/uploadImage/<int:paciente_id>', methods=['GET'])
def uploadImage(paciente_id):
    return render_template('uploadImage.html', paciente_id=paciente_id)  # Busca en app/templates/uploadImage.html

@main_bp.route('/buscar')
def search():
    return render_template('search.html') 

@main_bp.route('/perfil')
def profile():
    return render_template('profile.html')  # Busca en app/templates/profile.html

@main_bp.route('/subir_imagen', methods=['POST'])
def subir_imagen():
    paciente_id = request.form.get('paciente_id')
    if 'imagen' not in request.files or not paciente_id:
        flash('No se encontró el archivo o falta el paciente.')
        return redirect(url_for('main.patient_list'))

    file = request.files['imagen']

    if file.filename == '':
        flash('No se seleccionó ninguna imagen.')
        return redirect(url_for('main.patient_images', paciente_id=paciente_id))

    try:
        print(f"[DEBUG] paciente_id recibido: {paciente_id}")
        filename = save_image(file)
        flash('Imagen guardada correctamente: ' + filename)
        file_url = url_for('static', filename='media/uploads/' + filename, _external=True)
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("📁 Imagen guardada:")
        print("🔗 URL:", file_url)
        print("📄 Nombre del archivo:", filename)
        print("📅 Fecha:", fecha_actual)
        db = get_db()
        with db.cursor() as cursor:
            # Insertar imagen en mod_images
            sql_img = """
                INSERT INTO mod_images (mod_img_name, mod_img_path, mod_img_date)
                VALUES (%s, %s, %s)
            """
            print(f"[DEBUG] Ejecutando: {sql_img} con valores ({filename}, media/uploads/{filename}, {fecha_actual})")
            cursor.execute(sql_img, (filename, 'media/uploads/' + filename, fecha_actual))
            imagen_id = cursor.lastrowid
            print(f"[DEBUG] imagen_id insertado: {imagen_id}")
            # Insertar relación paciente-imagen
            sql_rel = "INSERT INTO paciente_imagen (paciente_id, imagen_id) VALUES (%s, %s)"
            print(f"[DEBUG] Ejecutando: {sql_rel} con valores ({paciente_id}, {imagen_id})")
            cursor.execute(sql_rel, (paciente_id, imagen_id))
            db.commit()
            print(f"[DEBUG] Commit realizado correctamente.")
    except Exception as e:
        flash(f'Error al subir la imagen: {str(e)}')
        return redirect(url_for('main.patient_images', paciente_id=paciente_id))

    return redirect(url_for('main.patient_images', paciente_id=paciente_id))


@main_bp.route('/delete_image/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Obtener ruta del archivo
        cursor.execute("SELECT mod_img_path FROM mod_images WHERE mod_img_id = %s", (image_id,))
        result = cursor.fetchone()
        
        if result:
            print("Ruta del archivo:", result)
            img_path = result['mod_img_path']
            print("img_path:", img_path)
            img_path = img_path.lstrip('/')
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            full_path = os.path.join(project_root, 'static', img_path)
            print("Ruta completa del archivo a eliminar:", full_path)
            print("¿Existe el archivo?", os.path.exists(full_path))
            if os.path.exists(full_path):
                os.remove(full_path)
                print("Archivo eliminado correctamente.")
                # Eliminar relación paciente-imagen primero
                cursor.execute("DELETE FROM paciente_imagen WHERE imagen_id = %s", (image_id,))
                # Eliminar registro de la base de datos
                cursor.execute("DELETE FROM mod_images WHERE mod_img_id = %s", (image_id,))
                db.commit()
                print("Registros eliminados de paciente_imagen y mod_images.")
                flash("Imagen eliminada correctamente.")
            else:
                print("El archivo NO existe.")
        else:
            flash("Imagen no encontrada.")
    except Exception as e:
        flash(f"Error al eliminar imagen: {str(e)}")
    
    return redirect(url_for('main.patient_list'))

@main_bp.route('/paciente/revision/save', methods=['POST'])
def save_revision():
    paciente_id = request.form.get('paciente_id')
    mod_pac_rev_dolor_persistente = 1 if request.form.get('mod_pac_rev_dolor_persistente') else 0
    mod_pac_rev_sensibilidad_prolongada = 1 if request.form.get('mod_pac_rev_sensibilidad_prolongada') else 0
    mod_pac_rev_hinchazon = 1 if request.form.get('mod_pac_rev_hinchazon') else 0
    mod_pac_rev_fistula = 1 if request.form.get('mod_pac_rev_fistula') else 0
    mod_pac_rev_cambio_color = 1 if request.form.get('mod_pac_rev_cambio_color') else 0
    mod_pac_rev_dolor_percusion = 1 if request.form.get('mod_pac_rev_dolor_percusion') else 0
    mod_pac_rev_movilidad = 1 if request.form.get('mod_pac_rev_movilidad') else 0
    mod_pac_rev_caries_profunda = 1 if request.form.get('mod_pac_rev_caries_profunda') else 0
    mod_pac_rev_lesion_radiografica = 1 if request.form.get('mod_pac_rev_lesion_radiografica') else 0
    mod_pac_rev_observaciones = request.form.get('mod_pac_rev_observaciones')

    connection = get_db()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # Verificar si el paciente ya tiene una revisión asociada
            cursor.execute('SELECT mod_pac_form_diag FROM mod_paciente WHERE mod_pac_id = %s', (paciente_id,))
            result = cursor.fetchone()
            revision_id = result['mod_pac_form_diag'] if result else None

            if not revision_id:
                # INSERT: el paciente NO tiene revisión, crearla y asociarla
                cursor.execute('''
                    INSERT INTO mod_paciente_revision (
                        mod_pac_rev_dolor_persistente, mod_pac_rev_sensibilidad_prolongada, mod_pac_rev_hinchazon,
                        mod_pac_rev_fistula, mod_pac_rev_cambio_color, mod_pac_rev_dolor_percusion, mod_pac_rev_movilidad,
                        mod_pac_rev_caries_profunda, mod_pac_rev_lesion_radiografica, mod_pac_rev_observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    mod_pac_rev_dolor_persistente, mod_pac_rev_sensibilidad_prolongada, mod_pac_rev_hinchazon,
                    mod_pac_rev_fistula, mod_pac_rev_cambio_color, mod_pac_rev_dolor_percusion, mod_pac_rev_movilidad,
                    mod_pac_rev_caries_profunda, mod_pac_rev_lesion_radiografica, mod_pac_rev_observaciones
                ))
                revision_id = cursor.lastrowid
                # Actualiza el paciente con el id de la revisión
                cursor.execute('UPDATE mod_paciente SET mod_pac_form_diag=%s WHERE mod_pac_id=%s', (revision_id, paciente_id))
            else:
                # UPDATE: el paciente YA tiene revisión, solo actualizar la revisión
                cursor.execute('''
                    UPDATE mod_paciente_revision SET
                        mod_pac_rev_dolor_persistente=%s, mod_pac_rev_sensibilidad_prolongada=%s, mod_pac_rev_hinchazon=%s,
                        mod_pac_rev_fistula=%s, mod_pac_rev_cambio_color=%s, mod_pac_rev_dolor_percusion=%s, mod_pac_rev_movilidad=%s,
                        mod_pac_rev_caries_profunda=%s, mod_pac_rev_lesion_radiografica=%s, mod_pac_rev_observaciones=%s
                    WHERE mod_pac_rev_id=%s
                ''', (
                    mod_pac_rev_dolor_persistente, mod_pac_rev_sensibilidad_prolongada, mod_pac_rev_hinchazon,
                    mod_pac_rev_fistula, mod_pac_rev_cambio_color, mod_pac_rev_dolor_percusion, mod_pac_rev_movilidad,
                    mod_pac_rev_caries_profunda, mod_pac_rev_lesion_radiografica, mod_pac_rev_observaciones,
                    revision_id
                ))
            connection.commit()
    finally:
        connection.close()
    return redirect(url_for('main.patient_list'))