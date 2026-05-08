# Documento de Arquitectura y Diseño - Sistema de Replicación DOP

## 1. Visión General
El proyecto "Sistema de Replicación DOP" es una aplicación web diseñada para facilitar la exploración de bases de datos y la replicación (transferencia) de datos entre múltiples instancias de bases de datos MySQL. 

El sistema actúa como un puente o middleware que se conecta a diferentes nodos (por ejemplo, bases de datos de diferentes sucursales como "heladería" o "panadería", o bases de datos externas configuradas dinámicamente por el usuario) permitiendo copiar tablas completas de un origen a un destino.

## 2. Pila Tecnológica (Tech Stack)
*   **Lenguaje de Programación:** Python 3
*   **Framework Web:** Flask (Microframework web para Python)
*   **Base de Datos (Soportada):** MySQL
*   **Librería de Conexión a BD:** `mysql-connector-python` (Para ejecutar consultas SQL crudas/raw)
*   **Frontend:** HTML5, CSS3 (Vistas renderizadas del lado del servidor usando el motor de plantillas Jinja2)
*   **Servidor de Aplicaciones (Producción):** Gunicorn (Indicado en el `Procfile` y `requirements.txt`)

## 3. Patrón de Arquitectura
El sistema sigue un patrón de diseño **Modelo-Vista-Controlador (MVC)** simplificado:

*   **Modelo (Gestión de Datos):** No utiliza un ORM (Object-Relational Mapping) formal como SQLAlchemy. En su lugar, el acceso y la manipulación de datos se realizan directamente mediante sentencias SQL en crudo dentro del archivo `app.py`. Esto es adecuado para su propósito, ya que necesita realizar operaciones dinámicas sobre tablas (ej. `SHOW TABLES`, `SHOW COLUMNS`, y generadores dinámicos de consultas `INSERT ... ON DUPLICATE KEY UPDATE`).
*   **Vista (Interfaz de Usuario):** Compuesta por plantillas HTML (`.html`) ubicadas en la carpeta `templates/` y estilizadas mediante una hoja de estilos centralizada en `static/style.css`. Flask utiliza Jinja2 para inyectar datos del backend en estas plantillas de manera dinámica antes de enviarlas al navegador del cliente.
*   **Controlador (Lógica de Negocio):** Concentrado principalmente en el archivo `app.py`. Este archivo maneja el enrutamiento HTTP (endpoints como `@app.route('/ejecutar_replicacion')`), procesa las solicitudes del usuario, interactúa con el Modelo (las bases de datos) y decide qué Vista renderizar.

## 4. Estructura del Código y Directorios
El proyecto está estructurado de la siguiente manera:

*   **`app.py`**: El corazón de la aplicación. Contiene la configuración del servidor web Flask, las credenciales, la gestión de sesiones, la definición de las rutas (endpoints) y la lógica central del algoritmo de transferencia/replicación.
*   **`requirements.txt`**: Archivo estándar de Python que lista todas las dependencias necesarias para desplegar el proyecto.
*   **`Procfile`**: Archivo de configuración utilizado por plataformas de despliegue en la nube (PaaS como Render, Railway o Heroku) que indica el comando que se debe ejecutar para iniciar el servidor web (`gunicorn app:app`).
*   **`templates/`**: Directorio reservado por Flask que contiene todas las vistas (archivos HTML). Algunas de las vistas principales incluyen:
    *   `index.html`: Punto de entrada a la aplicación.
    *   `dashboard.html`: Panel de control tras seleccionar una conexión.
    *   `explorar.html`: Vista principal para listar las tablas de una BD específica.
    *   `ver_datos.html`: Interfaz para visualizar en forma de tabla HTML los registros de la BD.
    *   `seleccionar_destino.html` y `confirmar_replica.html`: Interfaces que guían al usuario en el flujo de transferencia de datos.
    *   `configurar_externo.html`: Formulario para registrar dinámicamente credenciales de bases de datos de origen o destino no preconfiguradas.
*   **`static/`**: Directorio donde se almacenan los recursos estáticos públicos, específicamente `style.css` que contiene las reglas de diseño para la interfaz.

## 5. Diseño de Componentes Principales

### 5.1. Gestor de Conexiones a Bases de Datos (`obtener_conexion`)
El sistema maneja las conexiones a las bases de datos a través de una función fábrica que determina cómo conectarse basándose en un parámetro de entrada (`tipo`):
*   **Conexiones Preconfiguradas (Nodos Fijos):** Las conexiones hacia los nodos de prueba ("heladeria" y "panaderia") están configuradas estáticamente (hardcoded) y alojadas en la infraestructura cloud de Railway.
*   **Conexiones Dinámicas (Nodos Externos):** El sistema permite al usuario configurar bases de datos externas proveyendo explícitamente el Host, Usuario, Contraseña, etc. Para mantener un estado de conexión sin la necesidad de requerir un inicio de sesión general o guardar contraseñas en texto plano de manera permanente, el sistema utiliza **sesiones (cookies firmadas por Flask)** para almacenar de manera temporal bajo las claves `config_externa` (origen) y `config_externa_destino` (destino) la configuración de los nodos externos durante el ciclo de vida del uso de la aplicación.

### 5.2. Motor de Replicación de Datos (`realizar_transferencia`)
El proceso de replicar o migrar una tabla completa desde un Origen a un Destino es la función crítica del software y se divide lógicamente en dos fases:

1.  **Fase de Extracción (Lectura del Origen):** 
    *   Se establece conexión a la base de datos de origen.
    *   El sistema inspecciona la estructura (esquema) de la tabla (`SHOW COLUMNS`) de manera dinámica. Esto es vital dado que el sistema está diseñado para replicar *cualquier* tabla, no una con campos predefinidos.
    *   Se extraen los registros (`SELECT * FROM tabla`) usando cursores en modo de diccionario (`dictionary=True`), lo cual facilita el mapeo de los datos en la fase siguiente.
    
2.  **Fase de Carga (Escritura en el Destino):**
    *   Se conecta al nodo destino.
    *   Basado en las columnas leídas en la fase anterior, el controlador construye dinámicamente una cadena SQL de inserción masiva.
    *   **Estrategia de Actualización Continua (Upsert):** Para evitar fallos si un registro ya fue copiado previamente, y asegurar que modificaciones en el origen también se propaguen en el destino en sincronizaciones subsecuentes, el sistema implementa la instrucción condicional de MySQL `ON DUPLICATE KEY UPDATE`. Esto instruye a la base de datos a insertar el registro si su Llave Primaria (Primary Key) no existe o actualizar sus atributos si ya existe.
    *   Por motivos de seguridad y para prevenir ataques de inyección de datos (SQL Injection), los valores se pasan como parámetros variables `%s` (`placeholders`) al método de ejecución del cursor en lugar de ser incrustados directamente en la consulta.

## 6. Flujo Normal de Operación
1.  **Selección de Origen:** El usuario accede a la plataforma y selecciona a qué nodo de base de datos se conectará en primer lugar. Si selecciona un nodo "Externo", se le pedirá ingresar los parámetros de conexión.
2.  **Exploración de la Estructura:** El usuario explora las tablas del nodo y selecciona una tabla específica para ver su contenido.
3.  **Configuración de Destino:** Si el usuario decide que la tabla actual debe ser enviada a otro sistema, este oprime el botón de replicar. El sistema interroga a qué nodo destino se desea enviar la información (pudiendo ser otro nodo preconfigurado o requiriendo credenciales de uno externo nuevo).
4.  **Confirmación y Ejecución:** Tras un paso de confirmación, el sistema ejecuta el pipeline de extracción/carga (Upsert) en segundo plano y, finalmente, le notifica al usuario redirigiéndolo a la vista de datos de la tabla indicando el éxito del procedimiento.
