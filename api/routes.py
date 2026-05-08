from flask import Blueprint, request, jsonify
from core.database import get_all_connections, save_connection
from core.connection_manager import obtener_conexion_por_id
from core.replication_engine import iniciar_transferencia_background, TASK_STATUS

api_bp = Blueprint('api', __name__)

@api_bp.route('/connections', methods=['GET'])
def list_connections():
    conns = get_all_connections()
    return jsonify(conns)

@api_bp.route('/connections', methods=['POST'])
def add_connection():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"error": "Falta el nombre de la conexión"}), 400
        
    config = {
        'host': data.get('host'),
        'user': data.get('user'),
        'password': data.get('password'),
        'port': int(data.get('port', 3306)),
        'database': data.get('database')
    }
    
    tipo_conexion = data.get('tipo_conexion', 'remota')
    
    if tipo_conexion == 'local':
        if not data.get('ssh_host') or not data.get('ssh_user') or not data.get('ssh_password'):
            return jsonify({"error": "Faltan credenciales SSH obligatorias para conexión Local"}), 400
            
        config['ssh_config'] = {
            'host': data.get('ssh_host'),
            'user': data.get('ssh_user'),
            'password': data.get('ssh_password'),
            'port': int(data.get('ssh_port', 22))
        }
        
    success, msg = save_connection(name, config)
    if success:
        return jsonify({"message": msg}), 201
    return jsonify({"error": msg}), 400

@api_bp.route('/tables/<int:conn_id>', methods=['GET'])
def list_tables(conn_id):
    conn, tunnel = obtener_conexion_por_id(conn_id)
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        return jsonify(tables)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
        if tunnel: tunnel.stop()

@api_bp.route('/transfer', methods=['POST'])
def start_transfer():
    data = request.json
    origen_id = data.get('origen_id')
    destino_id = data.get('destino_id')
    tablas = data.get('tablas')
    
    if not origen_id or not destino_id or not tablas:
        return jsonify({"error": "Faltan parámetros (origen_id, destino_id, tablas)"}), 400
        
    task_id = iniciar_transferencia_background(origen_id, destino_id, tablas)
    return jsonify({"task_id": task_id, "message": "Transferencia iniciada"})

@api_bp.route('/transfer_status/<task_id>', methods=['GET'])
def transfer_status(task_id):
    status = TASK_STATUS.get(task_id)
    if not status:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(status)
