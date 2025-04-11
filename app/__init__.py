from flask import Flask
from app.db import close_db
import os

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.getcwd(), 'static')) 
    app.config.from_object('app.config.Config')

    from app.controllers.main_controller import main_bp
    app.register_blueprint(main_bp)

    # Cierra la conexión después de cada request
    app.teardown_appcontext(close_db)

    return app
