import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Master IA", page_icon="💰", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
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

# Inicializar hojas
sh = conectar_google_sheets()
if sh:
    ws_deudas = sh.worksheet("Deudas")
    ws_historial = sh.worksheet("Resumen")
    ws_gastos = sh.worksheet("Gastos")
    ws_pagos = sh.worksheet("Pagos")
else:
    st.stop()

# --- DATOS FIJOS ---
with st.sidebar:
    st.header("⚙️ Configuración")
    salario = st.number_input("Salario Neto", value=3000000, step=50000)
    gastos_fijos_base = st.number_input("Gastos Fijos (Casa/Servicios)", value=658000, step=10000)
    
    if st.button("🔄 Recargar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- CARGA DE DATOS ---
try:
    df_deudas = pd.DataFrame(ws_deudas.get_all_records())
    df_gastos = pd.DataFrame(ws_gastos.get_all_records())
    
    # Cálculos Generales
    total_deuda = df_deudas['Monto'].sum() if not df_deudas.empty else 0
    total_cuotas = df_deudas['Cuota'].sum() if not df_deudas.empty else 0
    
    # Sumar gastos hormiga del mes actual (Opcional: filtrar por mes)
    total_gastos_hormiga = df_gastos['Monto'].sum() if not df_gastos.empty else 0
    
    # Flujo Real
    flujo_libre = salario - gastos_fijos_base - total_cuotas - total_gastos_hormiga

except Exception as e:
    st.error(f"Error leyendo datos: {e}")
    st.stop()

# === INTERFAZ PRINCIPAL CON PESTAÑAS ===
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Registrar Movimientos", "💬 Chatbot IA"])

# ---------------- PESTAÑA 1: DASHBOARD ----------------
with tab1:
    st.title("🚀 Tu Centro de Comando")
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Deuda Total", f"${total_deuda:,.0f}", delta_color="inverse")
    c2.metric("Gastos Hormiga", f"${total_gastos_hormiga:,.0f}", delta="- variable")
    c3.metric("Flujo Libre Real", f"${flujo_libre:,.0f}")
    c4.metric("Nivel de Estrés", "Alto" if flujo_libre < 0 else "Bajo")

    st.markdown("---")
    
    # Gráficos
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        if not df_deudas.empty:
            st.subheader("🍰 Composición de Deuda")
            fig = px.pie(df_deudas, values='Monto', names='Nombre', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_graf2:
        if not df_gastos.empty:
            st.subheader("🐜 Tus Gastos Hormiga")
            fig_gastos = px.bar(df_gastos, x='Concepto', y='Monto', color='Monto')
            st.plotly_chart(fig_gastos, use_container_width=True)

# ---------------- PESTAÑA 2: REGISTRAR ----------------
with tab2:
    st.header("Gestionar mi Dinero")
    
    col_reg1, col_reg2 = st.columns(2)
    
    # --- 1. REGISTRAR GASTO HORMIGA ---
    with col_reg1:
        st.subheader("🐜 Nuevo Gasto Hormiga")
        with st.form("form_gasto"):
            fecha_gasto = st.date_input("Fecha", datetime.today())
            concepto_gasto = st.text_input("¿En qué gastaste?", placeholder="Ej: Empanada y gaseosa")
            monto_gasto = st.number_input("Valor ($)", min_value=0, step=1000)
            
            if st.form_submit_button("Registrar Gasto"):
                ws_gastos.append_row([str(fecha_gasto), concepto_gasto, monto_gasto])
                st.success("Gasto guardado. Qué dolor de bolsillo 😅")
                st.cache_data.clear()

    # --- 2. REGISTRAR ABONO A DEUDA (¡CON ACTUALIZACIÓN AUTOMÁTICA!) ---
    with col_reg2:
        st.subheader("💳 Abonar a Deuda")
        if not df_deudas.empty:
            lista_nombres = df_deudas['Nombre'].tolist()
            deuda_seleccionada = st.selectbox("¿Qué deuda pagaste?", lista_nombres)
            
            with st.form("form_pago"):
                fecha_pago = st.date_input("Fecha Pago", datetime.today())
                monto_abono = st.number_input("Valor Abonado ($)", min_value=0, step=10000)
                
                if st.form_submit_button("Registrar Pago"):
                    # 1. Guardar en historial de pagos
                    ws_pagos.append_row([str(fecha_pago), deuda_seleccionada, monto_abono])
                    
                    # 2. ACTUALIZAR SALDO EN LA HOJA DE DEUDAS
                    try:
                        # Buscar la celda donde está el nombre de la deuda
                        cell = ws_deudas.find(deuda_seleccionada)
                        # El monto está en la columna 2 (B), fila encontrada
                        fila = cell.row
                        saldo_actual_str = ws_deudas.cell(fila, 2).value
                        # Limpiamos el valor por si tiene comas o puntos
                        saldo_actual = float(str(saldo_actual_str).replace(",","").replace("$",""))
                        
                        nuevo_saldo = saldo_actual - monto_abono
                        if nuevo_saldo < 0: nuevo_saldo = 0
                        
                        # Actualizamos la celda en Google Sheets
                        ws_deudas.update_cell(fila, 2, nuevo_saldo)
                        
                        st.success(f"¡Pago registrado! El nuevo saldo de {deuda_seleccionada} es ${nuevo_saldo:,.0f}")
                        st.balloons()
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Se guardó el pago, pero hubo error actualizando el saldo: {e}")
        else:
            st.warning("No tienes deudas registradas para pagar.")

    # --- 3. AGREGAR NUEVA DEUDA ---
    with st.expander("➕ Crear Nueva Deuda (Si te endeudaste más)"):
        n_nombre = st.text_input("Nombre")
        n_monto = st.number_input("Total Deuda", step=50000)
        n_cuota = st.number_input("Cuota", step=10000)
        if st.button("Guardar Nueva Deuda"):
            ws_deudas.append_row([n_nombre, n_monto, n_cuota])
            st.success("Guardada.")
            st.cache_data.clear()

# ---------------- PESTAÑA 3: CHATBOT IA ----------------
with tab3:
    st.header("🤖 Tu Asesor Financiero Personal")
    st.markdown("Pregúntame lo que quieras sobre tus deudas, gastos o pide consejos.")

    # Inicializar historial de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input del usuario
    if prompt := st.chat_input("Ej: ¿Cuánto he gastado en hormigas? ó ¿Qué deuda pago primero?"):
        # Guardar y mostrar mensaje usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Preparar respuesta IA
        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            try:
                # Contexto Financiero Completo
                contexto = f"""
                Eres un asesor financiero experto y amigable. Tienes acceso a mis datos en tiempo real:
                
                - Salario Neto: ${salario:,.0f}
                - Gastos Fijos: ${gastos_fijos_base:,.0f}
                - Gastos Hormiga Registrados: ${total_gastos_hormiga:,.0f}
                - Deuda Total Actual: ${total_deuda:,.0f}
                - Flujo Libre (Dinero sobrante): ${flujo_libre:,.0f}
                
                DETALLE DE MIS DEUDAS:
                {df_deudas.to_string(index=False) if not df_deudas.empty else "No hay deudas"}
                
                DETALLE DE MIS GASTOS HORMIGA:
                {df_gastos.to_string(index=False) if not df_gastos.empty else "No hay gastos"}
                
                Responde a la pregunta del usuario: "{prompt}"
                Usa emojis, sé breve y da consejos matemáticos precisos basados en mis números.
                """
                
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(contexto)
                respuesta_ia = response.text
                
                # Mostrar respuesta IA
                with st.chat_message("assistant"):
                    st.markdown(respuesta_ia)
                
                st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})
                
            except Exception as e:
                st.error(f"Error IA: {e}")
        else:
            st.warning("Configura tu API Key primero.")