import threading
import uuid
import time
import logging

logger = logging.getLogger(__name__)

# Diccionario en memoria para almacenar el estado y logs de las tareas
TASK_STATUS = {}

def iniciar_transferencia_background(conn_origen_id, conn_destino_id, tablas):
    """Genera un task_id e inicia un hilo para la transferencia."""
    task_id = str(uuid.uuid4())
    TASK_STATUS[task_id] = {
        'status': 'Running',
        'logs': [f"Inicializando transferencia para {len(tablas)} tablas..."],
        'progress': 0,
        'total': len(tablas)
    }
    
    # Importar aquí para evitar importaciones circulares si es necesario
    from core.connection_manager import obtener_conexion_por_id
    
    def worker():
        conn_or, tunnel_or = obtener_conexion_por_id(conn_origen_id)
        conn_des, tunnel_des = obtener_conexion_por_id(conn_destino_id)
        
        if not conn_or or not conn_des:
            TASK_STATUS[task_id]['logs'].append("ERROR: Fallo crítico al conectar origen o destino.")
            TASK_STATUS[task_id]['status'] = 'Failed'
            _cerrar_conexiones(conn_or, tunnel_or, conn_des, tunnel_des)
            return

        try:
            replicar_tablas_con_estado(task_id, conn_or, conn_des, tablas)
            TASK_STATUS[task_id]['status'] = 'Completed'
            TASK_STATUS[task_id]['logs'].append("=== TRANSFERENCIA COMPLETADA ===")
        except Exception as e:
            TASK_STATUS[task_id]['status'] = 'Failed'
            TASK_STATUS[task_id]['logs'].append(f"ERROR FATAL: {str(e)}")
        finally:
            _cerrar_conexiones(conn_or, tunnel_or, conn_des, tunnel_des)

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    
    return task_id

def _cerrar_conexiones(conn_or, tunnel_or, conn_des, tunnel_des):
    if conn_or: conn_or.close()
    if tunnel_or: tunnel_or.stop()
    if conn_des: conn_des.close()
    if tunnel_des: tunnel_des.stop()

def replicar_tablas_con_estado(task_id, conn_origen, conn_destino, tablas, batch_size=1000):
    for i, tabla in enumerate(tablas):
        TASK_STATUS[task_id]['logs'].append(f"-> Procesando tabla: {tabla}")
        try:
            cursor_origen = conn_origen.cursor(dictionary=True)
            cursor_destino = conn_destino.cursor()
            
            cursor_destino.execute(f"SHOW COLUMNS FROM {tabla}")
            columnas = [col[0] for col in cursor_destino.fetchall()]
            usa_conflict_resolution = 'ultima_actualizacion' in columnas
            
            cols_str = ", ".join(columnas)
            placeholders = ", ".join(["%s"] * len(columnas))
            
            if usa_conflict_resolution:
                update_str = ", ".join([
                    f"{c} = IF(VALUES(ultima_actualizacion) > {tabla}.ultima_actualizacion, VALUES({c}), {tabla}.{c})" 
                    for c in columnas
                ])
            else:
                update_str = ", ".join([f"{c}=VALUES({c})" for c in columnas])
                
            sql_bulk = f"INSERT INTO {tabla} ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_str}"
            
            cursor_origen.execute(f"SELECT * FROM {tabla}")
            total_procesados = 0
            
            while True:
                filas = cursor_origen.fetchmany(batch_size)
                if not filas: break
                
                lote = [tuple(fila[c] for c in columnas) for fila in filas]
                cursor_destino.executemany(sql_bulk, lote)
                conn_destino.commit()
                
                total_procesados += len(lote)
                TASK_STATUS[task_id]['logs'].append(f"   {total_procesados} registros insertados/actualizados...")
                
            TASK_STATUS[task_id]['progress'] = i + 1
            TASK_STATUS[task_id]['logs'].append(f"[OK] {tabla} finalizada.")
            
        except Exception as e:
            conn_destino.rollback()
            TASK_STATUS[task_id]['logs'].append(f"[ERROR] Falló la tabla {tabla}: {str(e)}")
            raise e
