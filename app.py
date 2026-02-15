import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Pro", page_icon="💸", layout="wide")

# --- ESTILOS VISUALES (CSS) ---
st.markdown("""
    <style>
    .big-font { font-size:20px !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- TÍTULO PRINCIPAL ---
st.title("🚀 Mi Centro de Comando Financiero")
st.markdown("---")

# --- CONEXIÓN API (SECRETS) ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 API Key Gemini", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- BARRA LATERAL (DATOS) ---
with st.sidebar:
    st.header("📝 Tus Datos")
    salario = st.number_input("Salario Mensual Neto", value=3000000, step=50000)
    gastos_fijos = st.number_input("Gastos Fijos (Vivir)", value=658000, step=10000)
    
    st.markdown("---")
    st.subheader("Agregar Deuda")
    nombre = st.text_input("Nombre (Ej: Addi)")
    monto = st.number_input("Saldo Total", min_value=0, step=50000)
    cuota = st.number_input("Cuota Mensual", min_value=0, step=10000)
    
    if st.button("➕ Agregar Deuda"):
        if 'deudas' not in st.session_state:
            st.session_state.deudas = []
        st.session_state.deudas.append({"Deuda": nombre, "Saldo": monto, "Cuota": cuota})
        st.success(f"Agregada: {nombre}")

# --- PANTALLA PRINCIPAL ---

# 1. VISUALIZACIÓN DE DATOS
if 'deudas' in st.session_state and st.session_state.deudas:
    # Convertimos datos a Tabla (DataFrame)
    df = pd.DataFrame(st.session_state.deudas)
    
    # Cálculos matemáticos
    total_deuda = df['Saldo'].sum()
    total_cuotas = df['Cuota'].sum()
    flujo_libre = salario - gastos_fijos - total_cuotas
    
    # KPIs (Indicadores Grandes)
    col1, col2, col3 = st.columns(3)
    col1.metric("Deuda Total", f"${total_deuda:,.0f}", delta_color="inverse")
    col2.metric("Cuotas Mensuales", f"${total_cuotas:,.0f}", delta="-Obligatorio")
    col3.metric("Flujo Libre Real", f"${flujo_libre:,.0f}", delta="Disponible", delta_color="normal")

    st.markdown("---")

    # GRÁFICOS INTERACTIVOS
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🍰 ¿A quién le debes más?")
        # Gráfico de Torta (Dona)
        fig_pie = px.pie(df, values='Saldo', names='Deuda', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("📊 Peso de la Cuota Mensual")
        # Gráfico de Barras
        fig_bar = px.bar(df, x='Deuda', y='Cuota', color='Cuota', color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    # BARRA DE PELIGRO (Ratio de Endeudamiento)
    ratio = min(total_cuotas / salario, 1.0) # Para que no pase de 100%
    st.write(f"**Nivel de Endeudamiento: {int(ratio*100)}% de tu sueldo**")
    if ratio > 0.40:
        st.progress(ratio, text="⚠️ ¡Cuidado! Tus cuotas son muy altas")
    else:
        st.progress(ratio, text="✅ Estás en un nivel manejable")

else:
    st.info("👈 Usa el menú de la izquierda para agregar tus deudas y ver la magia.")

# --- BOTÓN DE INTELIGENCIA ARTIFICIAL ---
st.markdown("---")
if st.button("✨ Generar Estrategia con IA", type="primary"):
    if 'deudas' not in st.session_state or not st.session_state.deudas:
        st.error("Agrega deudas primero.")
    else:
        with st.spinner('🤖 Gemini está analizando tus gráficos...'):
            prompt = f"""
            Eres un experto financiero. Tengo un salario de ${salario}, gastos de ${gastos_fijos}.
            Mis deudas son: {st.session_state.deudas}.
            
            Analiza mi situación basándote en que mi flujo libre es ${flujo_libre}.
            1. Dame un diagnóstico directo (¿Estoy grave o bien?).
            2. Crea una tabla con el orden EXACTO de pago (Bola de nieve).
            3. Dime cuánto dinero extra ponerle a la primera deuda.
            4. Dame una frase motivadora corta al final.
            Usa emojis y formato Markdown limpio.
            """
            try:
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                
                st.balloons() # ¡EFECTO ESPECIAL!
                st.markdown("### 📋 Tu Plan de Libertad Financiera")
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error: {e}")