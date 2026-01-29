import streamlit as st
import requests
import json
import base64
import base_datos
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Comando Fitness IA", page_icon="🛡️", layout="wide")

# 🔑 API KEY
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception as e:
    st.error(f"Error de configuración: Falta la API Key en secrets.toml. {e}")
    st.stop()

# ✅ MODELO CORREGIDO (Este es el que funciona seguro)
MODELO = "gemini-1.5-flash"

# Inicializar DB y Variables
base_datos.inicializar_db()

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None
if 'mensajes_chat' not in st.session_state:
    st.session_state.mensajes_chat = []

# --- FUNCIONES BACKEND ---

def analizar_ingesta(imagen_bytes=None, texto_usuario=None, perfil_usuario=None):
    """Módulo de Visión: Calcula calorías y macros"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contexto = """
    Eres un nutricionista experto. Analiza la imagen.
    Responde ÚNICAMENTE con un objeto JSON válido.
    NO uses markdown, ni ```json, ni texto extra. Solo las llaves { }.
    
    Formato:
    {
        "plato": "Nombre corto del plato",
        "calorias_aprox": 0,
        "proteinas_g": 0,
        "carbohidratos_g": 0,
        "grasas_g": 0,
        "consejo": "Consejo breve y directo"
    }
    """
    
    if perfil_usuario:
        contexto += f" Usuario: {perfil_usuario['genero']}, Objetivo: {perfil_usuario['objetivo']}."

    parts = [{"text": contexto}]
    
    if texto_usuario:
        parts.append({"text": f"Nota: {texto_usuario}"})
    if imagen_bytes:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64_image}})
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code != 200:
            st.error(f"Error de IA ({response.status_code}): {response.text}")
            return None

        texto_raw = response.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = texto_raw.replace('```json', '').replace('```', '').strip()
        
        if "{" in clean_json:
            clean_json = clean_json[clean_json.find("{"):clean_json.rfind("}")+1]
            
        return json.loads(clean_json)
        
    except Exception as e:
        st.error(f"No pudimos leer la respuesta. Intente otra foto.")
        return None

def generar_plan_entrenamiento(meta, duracion, nivel, dias_semana, equipo, perfil=None):
    """Módulo Entrenador"""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    datos_extra = ""
    if perfil:
        datos_extra = f"(Usuario: {perfil['genero']}, {perfil['edad']} años, Peso {perfil['peso']}kg)"

    prompt = f"""
    Crea un PLAN DE ENTRENAMIENTO (Formato Markdown):
    - Perfil: {datos_extra}
    - Objetivo: {meta}
    - Duración: {duracion}
    - Nivel: {nivel}
    - Frecuencia: {dias_semana} días/sem
    - Equipo: {equipo}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        return "Error al generar el plan."
    except Exception as e:
        return f"Error técnico: {e}"

def chat_especialista(historial, info_comida, perfil=None):
    """Módulo Chat"""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contents = []