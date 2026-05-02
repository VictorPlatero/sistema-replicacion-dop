import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'clave_maestra_final_v7'

# CONFIGURACIÓN RAILWAY
CONFIGURACIONES_MYSQL = {
    'heladeria': {
        'host': 'switchyard.proxy.rlwy.net',
        'user': 'root', 'password': 'vYKkgsovkdqgsWPJqdeWfLDKEyxeJynf',
        'port': 37240, 'database': 'railway'
    },
    'panaderia': {
        'host': 'hopper.proxy.rlwy.net',
        'user': 'root', 'password': 'PbbhHdkLhWuMRoJAWEJPTgguIhVRYgfz',
        'port': 22262, 'database': 'railway'
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
    return render_template('index.html')

@app.route('/dashboard/<tipo>')
def dashboard(tipo):
    host = CONFIGURACIONES_MYSQL[tipo]['host'] if tipo != 'externo' else session.get('config_externa', {}).get('host', 'Externo')
    return render_template('dashboard.html', tipo=tipo, host=host)

@app.route('/explorar/<tipo>')
def explorar(tipo):
    conn = obtener_conexion(tipo)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tablas = [t[0] for t in cursor.fetchall()]
    conn.close()
    return render_template('explorar.html', tablas=tablas, tipo=tipo)

@app.route('/ver_datos/<tipo>/<tabla>')
def ver_datos(tipo, tabla):
    conn = obtener_conexion(tipo)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {tabla}")
    datos = cursor.fetchall()
    conn.close()
    exito = request.args.get('exito')
    return render_template('ver_datos.html', tipo=tipo, tabla=tabla, datos=datos, exito=exito)

# --- RUTAS DE REPLICACIÓN USANDO PARÁMETROS (?tabla=...) ---

@app.route('/seleccionar_destino/<origen>')
def seleccionar_destino(origen):
    tabla = request.args.get('tabla')
    return render_template('seleccionar_destino.html', origen=origen, tabla=tabla)

@app.route('/confirmar_replica')
def confirmar_replica():
    origen = request.args.get('origen')
    destino = request.args.get('destino')
    tabla = request.args.get('tabla')
    return render_template('confirmar_replica.html', origen=origen, destino=destino, tabla=tabla)

@app.route('/ejecutar_replicacion', methods=['POST'])
def ejecutar_replicacion():
    origen = request.form.get('origen')
    destino = request.form.get('destino')
    tabla = request.form.get('tabla')
    return realizar_transferencia(origen, destino, tabla)

def realizar_transferencia(origen, destino, tabla):
    try:
        conn_or = obtener_conexion(origen)
        cursor_or = conn_or.cursor(dictionary=True)
        cursor_or.execute(f"SHOW COLUMNS FROM {tabla}")
        columnas = [col['Field'] for col in cursor_or.fetchall()]
        cursor_or.execute(f"SELECT * FROM {tabla}")
        filas = cursor_or.fetchall()
        conn_or.close()

        if filas:
            conn_des = obtener_conexion(destino)
            cursor_des = conn_des.cursor()
            cols_str = ", ".join(columnas)
            placeholders = ", ".join(["%s"] * len(columnas))
            update_str = ", ".join([f"{c}=VALUES({c})" for c in columnas])
            sql = f"INSERT INTO {tabla} ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_str}"
            
            for fila in filas:
                valores = tuple(fila[c] for c in columnas)
                cursor_des.execute(sql, valores)
            
            conn_des.commit()
            conn_des.close()
        return redirect(url_for('ver_datos', tipo=origen, tabla=tabla, exito='True'))
    except Exception as e:
        return f"Error crítico: {e}"

@app.route('/formulario_externo')
def formulario_externo():
    origen = request.args.get('origen')
    tabla = request.args.get('tabla')
    return render_template('configurar_externo.html', origen_pendiente=origen, tabla_pendiente=tabla)

@app.route('/conectar_externo', methods=['POST'])
def conectar_externo():
    session['config_externa'] = {
        'host': request.form['host'], 'user': request.form['user'],
        'password': request.form['password'], 'port': request.form['port'],
        'database': request.form['database']
    }
    origen = request.form.get('origen_pendiente')
    tabla = request.form.get('tabla_pendiente')
    
    # Replicación automática si hay un origen y tabla pendientes
    if origen and tabla and origen != "None" and origen != "":
        return realizar_transferencia(origen, 'externo', tabla)
    
    return redirect(url_for('dashboard', tipo='externo'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
