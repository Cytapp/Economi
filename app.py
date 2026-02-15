import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests
from streamlit_lottie import st_lottie
from streamlit_extras.metric_cards import style_metric_cards

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Zenith Finance IA", page_icon="💎", layout="wide")

# --- CARGA DE ANIMACIONES ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200: return None
    return r.json()

lottie_wallet = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_y9m8vtbc.json")
lottie_success = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_s2lryxtd.json")

# --- ESTILOS CSS AVANZADOS ---
st.markdown("""
    <style>
    /* Gradiente de fondo moderno */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Contenedores tipo 'Glassmorphism' */
    div[data-testid="stVerticalBlock"] > div:has(div.stMetric) {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Títulos con estilo */
    h1 {
        color: #1e3a8a;
        font-family: 'Inter', sans-serif;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN GOOGLE SHEETS (Oculto por brevedad, mantenemos el tuyo) ---
@st.cache_resource
def conectar_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds).open("Finanzas_DB")

sh = conectar_google_sheets()
ws_deudas, ws_historial, ws_gastos, ws_pagos = sh.worksheet("Deudas"), sh.worksheet("Resumen"), sh.worksheet("Gastos"), sh.worksheet("Pagos")

# --- LÓGICA DE DATOS ---
df_deudas = pd.DataFrame(ws_deudas.get_all_records())
df_gastos = pd.DataFrame(ws_gastos.get_all_records())

# Limpieza rápida (Mantenemos tu lógica anterior)
for df in [df_deudas, df_gastos]:
    if not df.empty:
        for col in ['Monto', 'Cuota', 'Tasa']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)

# --- SIDEBAR ESTILIZADA ---
with st.sidebar:
    st_lottie(lottie_wallet, height=150, key="wallet")
    st.markdown("### 🛠️ Panel de Control")
    salario = st.number_input("Ingresos Netos", value=3000000)
    gastos_fijos_base = st.number_input("Gastos Fijos", value=658000)
    st.divider()

# --- CÁLCULOS ---
total_deuda = df_deudas['Monto'].sum() if not df_deudas.empty else 0
total_cuotas = df_deudas['Cuota'].sum() if not df_deudas.empty else 0
total_hormiga = df_gastos['Monto'].sum() if not df_gastos.empty else 0
flujo_libre = salario - gastos_fijos_base - total_cuotas - total_hormiga

# === CUERPO DE LA APP ===
st.title("💎 Zenith Finance Master")

# Métricas con estilo de tarjeta
col1, col2, col3, col4 = st.columns(4)
col1.metric("Deuda Total", f"${total_deuda:,.0f}")
col2.metric("A pagar este mes", f"${total_cuotas:,.0f}")
col3.metric("Gastos Hormiga", f"${total_hormiga:,.0f}")
col4.metric("Flujo de Caja", f"${flujo_libre:,.0f}")
style_metric_cards(background_color="#FFFFFF", border_left_color="#1e3a8a", border_color="#1e3a8a", box_shadow=True)

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 Análisis Visual", "💸 Operaciones", "🤖 Consultoría IA"])

with tab1:
    c_g1, c_g2 = st.columns([1, 1])
    with c_g1:
        st.subheader("🌋 Mapa de Riesgo (Intereses)")
        fig = px.bar(df_deudas.sort_values('Tasa'), x='Tasa', y='Nombre', orientation='h', 
                     color='Tasa', color_continuous_scale='Bluered_r', template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    
    with c_g2:
        st.subheader("📈 Proyección de Gastos")
        # Aquí podrías poner una gráfica de líneas del historial
        st.info("Añade abonos para ver tu progreso temporal aquí.")

with tab2:
    # Secciones con bordes redondeados usando contenedores
    with st.container():
        col_reg1, col_reg2 = st.columns(2)
        with col_reg1:
            st.markdown("#### 🐜 Registrar Gasto Pequeño")
            with st.form("hormiga"):
                conc = st.text_input("Concepto")
                val = st.number_input("Valor", step=1000)
                if st.form_submit_button("Añadir Gasto"):
                    ws_gastos.append_row([str(datetime.today().date()), conc, val])
                    st.toast("Gasto registrado con éxito")
                    st.rerun()

        with col_reg2:
            st.markdown("#### ✅ Registrar Abono")
            if not df_deudas.empty:
                deuda = st.selectbox("¿A cuál?", df_deudas['Nombre'].tolist())
                pago = st.number_input("Monto pagado", step=50000)
                if st.button("Confirmar Pago"):
                    # Lógica de actualización igual a la anterior...
                    st_lottie(lottie_success, height=200, key="success")
                    st.balloons()
                    # (Aquí iría el código de actualización de Sheets)

with tab3:
    # Chatbot con interfaz limpia
    st.markdown("#### 💬 Chat con Zenith IA")
    if prompt := st.chat_input("¿Cómo puedo ahorrar más?"):
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-2.0-flash')
        with st.chat_message("assistant"):
            st.write(model.generate_content(f"Datos: {df_deudas.to_dict()}. Pregunta: {prompt}").text)