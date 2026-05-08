import mysql.connector
from sshtunnel import SSHTunnelForwarder
from core.database import get_connection_config

def obtener_conexion_por_id(conn_id):
    """
    Obtiene la conexión leyendo desde SQLite.
    Retorna la conexión MySQL y el túnel SSH (o None si no aplica).
    """
    conf = get_connection_config(conn_id)
    if not conf:
        return None, None
        
    if 'ssh_config' in conf:
        return get_hybrid_connection(conf, conf['ssh_config'])
        
    return _conectar(conf), None

def _conectar(conf):
    return mysql.connector.connect(
        host=conf['host'], user=conf['user'],
        password=conf['password'], port=int(conf['port']),
        database=conf['database']
    )

def get_hybrid_connection(db_config, ssh_config):
    """
    Establece un túnel SSH y luego se conecta a la BD local remota a través del túnel.
    """
    try:
        tunnel = SSHTunnelForwarder(
            (ssh_config['host'], int(ssh_config.get('port', 22))),
            ssh_username=ssh_config['user'],
            ssh_password=ssh_config.get('password'),
            ssh_pkey=ssh_config.get('pkey_path'),
            remote_bind_address=(db_config['host'], int(db_config['port']))
        )
        tunnel.start()
        
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        return conn, tunnel
    except Exception as e:
        print(f"Error establishing SSH tunnel or DB connection: {e}")
        return None, None
