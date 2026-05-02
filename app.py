import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_replicacion'

# Tus conexiones de Railway
CONFIGURACIONES_MYSQL = {
    'heladeria': {
        'host': 'switchyard.proxy.rlwy.net',
        'user': 'root',
        'password': 'vYKkgsovkdqgsWPJqdeWfLDKEyxeJynf',
        'port': 37240,
        'database': 'railway'
    },
    'panaderia': {
        'host': 'hopper.proxy.rlwy.net',
        'user': 'root',
        'password': 'PbbhHdkLhWuMRoJAWEJPTgguIhVRYgfz',
        'port': 22262,
        'database': 'railway'
    }
}

def obtener_conexion(tipo):
    if tipo == 'externo':
        conf = session.get('config_externa')
        if not conf: return None
        return mysql.connector.connect(
            host=conf['host'], user=conf['user'],
            password=conf['password'], port=int(conf['port']),
            database=conf['database']
        )
    return mysql.connector.connect(**CONFIGURACIONES_MYSQL[tipo])

@app.route('/')
def index():
    # Usamos tu archivo index.html que es el que tiene los botones azules
    return render_template('index.html')

@app.route('/tablas/<tipo>')
def ver_tablas(tipo):
    try:
        conn = obtener_conexion(tipo)
        if not conn: return redirect(url_for('formulario_externo'))
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tablas = [t[0] for t in cursor.fetchall()]
        conn.close()
        # USAMOS TU ARCHIVO explorar.html
        return render_template('explorar.html', tablas=tablas, tipo=tipo)
    except Exception as e:
        return f"Error de conexión: {e}"

@app.route('/formulario_externo')
def formulario_externo():
    # USAMOS TU ARCHIVO configurar_externo.html
    return render_template('configurar_externo.html')
