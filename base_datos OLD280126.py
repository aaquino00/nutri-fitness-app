import psycopg2
import hashlib
import streamlit as st
from datetime import datetime

# --- CONEXIÓN SEGURA A LA NUBE (SUPABASE) ---
def get_connection():
    # Esta línea busca la URL dentro de tu carpeta .streamlit/secrets.toml
    return psycopg2.connect(st.secrets["DATABASE_URL"])

def inicializar_db():
    """Crea las tablas en PostgreSQL si no existen"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # 1. Tabla Usuarios
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            );
        ''')
        
        # 2. Tabla Comidas 
        c.execute('''
            CREATE TABLE IF NOT EXISTS comidas (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                fecha TIMESTAMP,
                plato TEXT,
                calorias INTEGER,
                proteinas INTEGER,
                carbs INTEGER,
                grasas INTEGER,
                consejo TEXT,
                FOREIGN KEY (user_id) REFERENCES usuarios (username)
            );
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"❌ Error conectando a la Base de Datos: {e}")

# --- SEGURIDAD: HASHING ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- GESTIÓN DE USUARIOS ---
def crear_usuario(username, password):
    try:
        conn = get_connection()
        c = conn.cursor()
        pwd_hash = hash_password(password)
        c.execute("INSERT INTO usuarios (username, password_hash) VALUES (%s, %s)", (username, pwd_hash))
        conn.commit()
        conn.close()
        return True
    except psycopg2.IntegrityError:
        return False # Usuario ya existe
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return False

def login_usuario(username, password):
    try:
        conn = get_connection()
        c = conn.cursor()
        pwd_hash = hash_password(password)
        c.execute("SELECT * FROM usuarios WHERE username = %s AND password_hash = %s", (username, pwd_hash))
        user = c.fetchone()
        conn.close()
        return user is not None
    except Exception:
        return False

# --- GESTIÓN DE DATOS ---
def guardar_comida(user_id, datos_json):
    conn = get_connection()
    c = conn.cursor()
    fecha_hoy = datetime.now()
    
    c.execute('''
        INSERT INTO comidas (user_id, fecha, plato, calorias, proteinas, carbs, grasas, consejo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        user_id,
        fecha_hoy,
        datos_json['plato'],
        datos_json.get('calorias_aprox', 0),
        datos_json.get('proteinas_g', 0),
        datos_json.get('carbohidratos_g', 0),
        datos_json.get('grasas_g', 0),
        datos_json['consejo']
    ))
    conn.commit()
    conn.close()

def ver_historial(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM comidas WHERE user_id = %s ORDER BY fecha DESC", (user_id,))
    filas = c.fetchall()
    conn.close()
    return filas