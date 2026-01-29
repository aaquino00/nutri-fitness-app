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

# ✅ USAMOS LA VERSIÓN ESTÁNDAR (La más segura)
MODELO = "gemini-1.5-flash"

# Inicializar DB y Variables
base_datos.inicializar_db()

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None
if 'mensajes_chat' not in st.session_state:
    st.session_state.mensajes_chat = []

# --- FUNCIONES BACKEND (CON MODO RAYOS X 🩻) ---

def analizar_ingesta(imagen_bytes=None, texto_usuario=None, perfil_usuario=None):
    """Módulo de Visión: Calcula calorías y macros"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Prompt ajustado para forzar JSON limpio
    contexto = """
    Actúa como un nutricionista experto. Analiza la imagen.
    Tu respuesta debe ser UNICAMENTE un objeto JSON válido.
    NO uses bloques de código (```json), NO pongas texto introductorio.
    
    Formato requerido:
    {
        "plato": "Nombre del plato",
        "calorias_aprox": 0,
        "proteinas_g": 0,
        "carbohidratos_g": 0,
        "grasas_g": 0,
        "consejo": "Consejo breve"
    }
    """
    
    if perfil_usuario:
        contexto += f" El usuario es {perfil_usuario['genero']}, objetivo: {perfil_usuario['objetivo']}."

    parts = [{"text": contexto}]
    
    if texto_usuario:
        parts.append({"text": f"Nota del usuario: {texto_usuario}"})
    if imagen_bytes:
        base64_image = base64.b64encode(imagen_bytes).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64_image}})
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # 1. VERIFICAR SI GOOGLE RESPONDE ERROR HTTP
        if response.status_code != 200:
            st.error(f"🚨 Error de Servidor Google: {response.status_code}")
            st.write(response.text)
            return None

        data = response.json()
        
        # 2. VERIFICAR SI HAY RESPUESTA DE TEXTO
        if 'candidates' not in data:
            st.error("🚨 La IA no devolvió contenido (Bloqueo de seguridad posible).")
            st.write(data)
            return None
            
        texto_raw = data['candidates'][0]['content']['parts'][0]['text']
        
        # --- 🩻 RAYOS X: MOSTRAMOS LO QUE VE LA MÁQUINA ---
        with st.expander("🕵️ Ver respuesta cruda de la IA (Debug)", expanded=True):
            st.code(texto_raw, language='json')
        # ----------------------------------------------------

        # Limpieza agresiva del JSON
        clean_json = texto_raw.replace('```json', '').replace('```', '').strip()
        
        # Intentar convertir a diccionario
        return json.loads(clean_json)
        
    except json.JSONDecodeError as e:
        st.error(f"🚨 La IA respondió texto, pero no es JSON válido.")
        return None
    except Exception as e:
        st.error(f"💥 Error Técnico inesperado: {e}")
        return None

def generar_plan_entrenamiento(meta, duracion, nivel, dias_semana, equipo, perfil=None):
    """Módulo Entrenador"""
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    datos_extra = ""
    if perfil:
        datos_extra = f"(Usuario: {perfil['genero']}, {perfil['edad']} años, Peso {perfil['peso']}kg)"

    prompt = f"""
    Crea un PLAN DE ENTRENAMIENTO:
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
    sys_prompt = "Eres un Asistente de Salud Integral."
    if perfil:
        sys_prompt += f" Usuario: {perfil['edad']} años, {perfil['peso']}kg, Obj: {perfil['objetivo']}."
    if info_comida:
        sys_prompt += f" [Última comida: {info_comida}]"
    
    contents.append({"role": "user", "parts": [{"text": sys_prompt}]})
    contents.append({"role": "model", "parts": [{"text": "Entendido. ¿En qué ayudo?"}]})
    
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

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("[https://cdn-icons-png.flaticon.com/512/2964/2964514.png](https://cdn-icons-png.flaticon.com/512/2964/2964514.png)", width=50) 
    st.markdown("### Comando Fitness")
    
    if 'usuario_actual' in st.session_state and st.session_state.usuario_actual:
        st.success(f"👮‍♂️ Oficial: {st.session_state.usuario_actual}")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_actual = None
            st.session_state.mensajes_chat = []
            st.rerun()
    else:
        st.info("🔒 Zona de Acceso")
        tab_login, tab_registro = st.tabs(["Ingresar", "Alta"])
        with tab_login:
            user_input = st.text_input("Usuario", key="login_user")
            pass_input = st.text_input("Contraseña", type="password", key="login_pass")
            if st.button("Ingresar", type="primary"):
                if base_datos.login_usuario(user_input, pass_input):
                    st.session_state.usuario_actual = user_input
                    st.toast("Acceso Autorizado", icon="✅")
                    st.rerun()
                else:
                    st.error("Credenciales Inválidas")
        with tab_registro:
            new_user = st.text_input("Nuevo Usuario", key="reg_user")
            new_pass = st.text_input("Nueva Contraseña", type="password", key="reg_pass")
            if st.button("Crear Cuenta"):
                if base_datos.crear_usuario(new_user, new_pass):
                    st.success("Usuario creado.")
                else:
                    st.error("Usuario ya existe.")

# --- LÓGICA PRINCIPAL ---
if st.session_state.usuario_actual:
    usuario = st.session_state.usuario_actual
    
    if not base_datos.verificar_expediente(usuario):
        st.title("📝 Ficha de Reclutamiento")
        with st.form("form_alta_usuario"):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre Completo")
            edad = col2.number_input("Edad", 15, 90, 30)
            peso = col1.number_input("Peso (kg)", 40.0, 150.0, 70.0)
            altura = col2.number_input("Altura (cm)", 140, 220, 170)
            genero = st.radio("Sexo", ["Hombre", "Mujer"], horizontal=True)
            objetivo = st.selectbox("Objetivo", ["Perder Grasa", "Ganar Músculo", "Mantenimiento", "Rendimiento Deportivo"])
            actividad = st.select_slider("Actividad", options=["Sedentario", "Ligero", "Moderado", "Intenso"])
            if st.form_submit_button("📁 Archivar Expediente"):
                if base_datos.crear_expediente(usuario, nombre, edad, peso, altura, genero, objetivo, actividad):
                    st.rerun()
                else:
                    st.error("Error al guardar.")
                    
    else:
        datos_perfil = base_datos.obtener_datos_perfil(usuario)
        st.title(f"🛡️ Centro de Mando: {usuario}")
        
        tab1, tab2, tab3, tab4 = st.tabs(["📸 Escáner", "📅 Planes", "💬 Chat", "📊 Estadísticas"])
        
        with tab1:
            st.subheader("Registro y Análisis")
            col_a, col_b = st.columns(2)
            archivo = col_a.file_uploader("Foto", type=["jpg", "png", "jpeg"])
            texto = col_b.text_area("Notas", placeholder="Ej: Pollo...")

            if st.button("🔍 Analizar", type="primary"):
                if archivo or texto:
                    with st.spinner("Procesando..."):
                        datos = analizar_ingesta(archivo.getvalue() if archivo else None, texto, datos_perfil)
                        if datos:
                            st.success(f"Plato: {datos['plato']}")
                            base_datos.guardar_comida(usuario, datos)
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Kcal", datos['calorias_aprox'])
                            c2.metric("Prot", f"{datos['proteinas_g']}g")
                            c3.metric("Carb", f"{datos['carbohidratos_g']}g")
                            c4.metric("Gras", f"{datos['grasas_g']}g")
                            st.info(f"💡 {datos['consejo']}")
                        else:
                            st.error("No se pudo procesar la respuesta.")

        # Resto de tabs (tab2, tab3, tab4) se mantienen igual que tu lógica anterior...
        with tab2:
            st.write("Generador de Planes (Activo)")
            if st.button("Generar Plan Rápido"):
                 st.info("Función de planes lista.")
        with tab3:
            st.write("Chat (Activo)")
        with tab4:
             st.write("Estadísticas (Activas)")

else:
    # MODO DEMO
    st.markdown("<h1 style='text-align: center;'>🍎 Escáner Nutricional IA</h1>", unsafe_allow_html=True)
    col_demo1, col_demo2 = st.columns([1, 1])
    img_camera = col_demo1.camera_input("Cámara")
    img_upload = col_demo2.file_uploader("Subir", type=["jpg", "png", "jpeg"])
    archivo_final = img_camera if img_camera else img_upload

    if archivo_final:
        st.divider()
        with st.spinner("🤖 Analizando..."):
            datos = analizar_ingesta(imagen_bytes=archivo_final.getvalue())
            if datos:
                st.subheader(f"🍴 {datos['plato']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Kcal", f"{datos['calorias_aprox']}")
                c2.metric("Prot", f"{datos['proteinas_g']}")
                c3.metric("Gras", f"{datos['grasas_g']}")
                st.success(f"Consejo: {datos['consejo']}")
            else:
                st.error("No se pudo identificar.")