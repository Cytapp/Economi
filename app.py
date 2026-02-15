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
    gastos_fijos_base = st.number_input("Gastos Fijos", value=658000, step=10000)
    
    if st.button("🔄 Recargar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- CARGA Y LIMPIEZA DE DATOS (AQUÍ ESTÁ EL ARREGLO) ---
try:
    # 1. Cargar datos crudos
    data_deudas = ws_deudas.get_all_records()
    df_deudas = pd.DataFrame(data_deudas)
    
    data_gastos = ws_gastos.get_all_records()
    df_gastos = pd.DataFrame(data_gastos)

    # 2. LIMPIEZA AUTOMÁTICA DE NÚMEROS (Anti-Error)
    if not df_deudas.empty:
        # Limpiar Tasa (Cambiar comas por puntos, quitar %)
        if 'Tasa' in df_deudas.columns:
            df_deudas['Tasa'] = df_deudas['Tasa'].astype(str).str.replace(',', '.').str.replace('%', '').str.replace('$', '')
            df_deudas['Tasa'] = pd.to_numeric(df_deudas['Tasa'], errors='coerce').fillna(0)
        
        # Limpiar Monto y Cuota (Quitar signos de pesos y comas de miles)
        for col in ['Monto', 'Cuota']:
            if col in df_deudas.columns:
                df_deudas[col] = df_deudas[col].astype(str).str.replace(',', '').str.replace('$', '').str.replace('.', '')
                # OJO: Si usas puntos para miles en Excel, esto los quita. 
                # Si usas puntos para decimales en Monto, avísame. Asumo enteros para montos grandes.
                df_deudas[col] = pd.to_numeric(df_deudas[col], errors='coerce').fillna(0)

    if not df_gastos.empty:
        if 'Monto' in df_gastos.columns:
             df_gastos['Monto'] = df_gastos['Monto'].astype(str).str.replace(',', '').str.replace('$', '')
             df_gastos['Monto'] = pd.to_numeric(df_gastos['Monto'], errors='coerce').fillna(0)
    
    # 3. Cálculos Generales con datos limpios
    total_deuda = df_deudas['Monto'].sum() if not df_deudas.empty else 0
    total_cuotas = df_deudas['Cuota'].sum() if not df_deudas.empty else 0
    total_gastos_hormiga = df_gastos['Monto'].sum() if not df_gastos.empty else 0
    flujo_libre = salario - gastos_fijos_base - total_cuotas - total_gastos_hormiga

except Exception as e:
    st.error(f"Error procesando datos: {e}")
    st.stop()

# === INTERFAZ PRINCIPAL CON PESTAÑAS ===
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📝 Registrar & Agregar", "💬 Chatbot IA"])

# ---------------- PESTAÑA 1: DASHBOARD ----------------
with tab1:
    st.title("🚀 Tu Centro de Comando")
    
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Deuda Total", f"${total_deuda:,.0f}", delta_color="inverse")
    c2.metric("Gastos Hormiga", f"${total_gastos_hormiga:,.0f}", delta="- variable")
    c3.metric("Flujo Libre Real", f"${flujo_libre:,.0f}")
    
    # KPI de Tasa Promedio
    if not df_deudas.empty and 'Tasa' in df_deudas.columns:
        # Filtramos tasas mayores a 0 para el promedio real
        tasas_reales = df_deudas[df_deudas['Tasa'] > 0]['Tasa']
        if not tasas_reales.empty:
            tasa_promedio = tasas_reales.mean()
            c4.metric("Tasa Interés Promedio", f"{tasa_promedio:.1f}% E.A.")
        else:
             c4.metric("Tasa Interés", "0%")
    else:
        c4.metric("Nivel de Estrés", "Calculando...")

    st.markdown("---")
    
    # Gráficos
    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        if not df_deudas.empty:
            st.subheader("🍰 Composición de Deuda")
            fig = px.pie(df_deudas, values='Monto', names='Nombre', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
    
    with col_graf2:
        if not df_deudas.empty and 'Tasa' in df_deudas.columns:
            st.subheader("🔥 Deudas más Peligrosas (Por Interés)")
            df_sorted = df_deudas.sort_values(by='Tasa', ascending=True)
            fig_bar = px.bar(df_sorted, x='Tasa', y='Nombre', orientation='h', 
                             color='Tasa', color_continuous_scale='Reds',
                             text='Tasa')
            fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- PESTAÑA 2: REGISTRAR ----------------
with tab2:
    st.header("Gestionar mi Dinero")
    
    # --- SECCIÓN: NUEVA DEUDA CON IA ---
    with st.expander("➕ Crear Nueva Deuda (Con Consulta de Tasa IA)", expanded=True):
        col_new1, col_new2 = st.columns(2)
        
        with col_new1:
            n_nombre = st.text_input("Nombre Deuda (Ej: RappiCard)")
            n_monto = st.number_input("Total Deuda", step=50000)
        
        with col_new2:
            n_cuota = st.number_input("Cuota Mensual", step=10000)
            
            # --- MAGIA IA ---
            if "tasa_sugerida" not in st.session_state:
                st.session_state.tasa_sugerida = 0.0

            col_ia1, col_ia2 = st.columns([1, 2])
            with col_ia1:
                if st.button("🕵️ Consultar Tasa IA"):
                    if n_nombre and "GOOGLE_API_KEY" in st.secrets:
                        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                        try:
                            model = genai.GenerativeModel('gemini-2.0-flash')
                            with st.spinner(f"Investigando {n_nombre}..."):
                                prompt = f"""
                                Estima la Tasa de Interés Efectiva Anual (E.A.) en Colombia para '{n_nombre}'.
                                RESPONDE SOLO CON EL NÚMERO (Ejemplo: 28.5). Sin texto.
                                """
                                response = model.generate_content(prompt)
                                texto_limpio = ''.join(c for c in response.text if c.isdigit() or c == '.')
                                if texto_limpio:
                                    st.session_state.tasa_sugerida = float(texto_limpio)
                                    st.toast(f"Tasa encontrada: {st.session_state.tasa_sugerida}%")
                        except Exception as e:
                            st.error(f"Error consultando: {e}")

            with col_ia2:
                n_tasa = st.number_input("Tasa Interés E.A. (%)", value=st.session_state.tasa_sugerida, step=0.1, format="%.2f")

        if st.button("Guardar Nueva Deuda"):
            # Convertimos a string para asegurar formato
            ws_deudas.append_row([n_nombre, n_monto, n_cuota, n_tasa])
            st.success("Guardada con éxito.")
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")
    
    # --- PAGOS Y GASTOS ---
    col_reg1, col_reg2 = st.columns(2)
    
    with col_reg1:
        st.subheader("🐜 Nuevo Gasto Hormiga")
        with st.form("form_gasto"):
            fecha_gasto = st.date_input("Fecha", datetime.today())
            concepto_gasto = st.text_input("Concepto")
            monto_gasto = st.number_input("Valor ($)", min_value=0, step=1000)
            if st.form_submit_button("Registrar Gasto"):
                ws_gastos.append_row([str(fecha_gasto), concepto_gasto, monto_gasto])
                st.success("Gasto guardado.")
                st.cache_data.clear()

    with col_reg2:
        st.subheader("💳 Abonar a Deuda")
        if not df_deudas.empty:
            lista_nombres = df_deudas['Nombre'].tolist()
            deuda_seleccionada = st.selectbox("¿Qué deuda pagaste?", lista_nombres)
            with st.form("form_pago"):
                fecha_pago = st.date_input("Fecha Pago", datetime.today())
                monto_abono = st.number_input("Valor Abonado", min_value=0, step=10000)
                if st.form_submit_button("Registrar Pago"):
                    ws_pagos.append_row([str(fecha_pago), deuda_seleccionada, monto_abono])
                    
                    # Lógica de actualización de saldo
                    try:
                        cell = ws_deudas.find(deuda_seleccionada)
                        fila = cell.row
                        # Obtenemos saldo y limpiamos caracteres
                        saldo_raw = str(ws_deudas.cell(fila, 2).value).replace(',','').replace('$','')
                        saldo_actual = float(saldo_raw) if saldo_raw else 0.0
                        
                        nuevo_saldo = saldo_actual - monto_abono
                        if nuevo_saldo < 0: nuevo_saldo = 0
                        ws_deudas.update_cell(fila, 2, nuevo_saldo)
                        st.success(f"Nuevo saldo: ${nuevo_saldo:,.0f}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error actualizando saldo: {e}")

# ---------------- PESTAÑA 3: CHATBOT IA ----------------
with tab3:
    st.header("🤖 Tu Asesor Financiero Personal")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ej: ¿Cuál deuda debo pagar primero?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        if "GOOGLE_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            try:
                contexto = f"""
                Eres un asesor financiero experto.
                
                DATOS REALES:
                - Flujo Libre: ${flujo_libre:,.0f}
                - Deuda Total: ${total_deuda:,.0f}
                
                MIS DEUDAS:
                {df_deudas.to_string(index=False) if not df_deudas.empty else "Sin deudas"}
                
                Pregunta del usuario: "{prompt}"
                Responde brevemente.
                """
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(contexto)
                respuesta_ia = response.text
                
                with st.chat_message("assistant"):
                    st.markdown(respuesta_ia)
                st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})
            except Exception as e:
                st.error(f"Error IA: {e}")