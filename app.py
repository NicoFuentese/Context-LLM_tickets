import streamlit as st
import pandas as pd
from data.repository import TicketRepository
from services.llm_service import ITAdvisorService
from services.rag_service import KnowledgeBaseService
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Smart-IT Ops V2 (RAG)| GLPi Advisor",
    page_icon="🛡️",
    layout="wide"
)

# --- INICIALIZACIÓN ---
@st.cache_resource
def get_services():
    try:
        repo = TicketRepository()
        llm = ITAdvisorService()
        rag = KnowledgeBaseService()
        return repo, llm, rag
    except FileNotFoundError as e:
        st.error(f"🛑 {e}")
        st.stop()
    except Exception as e:
        st.error(f"🛑 Error crítico de inicialización: {e}")
        st.stop()

repo, advisor, kb_service = get_services()

def main():
    st.title("🛡️ Smart-IT Ops V2 | RAG Enhanced")

# --- SIDEBAR ---
    with st.sidebar:
        st.header("🧠 Base de Conocimiento")
        # Botón para admin: Recargar protocolos
        if st.button("🔄 Re-indexar Protocolos"):
            with st.spinner("Leyendo y vectorizando documentos..."):
                result = kb_service.ingest_protocols()
            st.success(result)
    
        # Obtener tickets sin asignar
        try:
            unassigned_list = repo.get_unassigned_tickets(limit=30)
            st.metric("Tickets Sin Asignar", len(unassigned_list) if unassigned_list else 0)
        except Exception:
            unassigned_list = []
            
        st.divider()

        try:
            workload = repo.get_team_workload()
            st.subheader("Carga Equipo")
            for tech, count in workload.items():
                st.write(f"**{tech}**: {count}")
                st.progress(min(count/10, 1.0))
        except Exception:
            st.error("Error cargando tickets")

    # --- CHAT ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Consulta sobre tickets o protocolos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analizando carga, especialidades y protocolos..."):
                # 1. RAG: Buscar contexto relevante en documentos
                rag_context = kb_service.search_context(prompt, n_results=25)
                
                # 2. LLM: Enviar todo a Gemini
                response = advisor.ask_advisor(
                    user_question=prompt,
                    workload_dict=workload,
                    rag_context=rag_context,
                    chat_history=st.session_state.messages,
                    unassigned_tickets=unassigned_list
                )
                
                st.write(response)
                
                # Debug visual (Opcional: mostrar qué encontró el RAG)
                if rag_context:
                    with st.expander("📚 Fuentes consultadas (RAG Context)"):
                        st.text(rag_context)

        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()

#Analiza los tickets sin asignar y recomiéndame asignaciones.