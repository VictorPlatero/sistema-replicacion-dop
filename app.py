# --- ESTA ES LA PARTE QUE HACE LA REPLICACIÓN REAL ---
@app.route('/ejecutar_replicacion', methods=['POST'])
def ejecutar_replicacion():
    origen_tipo = request.form.get('origen')
    destino_tipo = request.form.get('destino') # Asegúrate de pasar 'destino' desde el form
    tabla = "clientes" # Tabla a replicar

    try:
        # 1. Conectar al ORIGEN y sacar los datos
        conn_origen = obtener_conexion(origen_tipo)
        cursor_origen = conn_origen.cursor(dictionary=True)
        cursor_origen.execute(f"SELECT * FROM {tabla}")
        filas = cursor_origen.fetchall()
        conn_origen.close()

        if filas:
            # 2. Conectar al DESTINO e insertar los datos
            conn_destino = obtener_conexion(destino_tipo)
            cursor_destino = conn_destino.cursor()
            
            # Limpiamos la tabla destino para que sea una réplica exacta (opcional)
            # cursor_destino.execute(f"DELETE FROM {tabla}") 

            for fila in filas:
                # Ajustamos la consulta según tus columnas (id, nombre)
                sql = f"INSERT INTO {tabla} (id, nombre) VALUES (%s, %s) ON DUPLICATE KEY UPDATE nombre=%s"
                val = (fila['id'], fila['nombre'], fila['nombre'])
                cursor_destino.execute(sql, val)
            
            conn_destino.commit()
            conn_destino.close()

        # Si todo sale bien, mandamos el aviso de éxito
        return redirect(url_for('ver_datos', tipo=origen_tipo, tabla=tabla, exito='True'))
    
    except Exception as e:
        return f"Error en la replicación física: {e}"
