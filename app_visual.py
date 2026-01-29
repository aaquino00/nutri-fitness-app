import streamlit as st
import psycopg2
from datetime import datetime

# --- CONEXIÓN A LA BASE DE DATOS ---
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"])
    except Exception as e:
        st.error(f"Error de conexión DB: {e}")
        return None

def inicializar_db():
    """Crea la tabla de usuarios si no existe (Solo corre una vez)"""
    conn = init_connection()
    if conn:
        cur = conn.cursor()
        # Tabla Usuarios
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            );
        """)
        # Tabla Historial de Comidas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS historial_comidas (
                id SERIAL PRIMARY KEY,
                usuario_id TEXT REFERENCES usuarios(username),
                fecha TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                plato TEXT,
                calorias INT,
                proteinas FLOAT,
                carbos FLOAT,
                grasas FLOAT,
                consejo TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()

# --- GESTIÓN DE USUARIOS (LOGIN/REGISTRO) ---
def crear_usuario(username, password):
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO usuarios (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        cur.close()
        conn.close()

def login_usuario(username, password):
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user is not None

# --- GESTIÓN DE COMIDAS (HISTORIAL) ---
def guardar_comida(usuario, datos):
    conn = init_connection()
    if not conn: return
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO historial_comidas (usuario_id, plato, calorias, proteinas, carbos, grasas, consejo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (usuario, datos['plato'], datos['calorias_aprox'], datos['proteinas_g'], datos['carbohidratos_g'], datos['grasas_g'], datos['consejo']))
    conn.commit()
    cur.close()
    conn.close()

def ver_historial(usuario):
    conn = init_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT * FROM historial_comidas WHERE usuario_id = %s ORDER BY fecha DESC", (usuario,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# --- NUEVO: GESTIÓN DE EXPEDIENTES (PERFILES) ---
# Estas son las funciones que necesita la nueva actualización

def verificar_expediente(usuario):
    """Revisa si el usuario ya llenó su ficha técnica"""
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    # Verifica si existe la tabla por si acaso
    try:
        cur.execute("SELECT * FROM expedientes WHERE usuario_id = %s", (usuario,))
        resultado = cur.fetchone()
        return resultado is not None
    except:
        return False
    finally:
        cur.close()
        conn.close()

def crear_expediente(usuario, nombre, edad, peso, altura, genero, objetivo, actividad):
    """Crea la ficha técnica inicial del usuario"""
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO expedientes 
            (usuario_id, nombre_completo, edad, peso, altura_cm, genero, objetivo, nivel_actividad)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario, nombre, edad, peso, altura, genero, objetivo, actividad))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando expediente: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def obtener_datos_perfil(usuario):
    """Recupera los datos para alimentar a la IA"""
    conn = init_connection()
    if not conn: return None
    cur = conn.cursor()
    try:
        cur.execute("SELECT edad, peso, altura_cm, objetivo, genero FROM expedientes WHERE usuario_id = %s", (usuario,))
        data = cur.fetchone()
        if data:
            return {
                "edad": data[0], "peso": data[1], "altura": data[2], 
                "objetivo": data[3], "genero": data[4]
            }
        return None
    except:
        return None
    finally:
        cur.close()
        conn.close()