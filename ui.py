import streamlit as st
import requests
import uuid
import os

st.set_page_config(page_title="Aegis-Ops SRE", page_icon="🛡️", layout="wide")

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.title("🛡️ Aegis-Ops: Stateful Auto-Healer")
st.caption("Human-in-the-Loop (HITL) LangGraph Execution with MemorySaver")

# Session state to hold our active incident thread
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "incident_active" not in st.session_state:
    st.session_state.incident_active = False
if "frozen_state" not in st.session_state:
    st.session_state.frozen_state = None

st.markdown("### 1. Trigger Production Incident")
incident_input = st.text_input(
    "Alert Description:",
    placeholder="e.g., CRITICAL: API Gateway latency spiking to 5000ms, DB connection pool exhausted."
)

if st.button("🚨 Simulate PagerDuty Alert", type="primary", disabled=st.session_state.incident_active):
    if not incident_input:
        st.warning("Provide an alert description.")
    else:
        with st.spinner("AI Investigator & Resolver analyzing..."):
            # Generate fresh thread for LangGraph memory tracking
            st.session_state.thread_id = str(uuid.uuid4()) 
            
            try:
                res = requests.post(
                    f"{API_URL}/api/v1/trigger",
                    json={"thread_id": st.session_state.thread_id, "description": incident_input}
                )
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.frozen_state = data.get("state")
                    st.session_state.incident_active = True
                    st.rerun()
                else:
                    st.error(f"API Error: {res.text}")
            except requests.exceptions.ConnectionError:
                st.error("Backend unreachable. Ensure FastAPI is running on port 8000!")

# ==========================================
# HITL INTERRUPT UI (Only shows when graph is paused)
# ==========================================
if st.session_state.incident_active and st.session_state.frozen_state:
    st.divider()
    st.error("⚠️ SYSTEM PAUSED: HUMAN OVERRIDE REQUIRED BEFORE EXECUTION")
    
    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### 🕵️ AI Investigation Report")
        st.info(st.session_state.frozen_state.get("investigation_report", "N/A"))
    with cols[1]:
        st.markdown("#### 🛠️ AI Proposed Infrastructure Fix")
        st.warning(st.session_state.frozen_state.get("proposed_fix", "N/A"))
        
    feedback_input = st.text_input("Optional Instructions to Agent:", placeholder="e.g., Scale up by 4 instead of 2.")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("✅ APPROVE Execution"):
            with st.spinner("Waking up graph and executing..."):
                try:
                    res = requests.post(
                        f"{API_URL}/api/v1/resolve",
                        json={"thread_id": st.session_state.thread_id, "is_approved": True, "feedback": feedback_input}
                    )
                    if res.status_code == 200:
                        st.success("✅ Fix Executed!")
                        st.code(res.json().get("log", ""))
                        st.session_state.incident_active = False
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Error: {str(e)}")
                    
    with c2:
        if st.button("❌ DENY & Abort"):
            with st.spinner("Aborting Graph..."):
                try:
                    res = requests.post(
                        f"{API_URL}/api/v1/resolve",
                        json={"thread_id": st.session_state.thread_id, "is_approved": False, "feedback": feedback_input}
                    )
                    if res.status_code == 200:
                        st.error("❌ Execution Aborted.")
                        st.code(res.json().get("log", ""))
                        st.session_state.incident_active = False
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Error: {str(e)}")