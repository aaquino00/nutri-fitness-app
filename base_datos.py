import streamlit as st
import psycopg2
from datetime import datetime

# --- CONEXIÓN SEGURA ---
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DATABASE_URL"])
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return None

# --- USUARIOS ---
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
        conn.close()

def login_usuario(username, password):
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    conn.close()
    return user is not None

# --- EXPEDIENTES (ONBOARDING) ---
def guardar_expediente(usuario, nombre, sexo, edad, peso, altura, meta, actividad):
    conn = init_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO expedientes (usuario_id, nombre, sexo, edad, peso, altura, meta, nivel_actividad)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (usuario, nombre, sexo, edad, peso, altura, meta, actividad))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error guardando perfil: {e}")
        return False
    finally:
        conn.close()

def obtener_perfil(usuario):
    conn = init_connection()
    if not conn: return None
    cur = conn.cursor()
    cur.execute("SELECT * FROM expedientes WHERE usuario_id = %s", (usuario,))
    # Convertimos la respuesta en un diccionario fácil de usar
    data = cur.fetchone()
    conn.close()
    if data:
        return {
            "nombre": data[1], "sexo": data[2], "edad": data[3],
            "peso": data[4], "altura": data[5], "meta": data[6],
            "actividad": data[7]
        }
    return None

# --- HISTORIAL ---
def guardar_comida(usuario, datos):
    conn = init_connection()
    if not conn: return
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO historial_comidas (usuario_id, plato, calorias, proteinas, carbos, grasas, consejo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (usuario, datos['plato'], datos['calorias_aprox'], datos['proteinas_g'], datos['carbohidratos_g'], datos['grasas_g'], datos['consejo']))
    conn.commit()
    conn.close()

def obtener_historial(usuario):
    conn = init_connection()
    if not conn: return []
    cur = conn.cursor()
    cur.execute("SELECT fecha, plato, calorias, proteinas, carbos, grasas FROM historial_comidas WHERE usuario_id = %s ORDER BY fecha DESC", (usuario,))
    data = cur.fetchall()
    conn.close()
    return data
