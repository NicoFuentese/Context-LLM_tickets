import streamlit as st
import pandas as pd
from data.repository import TicketRepository
from services.llm_service import ITAdvisorService
import re

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
if prompt := st.chat_input("Ej: ¿A quién asigno el ticket #102?"):
    # 1. Mostrar mensaje usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Generar respuesta
    with st.chat_message("assistant"):
        with st.spinner("Analizando ticket y carga..."):
            # --- LÓGICA DE DETECCIÓN DE CONTEXTO ---
            
            # 1. Obtenemos carga base
            current_workload = repo.get_team_workload()
            
            # 2. Detectamos si el usuario menciona un ID (ej: "#123" o "ticket 500")
            # Regex busca: simbolo # seguido de numeros O palabra ticket espacio numero
            ticket_pattern = r'(?:#|ticket|id|caso)\s*:?\s*(\d+)'
            ticket_match = re.search(ticket_pattern, prompt, re.IGNORECASE)
            
            specific_info = ""
            
            if ticket_match:
                # Si encontró un ID, buscamos el detalle
                ticket_id = ticket_match.group(1)
                st.toast(f"🔍 Analizando detalles ticket ID {ticket_id}...", icon="🤖")
                specific_info = repo.get_ticket_details(ticket_id)
            else:
                # Si NO menciona un ID especifico, le damos contexto de los "Sin Asignar"
                # por si pregunta "¿Qué tengo pendiente?"
                specific_info = "COLA DE PENDIENTES:\n" + repo.get_unassigned_tickets()

            # --- LLAMADA AL LLM ---
            try:
                response = llm_service.get_recommendation(
                    user_query=prompt, 
                    workload_data=current_workload,
                    specific_ticket_info=specific_info
                )
                
                st.markdown(response)

                #Guardar respuesta en historial
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"🛑 Error en el servicio de IA: {e}")