import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_replicacion'

# Configuraciones de Railway (Heladería y Panadería)
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
        if not conf:
            return None
        # Conexión a MySQL Externo (Ej: BD Aternos en Railway)
        return mysql.connector.connect(
            host=conf['host'],
            user=conf['user'],
            password=conf['password'],
            port=int(conf['port']),
            database=conf['database']
        )
    # Conexión a Railway Predeterminadas
    return mysql.connector.connect(**CONFIGURACIONES_MYSQL[tipo])

# --- RUTAS ---

@app.route('/')
def index():
    # Esta ruta elimina el error "Not Found"
    return render_template('index.html')

@app.route('/conectar_externo', methods=['POST'])
def conectar_externo():
    # Guarda la configuración manual en la sesión
    session['config_externa'] = {
        'host': request.form['host'],
        'user': request.form['user'],
        'password': request.form['password'],
        'port': request.form['port'],
        'database': request.form['database']
    }
    return redirect(url_for('ver_tablas', tipo='externo'))

@app.route('/tablas/<tipo>')
def ver_tablas(tipo):
    try:
        conn = obtener_conexion(tipo)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tablas = [t[0] for t in cursor.fetchall()]
        conn.close()
        return render_template('tablas.html', tablas=tablas, tipo=tipo)
    except Exception as e:
        return f"Error al conectar: {e}"

@app.route('/replicar', methods=['POST'])
def replicar():
    origen = request.form['origen']
    destino = 'externo'
    tabla = request.form['tabla']

    try:
        # 1. Leer datos del origen
        conn_ori = obtener_conexion(origen)
        cur_ori = conn_ori.cursor(dictionary=True)
        cur_ori.execute(f"SELECT * FROM {tabla}")
        datos = cur_ori.fetchall()
        
        # Obtener estructura de la tabla
        cur_ori.execute(f"SHOW CREATE TABLE {tabla}")
        create_sql = cur_ori.fetchone()['Create Table']
        conn_ori.close()

        # 2. Insertar en destino
        conn_des = obtener_conexion(destino)
        cur_des = conn_des.cursor()
        
        # Crear tabla si no existe
        cur_des.execute(create_sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS'))
        
        if datos:
            columnas = datos[0].keys()
            placeholders = ", ".join(["%s"] * len(columnas))
            sql_insert = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
            
            for fila in datos:
                cur_des.execute(sql_insert, list(fila.values()))
        
        conn_des.commit()
        conn_des.close()
        return "¡Replicación exitosa!"
    except Exception as e:
        return f"Error en la replicación: {e}"

if __name__ == '__main__':
    # Render usa el puerto 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
