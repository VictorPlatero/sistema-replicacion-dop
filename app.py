from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura'

# Configuración de conexiones (Asegúrate de que estas credenciales sean correctas)
def obtener_conexion(tipo):
    if tipo == 'heladeria':
        return mysql.connector.connect(
            host="tu_host_heladeria", 
            user="tu_usuario", 
            password="tu_password", 
            database="heladeria",
            port=3306
        )
    elif tipo == 'panaderia':
        return mysql.connector.connect(
            host="tu_host_panaderia", 
            user="tu_usuario", 
            password="tu_password", 
            database="panaderia",
            port=3306
        )
    elif tipo == 'externo':
        # Usa los datos guardados en la sesión para el servidor manual
        return mysql.connector.connect(
            host=session.get('ext_host'),
            user=session.get('ext_user'),
            password=session.get('ext_pass'),
            database=session.get('ext_db'),
            port=session.get('ext_port')
        )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard/<tipo>')
def dashboard(tipo):
    return render_template('dashboard.html', tipo=tipo)

@app.route('/tablas/<tipo>')
def explorar(tipo):
    # Aquí deberías listar las tablas reales, por ahora dejamos 'clientes'
    return render_template('explorar.html', tipo=tipo, tablas=['clientes'])

@app.route('/ver_datos/<tipo>/<tabla>')
def ver_datos(tipo, tabla):
    conn = obtener_conexion(tipo)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM {tabla}")
    datos = cursor.fetchall()
    conn.close()
    exito = request.args.get('exito')
    return render_template('ver_datos.html', tipo=tipo, tabla=tabla, datos=datos, exito=exito)

@app.route('/seleccionar_destino/<origen>')
def seleccionar_destino(origen):
    return render_template('seleccionar_destino.html', origen=origen)

@app.route('/confirmar_replica/<origen>/<destino>')
def confirmar_replica(origen, destino):
    return render_template('confirmar_replica.html', origen=origen, destino=destino, tabla='clientes')

# --- LÓGICA DE REPLICACIÓN REAL ---
@app.route('/ejecutar_replicacion', methods=['POST'])
def ejecutar_replicacion():
    origen = request.form.get('origen')
    destino = request.form.get('destino')
    tabla = "clientes"

    try:
        # 1. Extraer datos del origen
        conn_origen = obtener_conexion(origen)
        cursor_or = conn_origen.cursor(dictionary=True)
        cursor_or.execute(f"SELECT * FROM {tabla}")
        filas = cursor_or.fetchall()
        conn_origen.close()

        if filas:
            # 2. Insertar en el destino
            conn_dest = obtener_conexion(destino)
            cursor_des = conn_dest.cursor()
            
            for fila in filas:
                # Usamos INSERT IGNORE o ON DUPLICATE KEY para evitar errores de IDs repetidos
                sql = f"INSERT INTO {tabla} (id, nombre) VALUES (%s, %s) ON DUPLICATE KEY UPDATE nombre=%s"
                cursor_des.execute(sql, (fila['id'], fila['nombre'], fila['nombre']))
            
            conn_dest.commit()
            conn_dest.close()

        # Redirigir mostrando el mensaje de éxito
        return redirect(url_for('ver_datos', tipo=origen, tabla=tabla, exito='True'))
    except Exception as e:
        return f"Error crítico al replicar: {e}"

@app.route('/formulario_externo')
def formulario_externo():
    return render_template('configurar_externo.html')

@app.route('/conectar_externo', methods=['POST'])
def conectar_externo():
    session['ext_host'] = request.form.get('host')
    session['ext_user'] = request.form.get('user')
    session['ext_pass'] = request.form.get('password')
    session['ext_port'] = request.form.get('port')
    session['ext_db'] = request.form.get('database')
    return redirect(url_for('dashboard', tipo='externo'))

if __name__ == '__main__':
    app.run(debug=True)
