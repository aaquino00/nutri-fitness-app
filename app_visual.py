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
    st.error(f"Error de configuración: Falta la API Key en secrets.toml. {e}")
    st.stop()

MODELO = "gemini-1.5-flash"

# Inicializar DB y Variables
base_datos.inicializar_db()

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None
if 'mensajes_chat' not in st.session_state:
    st.session_state.mensajes_chat = []

# --- FUNCIONES BACKEND (CONEXIÓN CON IA) ---

def analizar_ingesta(imagen_bytes=None, texto_usuario=None, perfil_usuario=None):
    """Módulo de Visión: Calcula calorías y macros"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contexto = """
    Eres un nutricionista experto. Analiza la entrada.
    Responde ESTRICTAMENTE con este JSON: 
    {"plato": "Nombre corto", "calorias_aprox": 0, "proteinas_g": 0, "carbohidratos_g": 0, "grasas_g": 0, "consejo": "Consejo breve"}
    """
    
    if perfil_usuario:
        contexto += f"""
        IMPORTANTE: El usuario es {perfil_usuario['genero']}, pesa {perfil_usuario['peso']}kg y su objetivo es {perfil_usuario['objetivo']}.
        Ajusta el campo 'consejo' basándote en estos datos.
        """

    parts = [{"text": contexto}]
    
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

def generar_plan_entrenamiento(meta, duracion, nivel, dias_semana, equipo, perfil=None):
    """Módulo Entrenador: Crea PLANES A LARGO PLAZO"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    datos_extra = ""
    if perfil:
        datos_extra = f"(Usuario: {perfil['genero']}, {perfil['edad']} años, Peso {perfil['peso']}kg)"

    prompt = f"""
    Actúa como un Entrenador Personal de Élite.
    Crea un PLAN DE ENTRENAMIENTO COMPLETO con los siguientes parámetros:
    
    - Perfil: {datos_extra}
    - Objetivo Principal: {meta}
    - Duración del ciclo: {duracion}
    - Nivel del atleta: {nivel}
    - Frecuencia: {dias_semana} días por semana
    - Equipo disponible: {equipo}
    
    Estructura la respuesta en Markdown de la siguiente forma:
    1. **Resumen del Plan**: Estrategia breve.
    2. **Distribución Semanal**: Rutina día a día.
    3. **Tabla de Ejercicios Clave**: Ejercicios, Series y Repeticiones.
    4. **Progresión**: Cómo aumentar la dificultad.
    5. **Nutrición Sugerida**: Breve consejo nutricional para este plan.
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
    """Módulo Chat: Consultas libres"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    contents = []
    sys_prompt = "Eres un Asistente de Salud Integral. Responde dudas de nutrición y deporte."
    
    if perfil:
        sys_prompt += f" Tienes en frente a una persona de {perfil['edad']} años, {perfil['peso']}kg, cuyo objetivo es {perfil['objetivo']}."
    
    if info_comida:
        sys_prompt += f" [Dato: La última comida registrada fue {info_comida}]"
    
    contents.append({"role": "user", "parts": [{"text": sys_prompt}]})
    contents.append({"role": "model", "parts": [{"text": "Entendido, Oficial. ¿Cuál es la situación?"}]})
    
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

# --- BARRA LATERAL (CONTROL DE ACCESO) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2964/2964514.png", width=50) 
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
                    st.success("Usuario creado. ¡Ingresa!")
                else:
                    st.error("El usuario ya existe.")

# --- LÓGICA PRINCIPAL ---

# 1. SI EL USUARIO ESTÁ LOGUEADO (MODO PRO)
if st.session_state.usuario_actual:
    usuario = st.session_state.usuario_actual
    
    # VERIFICAR SI TIENE EXPEDIENTE (ONBOARDING)
    if not base_datos.verificar_expediente(usuario):
        st.title("📝 Ficha de Reclutamiento")
        st.markdown("Para generar protocolos precisos, necesitamos sus datos biométricos.")
        
        with st.form("form_alta_usuario"):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre Completo")
            edad = col2.number_input("Edad", 15, 90, 30)
            peso = col1.number_input("Peso (kg)", 40.0, 150.0, 70.0)
            altura = col2.number_input("Altura (cm)", 140, 220, 170)
            genero = st.radio("Sexo Biológico", ["Hombre", "Mujer"], horizontal=True)
            objetivo = st.selectbox("Objetivo de la Misión", ["Perder Grasa", "Ganar Músculo", "Mantenimiento", "Rendimiento Deportivo"])
            actividad = st.select_slider("Nivel de Actividad", options=["Sedentario", "Ligero", "Moderado", "Intenso"])
            
            submitted = st.form_submit_button("📁 Archivar Expediente")
            if submitted:
                if base_datos.crear_expediente(usuario, nombre, edad, peso, altura, genero, objetivo, actividad):
                    st.success("¡Expediente creado! Accediendo al sistema...")
                    st.rerun()
                else:
                    st.error("Error al guardar datos. Intente de nuevo.")
                    
    else:
        # DASHBOARD COMPLETO (Usuario con expediente)
        datos_perfil = base_datos.obtener_datos_perfil(usuario)
        
        st.title(f"🛡️ Centro de Mando: {usuario}")
        if datos_perfil:
            st.caption(f"Objetivo: {datos_perfil['objetivo']} | Peso Actual: {datos_perfil['peso']}kg")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📸 Escáner Táctico", 
            "📅 Planes", 
            "💬 Chat Especialista", 
            "📊 Estadísticas"
        ])
        
        # TAB 1: ESCÁNER PRO (Guarda en DB)
        with tab1:
            st.subheader("Registro y Análisis")
            col_a, col_b = st.columns(2)
            with col_a:
                archivo = st.file_uploader("Evidencia Fotográfica", type=["jpg", "png", "jpeg"])
            with col_b:
                texto = st.text_area("Notas Adicionales", placeholder="Ej: Pollo a la plancha...")

            if st.button("🔍 Analizar y Registrar", type="primary"):
                if archivo or texto:
                    with st.spinner("Procesando datos biométricos..."):
                        bytes_img = archivo.getvalue() if archivo else None
                        datos = analizar_ingesta(bytes_img, texto, datos_perfil) # Pasamos el perfil
                        
                        if datos:
                            st.success(f"Plato Identificado: {datos['plato']}")
                            # Guardamos en DB porque es usuario PRO
                            base_datos.guardar_comida(usuario, datos)
                            
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Kcal", datos['calorias_aprox'])
                            c2.metric("Prot", f"{datos['proteinas_g']}g")
                            c3.metric("Carb", f"{datos['carbohidratos_g']}g")
                            c4.metric("Gras", f"{datos['grasas_g']}g")
                            st.info(f"💡 Consejo Personalizado: {datos['consejo']}")
                        else:
                            st.error("Fallo en el reconocimiento.")
                else:
                    st.warning("Se requiere imagen o texto.")

        # TAB 2: PLANES PERSONALIZADOS
        with tab2:
            st.subheader("Generador de Protocolos")
            col1, col2 = st.columns(2)
            with col1:
                # Pre-llenamos con el objetivo del perfil si existe
                idx_obj = 0
                opts_obj = ["Perdida de Grasa", "Ganar Músculo", "Mantenimiento", "Rendimiento Deportivo"]
                if datos_perfil and datos_perfil['objetivo'] in opts_obj:
                     idx_obj = opts_obj.index(datos_perfil['objetivo'])
                
                meta = st.selectbox("Objetivo del Ciclo", opts_obj, index=idx_obj)
                nivel = st.selectbox("Nivel", ["Principiante", "Intermedio", "Avanzado"])
                equipo = st.selectbox("Equipo", ["Gimnasio", "Mancuernas", "Calistenia", "Bandas"])
            with col2:
                duracion = st.select_slider("Duración", options=["15 Días", "30 Días", "60 Días", "90 Días"])
                dias = st.slider("Días/Semana", 2, 6, 4)

            if st.button("⚡ Generar Estrategia"):
                with st.spinner("Diseñando plan maestro..."):
                    plan = generar_plan_entrenamiento(meta, duracion, nivel, dias, equipo, datos_perfil)
                    st.markdown(plan)

        # TAB 3: CHAT CON CONTEXTO
        with tab3:
            st.subheader("Enlace Directo con el Coach")
            registros = base_datos.ver_historial(usuario)
            info_comida = f"{registros[0][3]} ({registros[0][4]} kcal)" if registros else None
            
            for msg in st.session_state.mensajes_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Escriba su consulta..."):
                st.session_state.mensajes_chat.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Analizando..."):
                        resp = chat_especialista(st.session_state.mensajes_chat, info_comida, datos_perfil)
                        st.markdown(resp)
                st.session_state.mensajes_chat.append({"role": "assistant", "content": resp})

        # TAB 4: ESTADÍSTICAS
        with tab4:
            st.subheader("Reporte de Progreso")
            registros = base_datos.ver_historial(usuario)
            if registros:
                df = pd.DataFrame(registros, columns=['ID', 'User', 'Fecha', 'Plato', 'Calorias', 'Proteinas', 'Carbos', 'Grasas', 'Consejo'])
                df['Fecha'] = pd.to_datetime(df['Fecha'])
                
                # Gráfico de Calorías
                st.write("Tendencia Calórica")
                st.line_chart(df, x='Fecha', y='Calorias', color="#FF4B4B")
                
                # Tabla reciente
                st.dataframe(df[['Fecha', 'Plato', 'Calorias', 'Proteinas', 'Carbos', 'Grasas']].head(10), hide_index=True)
            else:
                st.info("Aún no hay registros en el sistema.")

# 2. MODO PÚBLICO (GRATUITO / DEMO)
else:
    st.markdown("<h1 style='text-align: center;'>🍎 Escáner Nutricional IA</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align: center;'>
        <p>Analiza tu comida al instante. Sin registros. Gratis.</p>
        <p style='font-size: 0.8em; color: gray;'>🔓 Para guardar tu historial, obtener gráficas y planes personalizados, inicia sesión en el menú lateral.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

    # Interfaz Demo (Cámara directa o subida)
    col_demo1, col_demo2 = st.columns([1, 1])
    
    with col_demo1:
        st.info("📸 Opción 1: Cámara")
        img_camera = st.camera_input("Tomar foto")
    
    with col_demo2:
        st.info("📂 Opción 2: Subir archivo")
        img_upload = st.file_uploader("Cargar imagen", type=["jpg", "png", "jpeg"])

    archivo_final = img_camera if img_camera else img_upload

    if archivo_final:
        st.divider()
        with st.spinner("🤖 Analizando comida... (Modo Visitante)"):
            # Llamamos a la IA sin guardar en DB y sin perfil de usuario
            datos = analizar_ingesta(imagen_bytes=archivo_final.getvalue())
            
            if datos:
                col_res1, col_res2 = st.columns([1, 2])
                
                with col_res1:
                    # Mostrar la imagen que analizó
                    st.image(archivo_final, caption="Imagen analizada", width=200)
                
                with col_res2:
                    st.subheader(f"🍴 {datos['plato']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Calorías", f"{datos['calorias_aprox']} kcal")
                    c2.metric("Proteína", f"{datos['proteinas_g']} g")
                    c3.metric("Grasas", f"{datos['grasas_g']} g")
                    
                    st.success(f"💡 **Consejo IA:** {datos['consejo']}")
                    
                st.warning("⚠️ **Nota:** Este análisis no se ha guardado. Inicia sesión para llevar un registro histórico.")
            else:
                st.error("No pudimos identificar el alimento. Intenta con otra foto.")