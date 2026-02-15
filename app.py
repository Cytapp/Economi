import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Zenith Finance Pro", page_icon="💎", layout="wide")

# --- 2. ESTILO CSS AVANZADO (DISEÑO PROFESIONAL) ---
st.markdown("""
    <style>
    /* Fondo degradado moderno */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Tarjetas de métricas estilizadas */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        padding: 20px !important;
        border-radius: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
    }
    
    /* Títulos y fuentes */
    h1, h2, h3 {
        color: #1e3a8a !important;
        font-family: 'Inter', sans-serif;
    }

    /* Estilo para los botones */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }

    /* Pestañas personalizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: rgba(255,255,255,0.5);
        padding: 10px;
        border-radius: 15px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 10px;
        color: #1e3a8a;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        background-color: white !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS (Lógica Intacta) ---
@st.cache_resource
def conectar_google_sheets():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sheet = client.open("Finanzas_DB")
        return sheet
    except Exception as e:
        st.error(f"⚠️ Error conectando a Sheets: {e}")
        return None

sh = conectar_google_sheets()
if sh:
    ws_deudas = sh.worksheet("Deudas")
    ws_historial = sh.worksheet("Resumen")
    ws_gastos = sh.worksheet("Gastos")
    ws_pagos = sh.worksheet("Pagos")
else:
    st.stop()

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.markdown("# ⚙️ Configuración")
    salario = st.number_input("Salario Neto Mensual", value=3000000, step=50000)
    gastos_fijos_base = st.number_input("Gastos Fijos", value=658000, step=10000)
    
    st.divider()
    if st.button("🔄 Sincronizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.image("https://cdn-icons-png.flaticon.com/512/1611/1611154.png", width=100)

# --- 5. CARGA Y LIMPIEZA DE DATOS ---
try:
    df_deudas = pd.DataFrame(ws_deudas.get_all_records())
    df_gastos = pd.DataFrame(ws_gastos.get_all_records())
    
    # Limpieza robusta para cálculos
    if not df_deudas.empty:
        for col in ['Monto', 'Cuota', 'Tasa']:
            if col in df_deudas.columns:
                df_deudas[col] = df_deudas[col].astype(str).str.replace(',', '.').str.replace('$', '').str.replace('%', '')
                df_deudas[col] = pd.to_numeric(df_deudas[col], errors='coerce').fillna(0)

    if not df_gastos.empty:
        df_gastos['Monto'] = pd.to_numeric(df_gastos['Monto'], errors='coerce').fillna(0)

    total_deuda = df_deudas['Monto'].sum() if not df_deudas.empty else 0
    total_cuotas = df_deudas['Cuota'].sum() if not df_deudas.empty else 0
    total_gastos_hormiga = df_gastos['Monto'].sum() if not df_gastos.empty else 0
    flujo_libre = salario - gastos_fijos_base - total_cuotas - total_gastos_hormiga

except Exception as e:
    st.error(f"Error procesando datos: {e}")
    st.stop()

# --- 6. INTERFAZ PRINCIPAL ---
st.title("💎 Mi Centro Financiero Inteligente")
st.markdown("---")

# KPIs Destacados
c1, c2, c3, c4 = st.columns(4)
c1.metric("Deuda Total", f"${total_deuda:,.0f}")
c2.metric("Gastos Hormiga", f"${total_gastos_hormiga:,.0f}")
c3.metric("Flujo Libre", f"${flujo_libre:,.0f}", delta=f"${flujo_libre:,.0f}")
c4.metric("Estrés Financiero", "Bajo" if flujo_libre > 0 else "Crítico")

tab1, tab2, tab3 = st.tabs(["📊 DASHBOARD", "📝 OPERACIONES", "🤖 ASESOR IA"])

# ---------------- TAB 1: DASHBOARD ----------------
with tab1:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if not df_deudas.empty:
            st.subheader("🍰 Distribución de Deudas")
            fig = px.pie(df_deudas, values='Monto', names='Nombre', hole=0.5,
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        if not df_deudas.empty and 'Tasa' in df_deudas.columns:
            st.subheader("🔥 Ranking de Intereses (Avalancha)")
            df_sorted = df_deudas.sort_values(by='Tasa', ascending=True)
            fig_bar = px.bar(df_sorted, x='Tasa', y='Nombre', orientation='h', 
                             color='Tasa', color_continuous_scale='Reds', text_auto='.1f')
            st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- TAB 2: OPERACIONES ----------------
with tab2:
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        with st.container(border=True):
            st.subheader("🐜 Gasto Hormiga")
            with st.form("f_gasto", clear_on_submit=True):
                f_g = st.date_input("Fecha", datetime.today())
                c_g = st.text_input("¿Qué compraste?")
                m_g = st.number_input("Monto ($)", min_value=0, step=1000)
                if st.form_submit_button("Registrar Gasto ✍️"):
                    ws_gastos.append_row([str(f_g), c_g, m_g])
                    st.success("Gasto registrado")
                    st.cache_data.clear()

        with st.container(border=True):
            st.subheader("➕ Nueva Deuda / Crédito")
            with st.form("f_deuda", clear_on_submit=True):
                n_n = st.text_input("Nombre Entidad")
                n_m = st.number_input("Saldo Total", step=100000)
                n_c = st.number_input("Cuota Mensual", step=10000)
                n_t = st.number_input("Tasa E.A. %", step=0.1)
                if st.form_submit_button("Guardar en Nube ☁️"):
                    ws_deudas.append_row([n_n, n_m, n_c, n_t])
                    st.success("Deuda agregada")
                    st.cache_data.clear()

    with col_op2:
        with st.container(border=True):
            st.subheader("💳 Registrar Abono / Pago")
            if not df_deudas.empty:
                target = st.selectbox("Selecciona la deuda", df_deudas['Nombre'].tolist())
                abono = st.number_input("Valor pagado ($)", min_value=0, step=50000)
                
                if st.button("Confirmar Pago ✅", use_container_width=True, type="primary"):
                    ws_pagos.append_row([str(datetime.today().date()), target, abono])
                    try:
                        cell = ws_deudas.find(target)
                        fila = cell.row
                        saldo_raw = str(ws_deudas.cell(fila, 2).value).replace(',','').replace('$','')
                        nuevo_saldo = max(0, float(saldo_raw) - abono)
                        ws_deudas.update_cell(fila, 2, nuevo_saldo)
                        st.balloons()
                        st.success(f"¡Pagado! Nuevo saldo: ${nuevo_saldo:,.0f}")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("No hay deudas para pagar.")

# ---------------- TAB 3: CHATBOT IA ----------------
with tab3:
    st.subheader("🤖 Tu Consultor Gemini 2.0")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("¿Qué me aconsejas hoy?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                contexto = f"""Asesor financiero experto. Datos: Salario ${salario}, 
                Deuda Total ${total_deuda}, Flujo Libre ${flujo_libre}. 
                Deudas: {df_deudas.to_dict()}. Pregunta: {prompt}"""
                
                with st.spinner("Analizando tus finanzas..."):
                    res = model.generate_content(contexto).text
                    with st.chat_message("assistant"):
                        st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
            except Exception as e:
                st.error(f"Error IA: {e}")