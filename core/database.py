import sqlite3
import os
from core.security import encrypt_dict, decrypt_dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'middleware.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            config_encrypted TEXT NOT NULL
        )
    ''')
    
    # Insertar conexiones por defecto si no existen
    cursor.execute("SELECT count(*) FROM connections")
    if cursor.fetchone()[0] == 0:
        default_conns = [
            ('heladeria', {
                'host': 'switchyard.proxy.rlwy.net', 'user': 'root', 
                'password': 'vYKkgsovkdqgsWPJqdeWfLDKEyxeJynf', 
                'port': 37240, 'database': 'railway'
            }),
            ('panaderia', {
                'host': 'hopper.proxy.rlwy.net', 'user': 'root', 
                'password': 'PbbhHdkLhWuMRoJAWEJPTgguIhVRYgfz', 
                'port': 22262, 'database': 'railway'
            })
        ]
        for name, conf in default_conns:
            cursor.execute("INSERT INTO connections (name, config_encrypted) VALUES (?, ?)", 
                           (name, encrypt_dict(conf)))
    
    conn.commit()
    conn.close()

def save_connection(name, config_dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO connections (name, config_encrypted) VALUES (?, ?)", 
                       (name, encrypt_dict(config_dict)))
        conn.commit()
        return True, "Conexión guardada exitosamente."
    except sqlite3.IntegrityError:
        return False, "El nombre de la conexión ya existe."
    finally:
        conn.close()

def get_all_connections():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, config_encrypted FROM connections")
    rows = cursor.fetchall()
    conn.close()
    
    connections = []
    for row in rows:
        conf = decrypt_dict(row[2])
        if conf:
            # Quitamos los passwords para la vista pública
            conf_public = {k: v for k, v in conf.items() if 'password' not in k}
            connections.append({
                'id': row[0],
                'name': row[1],
                'details': conf_public
            })
    return connections

def get_connection_config(conn_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT config_encrypted FROM connections WHERE id = ?", (conn_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return decrypt_dict(row[0])
    return None
