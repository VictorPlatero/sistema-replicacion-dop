import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_replicacion'

# Configuraciones de Railway
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
    replicado = request.args.get('exito') == 'True'
    return render_template('ver_datos.html', tipo=tipo, tabla=tabla, datos=datos, replicado=replicado)

@app.route('/seleccionar_destino/<tipo>')
def seleccionar_destino(tipo):
    return render_template('seleccionar_destino.html', origen=tipo)

@app.route('/confirmar_replica/<origen>/<destino>')
def confirmar_replica(origen, destino):
    return render_template('confirmar_replica.html', origen=origen, destino=destino, tabla="clientes")

@app.route('/ejecutar_replicacion', methods=['POST'])
def ejecutar_replicacion():
    origen = request.form.get('origen')
    # Aquí iría la lógica SQL de replicación real
    return redirect(url_for('ver_datos', tipo=origen, tabla='clientes', exito='True'))

@app.route('/formulario_externo')
def formulario_externo():
    return render_template('configurar_externo.html')

@app.route('/conectar_externo', methods=['POST'])
def conectar_externo():
    session['config_externa'] = {
        'host': request.form['host'], 'user': request.form['user'],
        'password': request.form['password'], 'port': request.form['port'],
        'database': request.form['database']
    }
    return redirect(url_for('dashboard', tipo='externo'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
