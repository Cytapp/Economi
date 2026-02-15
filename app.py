import streamlit as st
import google.generativeai as genai

# Título de la App
st.title("💰 Mi Asesor Financiero IA")

# --- NUEVO CÓDIGO DE SEGURIDAD ---
# Intentamos obtener la clave desde los "Secretos" de Streamlit
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Si no hay secreto configurado (ej: en tu PC local), la pedimos manual
    api_key = st.text_input("Ingresa tu API Key de Google Gemini:", type="password")
# ---------------------------------

if api_key:
    genai.configure(api_key=api_key)
    st.write("✅ Conectado con Inteligencia Artificial")

    # A PARTIR DE AQUÍ SIGUE TU CÓDIGO NORMAL (Tus Ingresos, Gastos, etc...)
    # ... (El resto del código que ya tienes no cambia)

    # 2. Formulario de Datos
    st.header("1. Tus Ingresos")
    salario = st.number_input("Salario Mensual Neto ($)", min_value=0, value=3000000)

    st.header("2. Tus Gastos Fijos")
    gastos_fijos = st.number_input("Total Gastos Fijos (Arriendo, comida, servicios)", min_value=0, value=658000)

    st.header("3. Tus Deudas")
    st.info("Ingresa tus deudas una por una.")
    
    if 'deudas' not in st.session_state:
        st.session_state.deudas = []

    col1, col2 = st.columns(2)
    with col1:
        nombre_deuda = st.text_input("Nombre de la deuda (Ej: Addi)")
    with col2:
        monto_deuda = st.number_input("Saldo Total ($)", min_value=0, step=10000)
    
    cuota_mensual = st.number_input("Cuota Mensual Mínima ($)", min_value=0, step=10000)

    if st.button("Agregar Deuda"):
        st.session_state.deudas.append({
            "nombre": nombre_deuda,
            "saldo": monto_deuda,
            "cuota": cuota_mensual
        })
        st.success(f"Agregada: {nombre_deuda}")

    # Mostrar deudas agregadas
    if st.session_state.deudas:
        st.table(st.session_state.deudas)
        
        total_deuda = sum(d['saldo'] for d in st.session_state.deudas)
        total_cuotas = sum(d['cuota'] for d in st.session_state.deudas)
        st.write(f"**Deuda Total:** ${total_deuda:,.0f} | **Cuotas Totales:** ${total_cuotas:,.0f}")

    # 3. El Botón Mágico
    if st.button("¡Generar Plan de Salida!"):
        if not st.session_state.deudas:
            st.error("Por favor agrega al menos una deuda.")
        else:
            # Construimos el prompt para Gemini
            prompt = f"""
            Actúa como un experto asesor financiero radical pero empático.
            
            Mis Datos:
            - Salario Mensual: ${salario}
            - Gastos Fijos para sobrevivir: ${gastos_fijos}
            - Mis Deudas actuales: {st.session_state.deudas}
            
            Objetivo:
            Crea un plan paso a paso usando el método "Bola de Nieve" o "Avalancha" (elige el mejor).
            Calcula mi flujo de caja libre (Ingreso - Gastos - Cuotas mínimas).
            Dime exactamente qué deuda pagar primero y cuánto dinero extra abonarle.
            Déjame siempre un pequeño porcentaje para "gastos personales/diversión" para no frustrarme.
            Usa formato Markdown con tablas y negritas. Habla en pesos colombianos.
            """

            try:
                model = genai.GenerativeModel('gemini-pro')
                with st.spinner('Analizando tus finanzas...'):
                    response = model.generate_content(prompt)
                    st.markdown("---")
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")

else:
    st.warning("Necesitas ingresar tu API Key para comenzar.")