import streamlit as st
import requests
import json
import base64
import base_datos
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Comando Fitness IA", page_icon="🛡️", layout="wide")

# 🔑 TU API KEY
API_KEY = "AIzaSyCnuCXbDxwZHF-pumz00eht6ZUNehISZr8"
MODELO = "gemini-flash-latest"

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
    """Módulo Entrenador: Crea PLANES A LARGO PLAZO"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    Actúa como un Entrenador Personal de Élite especializado en periodización.
    Crea un PLAN DE ENTRENAMIENTO COMPLETO con los siguientes parámetros:
    
    - Objetivo Principal: {meta}
    - Duración del ciclo: {duracion}
    - Nivel del atleta: {nivel}
    - Frecuencia: {dias_semana} días por semana
    - Equipo disponible: {equipo}
    
    Estructura la respuesta en Markdown de la siguiente forma:
    1. **Resumen del Plan**: Explicación breve de la estrategia (ej: Frecuencia 2, Push/Pull/Legs).
    2. **Distribución Semanal**: Qué grupo muscular o enfoque toca cada día (Día 1, Día 2...).
    3. **Tabla de Ejercicios Clave**: Ejercicios, Series y Rangos de Repeticiones sugeridos.
    4. **Progresión**: Cómo aumentar la dificultad a lo largo de los {duracion}.
    5. **Consejo de Recuperación**: Vital para este objetivo.
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
    """Módulo Chat: Consultas libres"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contents = []
    sys_prompt = "Eres un Asistente de Salud Integral. Responde dudas de nutrición y deporte."
    if info_comida:
        sys_prompt += f" [Dato: La última comida registrada del usuario fue {info_comida}]"
    
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

# --- LOGIN ---
def mostrar_login():
    st.title("🔐 Acceso - Comando Fitness")
    t1, t2 = st.tabs(["Ingresar", "Registrarse"])
    with t1:
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar", type="primary"):
            if base_datos.login_usuario(u, p):
                st.session_state.usuario_actual = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")
    with t2:
        nu = st.text_input("Usuario Nuevo")
        np = st.text_input("Contraseña Nueva", type="password")
        if st.button("Crear Cuenta"):
            if base_datos.crear_usuario(nu, np):
                st.success("Cuenta creada exitosamente.")
            else:
                st.warning("El usuario ya existe.")

# --- APP PRINCIPAL ---
def mostrar_app():
    with st.sidebar:
        st.header(f"Hola, {st.session_state.usuario_actual}!")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_actual = None
            st.session_state.mensajes_chat = []
            st.rerun()

    st.title("🛡️ Centro de Control Metabólico")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Escanear Comida", 
        "📅 Planes de Entrenamiento", 
        "💬 Chat Especialista", 
        "📊 Mi Progreso"
    ])

    # --- TAB 1: ESCÁNER ---
    with tab1:
        st.subheader("Registro de Ingesta Diaria")
        col_a, col_b = st.columns(2)
        with col_a:
            archivo = st.file_uploader("Subir Foto", type=["jpg", "png", "jpeg"])
        with col_b:
            texto = st.text_area("Descripción manual", placeholder="Ej: Arroz con atún")

        if st.button("🔍 Analizar y Guardar", type="primary"):
            if archivo or texto:
                with st.spinner("Procesando datos..."):
                    bytes_img = archivo.getvalue() if archivo else None
                    datos = analizar_ingesta(bytes_img, texto)
                    
                    if datos:
                        st.success(f"Plato: {datos['plato']}")
                        base_datos.guardar_comida(st.session_state.usuario_actual, datos)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Kcal", datos['calorias_aprox'])
                        c2.metric("Prot", f"{datos['proteinas_g']}g")
                        c3.metric("Carb", f"{datos['carbohidratos_g']}g")
                        c4.metric("Gras", f"{datos['grasas_g']}g")
                        st.caption(f"Consejo: {datos['consejo']}")
                    else:
                        st.error("Error al analizar.")
            else:
                st.warning("Sube una foto o escribe algo.")

    # --- TAB 2: PLANES (MODIFICADO) ---
    with tab2:
        st.subheader("Diseñador de Planes a Largo Plazo")
        st.info("Configura los parámetros para generar tu ciclo de entrenamiento.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            meta = st.selectbox("Objetivo Principal", ["Perdida de Grasa", "Hipertrofia (Volumen)", "Fuerza Pura", "Resistencia Cardiovascular", "Recomposición Corporal"])
            nivel = st.selectbox("Tu Nivel Actual", ["Principiante (0-6 meses)", "Intermedio (6m - 2 años)", "Avanzado (+2 años)"])
            equipo = st.selectbox("Equipo Disponible", ["Gimnasio Completo", "Mancuernas en Casa", "Calistenia (Peso Corporal)", "Solo Bandas Elásticas"])
            
        with col2:
            duracion = st.select_slider("Duración del Plan", options=["15 Días", "30 Días", "60 Días", "90 Días"])
            dias_semana = st.slider("Días de entrenamiento por semana", 2, 6, 4)

        if st.button("⚡ Generar Plan Maestro", type="primary"):
            with st.spinner(f"Diseñando mesociclo de {duracion} para {meta}..."):
                plan = generar_plan_entrenamiento(meta, duracion, nivel, dias_semana, equipo)
                st.success("¡Plan Generado!")
                st.markdown("---")
                st.markdown(plan)
                
                # Botón opcional para descargar (simulado visualmente)
                st.download_button("💾 Descargar Plan (Texto)", plan, file_name=f"plan_{meta}.md")

    # --- TAB 3: CHAT ---
    with tab3:
        st.subheader("Consultorio Virtual")
        registros = base_datos.ver_historial(st.session_state.usuario_actual)
        info_comida = f"{registros[0][3]} ({registros[0][4]} kcal)" if registros else None
        
        for msg in st.session_state.mensajes_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Consulta a tu coach..."):
            st.session_state.mensajes_chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    resp = chat_especialista(st.session_state.mensajes_chat, info_comida)
                    st.markdown(resp)
            st.session_state.mensajes_chat.append({"role": "assistant", "content": resp})

    # --- TAB 4: PROGRESO ---
    with tab4:
        st.subheader("Estadísticas")
        registros = base_datos.ver_historial(st.session_state.usuario_actual)
        if registros:
            df = pd.DataFrame(registros, columns=['ID', 'User', 'Fecha', 'Plato', 'Calorias', 'Proteinas', 'Carbos', 'Grasas', 'Consejo'])
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            st.line_chart(df, x='Fecha', y='Calorias', color="#FF4B4B")
            st.dataframe(df[['Fecha', 'Plato', 'Calorias']], hide_index=True)
        else:
            st.info("Sin datos registrados.")

# --- ARRANQUE ---
if st.session_state.usuario_actual:
    mostrar_app()
else:
    mostrar_login()