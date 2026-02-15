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

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Zenith Finance AI", page_icon="💎", layout="wide")

# --- 2. ESTILOS CSS PROFESIONALES ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        font-weight: 700;
        color: #1e3a8a;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE APOYO (ANIMACIONES Y CONEXIÓN) ---
def load_lottieurl(url):
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

lottie_wallet = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_y9m8vtbc.json")
lottie_success = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_s2lryxtd.json")

@st.cache_resource
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        return client.open("Finanzas_DB")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- 4. CARGA DE DATOS ---
sh = conectar_google_sheets()
if not sh: st.stop()

ws_deudas = sh.worksheet("Deudas")
ws_historial = sh.worksheet("Resumen")
ws_gastos = sh.worksheet("Gastos")
ws_pagos = sh.worksheet("Pagos")

def get_data():
    df_d = pd.DataFrame(ws_deudas.get_all_records())
    df_g = pd.DataFrame(ws_gastos.get_all_records())
    
    for df in [df_d, df_g]:
        if not df.empty:
            for col in ['Monto', 'Cuota', 'Tasa']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(',', '.').str.replace('$', '').str.replace('%', '')
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df_d, df_g

df_deudas, df_gastos = get_data()

# --- 5. SIDEBAR ---
with st.sidebar:
    st_lottie(lottie_wallet, height=120)
    st.title("Settings")
    salario = st.number_input("Salario Mensual", value=3000000)
    gastos_fijos_base = st.number_input("Gastos Fijos Base", value=658000)
    if st.button("🔄 Refrescar Nube", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. CÁLCULOS ---
total_deuda = df_deudas['Monto'].sum() if not df_deudas.empty else 0
total_cuotas = df_deudas['Cuota'].sum() if not df_deudas.empty else 0
total_hormiga = df_gastos['Monto'].sum() if not df_gastos.empty else 0
flujo_libre = salario - gastos_fijos_base - total_cuotas - total_hormiga

# --- 7. DASHBOARD PRINCIPAL ---
st.title("💎 Zenith Finance AI Master")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Deuda Total", f"${total_deuda:,.0f}")
col2.metric("Pagos del Mes", f"${total_cuotas:,.0f}")
col3.metric("Gastos Hormiga", f"${total_hormiga:,.0f}")
col4.metric("Flujo Disponible", f"${flujo_libre:,.0f}")
style_metric_cards(border_left_color="#1e3a8a")

tab1, tab2, tab3 = st.tabs(["📊 ANÁLISIS", "💸 OPERACIONES", "🤖 CHAT ASESOR"])

# --- PESTAÑA 1: ANÁLISIS ---
with tab1:
    c1, c2 = st.columns([1.2, 0.8])
    with c1:
        st.subheader("🔥 Riesgo por Tasa de Interés")
        if not df_deudas.empty and 'Tasa' in df_deudas.columns:
            fig_bar = px.bar(df_deudas.sort_values('Tasa'), x='Tasa', y='Nombre', orientation='h', 
                             color='Tasa', color_continuous_scale='Reds', text_auto='.1f')
            st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        st.subheader("🎯 Concentración de Capital")
        if not df_deudas.empty:
            fig_pie = px.pie(df_deudas, values='Monto', names='Nombre', hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- PESTAÑA 2: OPERACIONES ---
with tab2:
    col_a, col_b = st.columns(2)
    
    with col_a:
        with st.container(border=True):
            st.subheader("➕ Nueva Deuda")
            n_n = st.text_input("Nombre de Entidad")
            n_m = st.number_input("Saldo", step=100000)
            n_c = st.number_input("Cuota", step=10000)
            
            if "tasa_ia" not in st.session_state: st.session_state.tasa_ia = 0.0
            
            if st.button("🕵️ Consultar Tasa con IA"):
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                res = model.generate_content(f"Tasa E.A. promedio en Colombia para {n_n}. Solo número.")
                st.session_state.tasa_ia = float(''.join(c for c in res.text if c.isdigit() or c == '.'))
                st.rerun()
            
            n_t = st.number_input("Tasa % E.A.", value=st.session_state.tasa_ia)
            if st.button("Guardar Deuda en Nube", type="primary"):
                ws_deudas.append_row([n_n, n_m, n_c, n_t])
                st.success("Guardado!"); st.cache_data.clear(); st.rerun()

    with col_b:
        with st.container(border=True):
            st.subheader("💳 Registrar Pago")
            if not df_deudas.empty:
                target = st.selectbox("Deuda pagada", df_deudas['Nombre'].tolist())
                abono = st.number_input("Monto abonado", step=50000)
                if st.button("Confirmar Abono ✅"):
                    ws_pagos.append_row([str(datetime.today().date()), target, abono])
                    cell = ws_deudas.find(target)
                    fila = cell.row
                    actual = float(str(ws_deudas.cell(fila, 2).value).replace(',',''))
                    ws_deudas.update_cell(fila, 2, max(0, actual - abono))
                    st_lottie(lottie_success, height=150)
                    st.balloons(); st.cache_data.clear(); st.rerun()

        with st.container(border=True):
            st.subheader("☕ Gasto Hormiga")
            conc_h = st.text_input("Concepto")
            mont_h = st.number_input("Valor", step=1000, key="h1")
            if st.button("Registrar Gasto 🐜"):
                ws_gastos.append_row([str(datetime.today().date()), conc_h, mont_h])
                st.toast("Gasto anotado!"); st.cache_data.clear(); st.rerun()

# --- PESTAÑA 3: CHATBOT ---
with tab3:
    st.subheader("💬 Inteligencia Financiera")
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if p := st.chat_input("¿Cómo voy con mis deudas?"):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.markdown(p)
        
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        ctx = f"Datos: Deuda ${total_deuda}, Flujo ${flujo_libre}. Deudas detalladas: {df_deudas.to_dict()}. Pregunta: {p}"
        response = model.generate_content(ctx).text
        
        with st.chat_message("assistant"): st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})