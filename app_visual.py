import streamlit as st
import requests
import json
import base64
import base_datos
import pandas as pd

# --- CONFIGURACIÓN VISUAL (ALEGRE Y PROFESIONAL) ---
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

MODELO = "gemini-1.5-flash"

# --- ESTADO DE SESIÓN ---
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# --- FUNCIONES DE IA (MOTOR) ---
def consultar_gemini(prompt, imagen=None):
    # Aseguramos que el modelo sea el correcto
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    parts = [{"text": prompt}]
    
    if imagen:
        base64_img = base64.b64encode(imagen).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64_img}})
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # --- AQUÍ ESTÁ EL CHIVATO (DEBUG) ---
        if response.status_code != 200:
            st.error(f"🚨 Error de IA ({response.status_code}):")
            st.code(response.text) # Muestra el mensaje técnico de Google
            return None
        # ------------------------------------

        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        st.error(f"💥 Error de Conexión: {e}")
        return None

def analizar_comida(imagen, perfil):
    prompt = f"""
    Actúa como un nutricionista deportivo positivo y motivador.
    Analiza la imagen de comida.
    El usuario es: {perfil['sexo']}, {perfil['edad']} años, busca {perfil['meta']}.
    
    Responde SOLO con este JSON exacto (sin texto extra):
    {{
        "plato": "Nombre del plato",
        "calorias_aprox": 0,
        "proteinas_g": 0,
        "carbohidratos_g": 0,
        "grasas_g": 0,
        "consejo": "Un consejo breve y motivador ajustado a su meta"
    }}
    """
    respuesta = consultar_gemini(prompt, imagen)
    if respuesta:
        try:
            clean = respuesta.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except:
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
                    st.error("Usuario o contraseña incorrectos")
        
        with tab2:
            nu = st.text_input("Nuevo Usuario")
            np = st.text_input("Nueva Contraseña", type="password")
            if st.button("✨ Crear Cuenta", use_container_width=True):
                if base_datos.crear_usuario(nu, np):
                    st.success("¡Bienvenido al equipo! Ahora ingresa.")
                else:
                    st.warning("El usuario ya existe.")

def vista_onboarding(usuario):
    st.markdown("## 📋 Ficha de Reclutamiento")
    st.info("Para que la IA sea precisa, necesitamos calibrar el motor con tus datos.")
    
    with st.form("form_perfil"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre o Apodo")
        sexo = col2.selectbox("Sexo Biológico", ["Hombre", "Mujer"])
        edad = col1.number_input("Edad", 15, 90, 30)
        altura = col2.number_input("Altura (cm)", 140, 220, 170)
        peso = col1.number_input("Peso Actual (kg)", 40.0, 200.0, 70.0)
        actividad = col2.select_slider("Nivel de Actividad", ["Sedentario", "Ligero", "Moderado", "Atleta"])
        meta = st.selectbox("¿Cuál es tu Misión?", ["Perder Grasa", "Ganar Músculo", "Mantenimiento", "Rendimiento"])
        
        if st.form_submit_button("💾 Guardar y Acceder al Sistema", type="primary"):
            if base_datos.guardar_expediente(usuario, nombre, sexo, edad, peso, altura, meta, actividad):
                st.balloons()
                st.rerun()

def vista_dashboard(usuario, perfil):
    # Sidebar con perfil
    with st.sidebar:
        st.title(f"Hola, {perfil['nombre']}!")
        st.caption(f"🎯 Meta: {perfil['meta']}")
        st.metric("Peso", f"{perfil['peso']} kg")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario = None
            st.rerun()

    # Tabs principales
    t1, t2, t3, t4 = st.tabs(["📸 Escáner IA", "🏋️ Rutinas", "💬 Coach IA", "📈 Progreso"])
    
    # 1. ESCÁNER
    with t1:
        st.header("Escáner Nutricional")
        col_cam, col_upl = st.columns(2)
        img_cam = col_cam.camera_input("Cámara")
        img_upl = col_upl.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])
        
        imagen = img_cam if img_cam else img_upl
        
        if imagen:
            if st.button("🔍 Analizar Plato", type="primary"):
                with st.spinner("La IA está calculando macros..."):
                    datos = analizar_comida(imagen.getvalue(), perfil)
                    if datos:
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Kcal", datos['calorias_aprox'])
                        c2.metric("Prot", f"{datos['proteinas_g']}g")
                        c3.metric("Carb", f"{datos['carbohidratos_g']}g")
                        c4.metric("Gras", f"{datos['grasas_g']}g")
                        
                        st.success(f"🍽️ {datos['plato']}")
                        st.info(f"💡 Coach dice: {datos['consejo']}")
                        
                        base_datos.guardar_comida(usuario, datos)
                    else:
                        st.error("No pude identificar comida clara.")

    # 2. RUTINAS
    with t2:
        st.header("Generador de Rutinas")
        col1, col2 = st.columns(2)
        dias = col1.slider("Días disponibles", 2, 6, 3)
        lugar = col2.selectbox("Lugar", ["Gimnasio", "Casa (sin equipo)", "Parque"])
        
        if st.button("⚡ Generar Rutina Semanal"):
            with st.spinner("Diseñando plan táctico..."):
                prompt = f"Crea una rutina de {dias} días para {perfil['sexo']}, objetivo {perfil['meta']}, en {lugar}. Formato tabla Markdown."
                rutina = consultar_gemini(prompt)
                st.markdown(rutina)

    # 3. CHAT
    with t3:
        st.header("Chat con la Especialista")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if prompt := st.chat_input("Pregunta sobre dieta o ejercicio..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                contexto = f"Eres coach fitness. El usuario es {perfil['sexo']}, {perfil['edad']} años, meta: {perfil['meta']}."
                resp = consultar_gemini(f"{contexto}. Pregunta: {prompt}")
                st.write(resp)
            st.session_state.chat_history.append({"role": "assistant", "content": resp})

    # 4. PROGRESO
    with t4:
        st.header("Métricas de Evolución")
        historial = base_datos.obtener_historial(usuario)
        if historial:
            df = pd.DataFrame(historial, columns=["Fecha", "Plato", "Kcal", "Prot", "Carb", "Gras"])
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            
            st.subheader("Calorías Diarias")
            st.bar_chart(df, x="Fecha", y="Kcal", color="#FF4B4B")
            
            st.subheader("Historial Reciente")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aún no hay datos. ¡Empieza escaneando tu primera comida!")

# --- CONTROLADOR PRINCIPAL ---
if not st.session_state.usuario:
    vista_login()
else:
    # Verificamos si ya llenó el onboarding
    perfil = base_datos.obtener_perfil(st.session_state.usuario)
    if perfil:
        vista_dashboard(st.session_state.usuario, perfil)
    else:
        vista_onboarding(st.session_state.usuario)

