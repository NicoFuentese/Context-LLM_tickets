import streamlit as st
import pandas as pd
from data.repository import TicketRepository
from services.llm_service import ITAdvisorService

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Smart-IT Ops | GLPi Advisor",
    page_icon="🛡️",
    layout="wide"
)

# --- INICIALIZACIÓN ---
@st.cache_resource
def get_services():
    try:
        repo = TicketRepository()
        llm = ITAdvisorService()
        return repo, llm
    except FileNotFoundError as e:
        st.error(f"🛑 {e}")
        st.stop()
    except Exception as e:
        st.error(f"🛑 Error crítico de inicialización: {e}")
        st.stop()

repo, llm_service = get_services()

# --- SIDEBAR: ESTADO DEL SISTEMA ---
with st.sidebar:
    st.header("📊 Métricas en Vivo")
    
    # Frescura del dato
    last_update = repo.get_last_update_time()
    st.caption(f"📅 Datos actualizados: **{last_update}**")
    st.divider()

    # Visualización de Carga
    try:
        workload = repo.get_team_workload()
        if "Error" in workload:
            st.error(workload["Error"])
        else:
            st.subheader("Carga de Trabajo Activa")
            df_workload = pd.DataFrame(list(workload.items()), columns=['Técnico', 'Tickets'])
            st.bar_chart(df_workload, x='Técnico', y='Tickets', color='#4CAF50')
            
            # Tabla detallada pequeña
            st.dataframe(df_workload, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"Error calculando métricas: {e}")

    st.divider()
    st.info("💡 **Tip:** Exporta un nuevo CSV desde GLPi para actualizar estas métricas.")

# --- ÁREA PRINCIPAL: CHAT ---
st.title("🛡️ Smart-IT Ops Advisor")
st.markdown("""
    *Asistente inteligente para la toma de decisiones operativas en infraestructura.*
""")

# Advertencia de Seguridad (Pilar Crítico)
st.caption("🔒 **Entorno Seguro:** El sistema está diseñado para leer tickets en modo solo lectura. **Por favor, NO comparta contraseñas, credenciales ni direcciones IP privadas en el chat.**")
st.divider()

# Gestión de Estado del Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input de usuario
if prompt := st.chat_input("Consulta sobre asignaciones o estado de la infraestructura..."):
    # 1. Mostrar mensaje usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Analizando carga operativa..."):
            # Obtenemos datos frescos para cada consulta
            current_workload = repo.get_team_workload()
            response = llm_service.get_recommendation(prompt, current_workload)
            st.markdown(response)
    
    # 3. Guardar historial
    st.session_state.messages.append({"role": "assistant", "content": response})