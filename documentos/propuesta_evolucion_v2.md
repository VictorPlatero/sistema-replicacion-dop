# Propuesta de Evolución: Arquitectura Híbrida y Sincronización Avanzada

## 1. Refactorización de Código (Arquitectura Modular)

Para soportar transferencias masivas y conectividad híbrida, el monolito actual (`app.py`) debe evolucionar hacia una arquitectura modular basada en servicios. 

### Nueva Estructura de Directorios Sugerida:
```text
sistema-replicacion/
│
├── core/
│   ├── __init__.py
│   ├── connection_manager.py  # Fábrica de conexiones, túneles SSH y pooling
│   ├── replication_engine.py  # Lógica de bulk inserts, resolución de conflictos
│   └── security.py            # Cifrado/descifrado simétrico (Fernet) de credenciales
│
├── utils/
│   ├── __init__.py
│   ├── logger.py              # Configuración de logs estructurados
│   └── schema_analyzer.py     # Inferencia de dependencias (Foreign Keys)
│
├── api/
│   ├── __init__.py
│   └── routes.py              # Endpoints de Flask (limpios de lógica de negocio)
│
├── app.py                     # Punto de entrada y configuración de Flask
└── requirements.txt
```
**Beneficios:** Separación de responsabilidades. `app.py` solo orquesta HTTP, `replication_engine.py` es agnóstico del entorno web y puede ejecutarse mediante workers en segundo plano (ej. Celery/Redis) para procesos largos.

---

## 2. Conectividad Híbrida (Bridge Local-Nube)

Para que la nube alcance bases de datos locales protegidas por firewalls (on-premise), la solución estándar de la industria es establecer un **Túnel SSH Inverso** o usar un **Túnel SSH Directo** si el firewall permite conexiones al puerto 22 de un servidor bastión.

### Snippet: Gestión de Conexión SSH con `sshtunnel`

```python
from sshtunnel import SSHTunnelForwarder
import mysql.connector
from utils.logger import logger

def get_hybrid_connection(db_config, ssh_config=None):
    """
    Establece una conexión MySQL directamente o a través de un túnel SSH.
    """
    if not ssh_config:
        # Conexión directa estándar
        return mysql.connector.connect(**db_config), None

    try:
        tunnel = SSHTunnelForwarder(
            (ssh_config['host'], ssh_config.get('port', 22)),
            ssh_username=ssh_config['user'],
            ssh_password=ssh_config.get('password'),
            ssh_pkey=ssh_config.get('pkey_path'), # Recomendado usar llaves RSA en vez de password
            remote_bind_address=(db_config['host'], int(db_config['port']))
        )
        tunnel.start()
        logger.info(f"Túnel SSH establecido en puerto local {tunnel.local_bind_port}")
        
        # Conectamos MySQL apuntando al puerto local que el túnel ha abierto
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        return conn, tunnel
    except Exception as e:
        logger.error(f"Fallo al establecer túnel Híbrido: {str(e)}")
        raise
```
*(Nota: El objeto `tunnel` debe mantenerse vivo durante la transferencia y llamar a `tunnel.stop()` en el bloque `finally` al terminar).*

---

## 3. Algoritmo de Transferencia (Procesamiento Multitabla, Lotes y Conflictos)

El algoritmo debe respetar la **integridad referencial**. Para esto, las tablas deben ordenarse topológicamente (padres primero, hijos después).

### Snippet: Motor de Replicación Avanzado

```python
import logging

logger = logging.getLogger(__name__)

def replicar_lote_con_conflictos(conn_origen, conn_destino, tablas_ordenadas, batch_size=1000):
    """
    Transfiere datos en lotes y resuelve conflictos usando 'ultima_actualizacion'.
    tablas_ordenadas: Lista de tablas ordenadas por dependencias (Foreing Keys).
    """
    reporte = {"completadas": [], "fallidas": []}
    
    for tabla in tablas_ordenadas:
        try:
            logger.info(f"Iniciando replicación para tabla: {tabla}")
            
            cursor_origen = conn_origen.cursor(dictionary=True)
            cursor_destino = conn_destino.cursor()
            
            # Obtener estructura
            cursor_destino.execute(f"SHOW COLUMNS FROM {tabla}")
            columnas = [col[0] for col in cursor_destino.fetchall()]
            
            # Validar si existe la columna de resolución de conflictos
            usa_conflict_resolution = 'ultima_actualizacion' in columnas
            
            cols_str = ", ".join(columnas)
            placeholders = ", ".join(["%s"] * len(columnas))
            
            # Construir cláusula ON DUPLICATE KEY UPDATE
            if usa_conflict_resolution:
                # Condicional: Solo actualiza si el timestamp que llega (VALUES) es mayor
                update_str = ", ".join([
                    f"{c} = IF(VALUES(ultima_actualizacion) > {tabla}.ultima_actualizacion, VALUES({c}), {tabla}.{c})" 
                    for c in columnas
                ])
            else:
                # Sobrescritura directa
                update_str = ", ".join([f"{c}=VALUES({c})" for c in columnas])
                
            sql_bulk = f"INSERT INTO {tabla} ({cols_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_str}"
            
            # Lectura y Escritura por Lotes (Bulk) para optimizar memoria y ancho de banda
            cursor_origen.execute(f"SELECT * FROM {tabla}")
            
            while True:
                filas = cursor_origen.fetchmany(batch_size)
                if not filas:
                    break # Terminamos de leer esta tabla
                
                lote = [tuple(fila[c] for c in columnas) for fila in filas]
                
                # Ejecutar inserción masiva
                cursor_destino.executemany(sql_bulk, lote)
                conn_destino.commit()
                logger.debug(f"Procesados {len(lote)} registros para {tabla}")
                
            reporte["completadas"].append(tabla)
            logger.info(f"[{tabla}] Replicación exitosa.")
            
        except Exception as e:
            conn_destino.rollback()
            error_msg = f"Error en tabla {tabla}: {str(e)}"
            logger.error(error_msg)
            reporte["fallidas"].append({"tabla": tabla, "error": error_msg})
            # En un entorno estricto con FKs, un fallo en un padre debería detener a los hijos.
            break 
            
    return reporte
```

---

## 4. Seguridad de Credenciales Externas

Actualmente, el sistema confía en la cookie de sesión (`session['config_externa']`). Aunque Flask firma estas cookies para evitar manipulación, **los datos viajan codificados en Base64, no cifrados**. Cualquiera que capture la cookie puede extraer la contraseña de la BD.

### Solución: Cifrado Simétrico (AES)

En lugar de almacenar credenciales en texto plano en la sesión, usaremos `cryptography` para cifrarlas usando una clave maestra que solo reside en el entorno del servidor.

```python
from cryptography.fernet import Fernet
import os

# Esta llave se inyecta por variables de entorno en producción
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(ENCRYPTION_KEY)

def guardar_credenciales_seguras(session_obj, config_dict, clave_sesion='config_ext'):
    import json
    data_str = json.dumps(config_dict)
    # Ciframos el JSON completo de configuración
    token_cifrado = cipher_suite.encrypt(data_str.encode('utf-8'))
    # Guardamos el token cifrado en la cookie
    session_obj[clave_sesion] = token_cifrado.decode('utf-8')

def recuperar_credenciales_seguras(session_obj, clave_sesion='config_ext'):
    import json
    token_cifrado = session_obj.get(clave_sesion)
    if not token_cifrado:
        return None
    try:
        data_str = cipher_suite.decrypt(token_cifrado.encode('utf-8')).decode('utf-8')
        return json.loads(data_str)
    except Exception:
        # Falla si la cookie fue adulterada o la llave cambió
        return None
```
**Ventaja:** Si la cookie es interceptada, el atacante solo verá un hash ininteligible (AES-128). La contraseña real de la base de datos nunca sale del servidor en texto plano.
