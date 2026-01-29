import streamlit as st
import requests
import json
import base64
import base_datos
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Comando Fitness IA", page_icon="🛡️", layout="wide")

# 🔑 API KEY BLINDADA
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception as e:
    st.error(f"Error crítico: Falta la API Key. {e}")
    st.stop()

# ✅ CORREGIDO: El nombre exacto que funciona siempre
MODELO = "gemini-1.5-flash"

# Inicializar DB y Variables
base_datos.inicializar_db()

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None
if 'mensajes_chat' not in st.session_state:
    st.session_state.mensajes_chat = []

# --- FUNCIONES BACKEND ---

def analizar_ingesta(imagen_bytes=None, texto_usuario=None):
    """Módulo de Visión: Calcula calorías y macros"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    parts = []
    parts.append({"text": """
    Eres un nutricionista experto. Analiza la entrada.
    Responde ESTRICTAMENTE con este JSON: 
    {"plato": "Nombre corto", "calorias_aprox": 0, "proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0, "consejo": "Consejo breve"}
    """})
    
    if texto_usuario:
        parts.append({"text": f"El usuario reporta: {texto_usuario}"})
    if imagen_bytes:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64_image}})
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            texto = response.json()['candidates'][0]['content']['parts'][0]['text']
            clean_json = texto.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        return None
    except Exception:
        return None

def generar_plan_entrenamiento(meta, duracion, nivel, dias_semana, equipo):
    """Módulo Entrenador"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    Actúa como un Entrenador Personal de Élite.
    Crea un PLAN DE ENTRENAMIENTO COMPLETO:
    - Objetivo: {meta}
    - Duración: {duracion}
    - Nivel: {nivel}
    - Frecuencia: {dias_semana} días/sem
    - Equipo: {equipo}
    
    Formato Markdown:
    1. Resumen
    2. Distribución Semanal
    3. Tabla de Ejercicios
    4. Progresión
    5. Consejo de Recuperación
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return "Error al generar el plan."
    except Exception as e:
        return f"Error técnico: {e}"

def chat_especialista(historial, info_comida):
    """Módulo Chat"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contents = []
    sys_prompt = "Eres un Asistente de Salud Integral."
    if info_comida:
        sys_prompt += f" [Dato: La última comida registrada fue {info_comida}]"
    
    contents.append({"role": "user", "parts": [{"text": sys_prompt}]})
    contents.append({"role": "model", "parts": [{"text": "Entendido. ¿En qué puedo ayudarte?"}]})
    
    for msg in historial:
        role_api = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role_api, "parts": [{"text": msg["content"]}]})
        
    payload = {"contents": contents}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return "Error de conexión."
    except Exception:
        return "Error técnico."

# --- VISTAS DEL SISTEMA ---

def mostrar_login():
    """Pantalla de Acceso (Lo primero que se ve)"""
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=100)
        st.markdown("<h1 style='text-align: center;'>Comando Fitness</h1>", unsafe_allow_html=True)
        st.info("🔒 Sistema Protegido. Identifíquese.")
        
        tab_ingreso, tab_registro = st.tabs(["Ingresar", "Registrarse"])
        
        with tab_ingreso:
            u = st.text_input("Usuario", key="u_login")
            p = st.text_input("Contraseña", type="password", key="p_login")
            if st.button("Acceder", type="primary", use_container_width=True):
                if base_datos.login_usuario(u, p):
                    st.session_state.usuario_actual = u
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
        
        with tab_registro:
            nu = st.text_input("Nuevo Usuario", key="u_reg")
            np = st.text_input("Nueva Contraseña", type="password", key="p_reg")
            if st.button("Crear Cuenta", use_container_width=True):
                if base_datos.crear_usuario(nu, np):
                    st.success("Cuenta creada. Ahora puede ingresar.")
                else:
                    st.warning("Ese usuario ya existe.")

def mostrar_app():
    """Panel de Control (Solo visible tras login)"""
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50)