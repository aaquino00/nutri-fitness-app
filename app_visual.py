import streamlit as st
import requests
import json
import base64
import base_datos
import pandas as pd

# --- CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="Comando Fitness 2.0",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔑 API KEY
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("⚠️ Falta configurar la API Key en secrets.toml")
    st.stop()

# ✅ CAMBIO CLAVE: Usamos la versión específica '001' que es más estable
MODELO = "gemini-1.5-flash-001"

# --- ESTADO DE SESIÓN ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- FUNCIONES DE IA (MOTOR) ---
def consultar_gemini(prompt, imagen=None):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    parts = [{"text": prompt}]
    
    if imagen:
        base64_img = base64.b64encode(imagen).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64_img}})
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # Si falla, devolvemos el error para verlo en pantalla
            return f"ERROR_API: {response.status_code} - {response.text}"
    except Exception as e:
        return f"ERROR_TECNICO: {e}"

def analizar_comida(imagen, perfil):
    prompt = f"""
    Actúa como un nutricionista deportivo.
    Analiza la imagen. Usuario: {perfil['sexo']}, {perfil['edad']} años, meta {perfil['meta']}.
    
    Responde SOLO con este JSON (sin ```json):
    {{
        "plato": "Nombre del plato",
        "calorias_aprox": 0,
        "proteinas_g": 0,
        "carbohidratos_g": 0,
        "grasas_g": 0,
        "consejo": "Consejo breve"
    }}
    """
    respuesta = consultar_gemini(prompt, imagen)
    
    # Verificación de errores
    if respuesta and "ERROR_" in respuesta:
        st.error(respuesta) # Mostrar el error técnico si ocurre
        return None
        
    if respuesta:
        try:
            clean = respuesta.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except:
            st.error("La IA no respondió con el formato correcto.")
            return None
    return None

# --- VISTAS ---

def vista_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🥑 Comando Fitness</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Tu Centro de Control Metabólico Inteligente</p>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔑 Ingresar", "📝 Registrarse"])
        
        with tab1:
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("🚀 Despegar", type="primary", use_container_width=True):
                if base_datos.login_usuario(u, p):
                    st.session_state.usuario = u
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
        
        with tab2:
            nu = st.text_input("Nuevo Usuario")
            np = st.text_input("Nueva Contraseña", type="password")
            if st.button("✨ Crear Cuenta", use_container_width=True):
                if base_datos.crear_usuario(nu, np):
                    st.success("Cuenta creada. Ahora ingresa.")
                else:
                    st.warning("El usuario ya existe.")

def vista_onboarding(usuario):
    st.markdown("## 📋 Ficha de Reclutamiento")
    st.info("Calibrando motor de IA...")
    
    with st.form("form_perfil"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre")
        sexo = col2.selectbox("Sexo", ["Hombre", "Mujer"])
        edad = col1.number_input("Edad", 15, 90, 30)
        altura = col2.number_input("Altura (cm)", 140, 220, 170)
        peso = col1.number_input("Peso (kg)", 40.0, 200.0, 70.0)
        actividad = col2.select_slider("Actividad", ["Sedentario", "Ligero", "Moderado", "Atleta"])
        meta = st.selectbox("Misión", ["Perder Grasa", "Ganar Músculo", "Mantenimiento", "Rendimiento"])
        
        if st.form_submit_button("💾 Guardar Perfil"):
            if base_datos.guardar_expediente(usuario, nombre, sexo, edad, peso, altura, meta, actividad):
                st.rerun()

def vista_dashboard(usuario, perfil):
    with st.sidebar:
        st.title(f"Hola, {perfil['nombre']}!")
        st.caption(f"🎯 Meta: {perfil['meta']}")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario = None
            st.rerun()
            
        st.divider()
        # 🔧 HERRAMIENTA DE DIAGNÓSTICO
        with st.expander("🔧 Diagnóstico Técnico"):
            if st.button("Probar Conexión IA"):
                try:
                    url_test = f"[https://generativelanguage.googleapis.com/v1beta/models?key=](https://generativelanguage.googleapis.com/v1beta/models?key=){API_KEY}"
                    resp = requests.get(url_test)
                    if resp.status_code == 200:
                        modelos = resp.json()
                        st.success("✅ Conexión Exitosa")
                        # Buscamos si el modelo que queremos está en la lista
                        nombres = [m['name'] for m in modelos.get('models', [])]
                        st.write("Modelos disponibles:", nombres)
                    else:
                        st.error(f"Error conectando: {resp.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Tabs principales
    t1, t2, t3, t4 = st.tabs(["📸 Escáner IA", "🏋️ Rutinas", "💬 Coach IA", "📈 Progreso"])
    
    # 1. ESCÁNER
    with t1:
        st.header("Escáner Nutricional")
        img_file = st.file_uploader("Sube una foto de tu comida", type=["jpg", "png", "jpeg"])
        
        if img_file:
            st.image(img_file, width=300)
            if st.button("🔍 Analizar Plato", type="primary"):
                with st.spinner("Analizando con Visión Artificial..."):
                    datos = analizar_comida(img_file.getvalue(), perfil)
                    if datos:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Kcal", datos['calorias_aprox'])
                        c2.metric("Prot", f"{datos['proteinas_g']}g")
                        c3.metric("Carb", f"{datos['carbohidratos_g']}g")
                        c4.metric("Gras", f"{datos['grasas_g']}g")
                        st.success(f"🍽️ {datos['plato']}")
                        st.info(f"💡 {datos['consejo']}")
                        base_datos.guardar_comida(usuario, datos)

    # 2. RUTINAS
    with t2:
        st.header("Generador de Rutinas")
        dias = st.slider("Días de entrenamiento", 1, 7, 3)
        if st.button("Generar Rutina"):
            with st.spinner("Creando plan..."):
                prompt = f"Crea rutina de {dias} días para {perfil['sexo']}, meta {perfil['meta']}."
                rutina = consultar_gemini(prompt)
                st.markdown(rutina)

    # 3. CHAT
    with t3:
        st.header("Chat Coach")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        if prompt := st.chat_input("Consulta..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                resp = consultar_gemini(f"Eres coach. Usuario: {perfil['meta']}. Responde: {prompt}")
                st.write(resp)
            st.session_state.chat_history.append({"role": "assistant", "content": resp})

    # 4. PROGRESO
    with t4:
        st.header("Tus Métricas")
        historial = base_datos.obtener_historial(usuario)
        if historial:
            df = pd.DataFrame(historial, columns=["Fecha", "Plato", "Kcal", "Prot", "Carb", "Gras"])
            st.dataframe(df)
        else:
            st.info("Sin datos aún.")

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.usuario:
    vista_login()
else:
    perfil = base_datos.obtener_perfil(st.session_state.usuario)
    if perfil:
        vista_dashboard(st.session_state.usuario, perfil)
    else:
        vista_onboarding(st.session_state.usuario)
