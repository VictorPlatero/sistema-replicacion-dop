import os
import psycopg2 # Librería para Supabase/Postgres
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'clave_para_supabase'

# Las configuraciones de Railway se mantienen igual
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
        # CONEXIÓN A SUPABASE (POSTGRES)
        return psycopg2.connect(
            host=conf['host'],
            user=conf['user'],
            password=conf['password'],
            port=conf['port'],
            database=conf['database']
        )
    # CONEXIÓN A RAILWAY (MYSQL)
    return mysql.connector.connect(**CONFIGURACIONES_MYSQL[tipo])

# El resto de tus rutas se mantienen, pero ahora el "Externo"
# podrá recibir los datos de tu proyecto de Supabase.