import os
from flask import Flask, render_template
from core.database import init_db
from api.routes import api_bp

app = Flask(__name__)
app.secret_key = 'clave_maestra_doble_externo_v8' # Mantener para la sesión si se ocupa

# Registrar Blueprint de la API
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    # Inicializar BD SQLite si no existe al primer request
    init_db()
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=True)
