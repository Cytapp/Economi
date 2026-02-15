import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Pro DB", page_icon="📈", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Función para conectar a la base de datos (Cacheada para que sea rápida)
@st.cache_resource
def conectar_google_sheets():
    # Usamos los secretos que configuraste en Streamlit
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # Convertimos el objeto de secretos de Streamlit a credenciales
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    client = gspread.authorize(creds)
    # Abrimos la hoja (Asegúrate de que se llame EXACTAMENTE así)
    sheet = client.open("Finanzas_DB")
    return sheet

try:
    sh = conectar_google_sheets()
    worksheet_deudas = sh.worksheet("Deudas")
    worksheet_historial = sh.worksheet("Resumen")
except Exception as e:
    st.error(f"Error conectando a Google Sheets: {e}")
    st.stop()

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.title("💳 Gestión de Datos")
    
    # Opción para agregar nueva deuda a la BD
    with st.expander("➕ Agregar Nueva Deuda"):
        nuevo_nombre = st.text_input("Nombre Deuda")
        nuevo_monto = st.number_input("Monto Total", step=50000)
        nueva_cuota = st.number_input("Cuota Mensual", step=10000)
        
        if st.button("Guardar en Nube"):
            if nuevo_nombre:
                worksheet_deudas.append_row([nuevo_nombre, nuevo_monto, nueva_cuota])
                st.success("¡Guardado! Recarga la página.")
                st.cache_data.clear() # Limpiamos caché para ver cambios
            else:
                st.warning("Ponle nombre a la deuda")

    st.markdown("---")
    
    # Datos Fijos (Podrías guardarlos en sheets también, pero por ahora aquí)
    salario = st.number_input("Salario Neto", value=3000000)
    gastos_fijos = st.number_input("Gastos Fijos", value=658000)

# --- CARGAR DATOS DE LA NUBE ---
datos_deudas = worksheet_deudas.get_all_records()
df_deudas = pd.DataFrame(datos_deudas)

# --- PANTALLA PRINCIPAL ---
st.title("🚀 Mi Tablero Financiero (En la Nube)")

if not df_deudas.empty:
    # CÁLCULOS
    total_deuda = df_deudas['Monto'].sum()
    total_cuotas = df_deudas['Cuota'].sum()
    flujo_libre = salario - gastos_fijos - total_cuotas

    # 1. KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Deuda Total", f"${total_deuda:,.0f}")
    col2.metric("Flujo de Caja Libre", f"${flujo_libre:,.0f}")
    col3.metric("Deudas Activas", len(df_deudas))

    # 2. GRÁFICOS DE ESTADO ACTUAL
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Tu deuda actual")
        fig = px.pie(df_deudas, values='Monto', names='Nombre', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.subheader("Tu Historial de Progreso")
        # Leemos el historial
        datos_hist = worksheet_historial.get_all_records()
        if datos_hist:
            df_hist = pd.DataFrame(datos_hist)
            fig_line = px.line(df_hist, x='Fecha', y='Deuda_Total', markers=True, title="Reducción de Deuda")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Aún no hay historial guardado.")

    # 3. BOTÓN DE REGISTRAR PROGRESO (Crea el historial)
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Guardar 'Foto' del Progreso Hoy"):
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            # Guardamos: Fecha, Deuda Total, Flujo Libre
            worksheet_historial.append_row([fecha_hoy, total_deuda, flujo_libre])
            st.success("¡Historial actualizado! Tu progreso ha sido guardado.")
            st.cache_data.clear()

    # 4. BOTÓN INTELIGENCIA ARTIFICIAL (GEMINI)
    with col_btn2:
        if st.button("✨ Pedir consejo a Gemini"):
            # Configurar API Key
            if "GOOGLE_API_KEY" in st.secrets:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                # --- LO NUEVO (PON ESTO) ---
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"""
                Analiza mi situación financiera actual:
                - Deuda Total: ${total_deuda}
                - Flujo Libre: ${flujo_libre}
                - Lista de deudas: {datos_deudas}
                
                Dime qué acción tomar ESTA SEMANA para mejorar mi situación. Sé breve y directo.
                """
                with st.spinner("Consultando..."):
                    response = model.generate_content(prompt)
                    st.info(response.text)

    # TABLA DE DETALLE
    with st.expander("Ver Tabla de Deudas Completa"):
        st.dataframe(df_deudas)

else:
    st.warning("No hay deudas en la base de datos. Agrega una desde el menú lateral.")