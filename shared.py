import streamlit as st

# Tato funkce vytvoří jeden objekt v paměti serveru, který vidí úplně VŠICHNI
@st.cache_resource
def get_global_store():
    return {
        "logs": [],        # Tady budou zprávy všech lidí
        "key_status": {},  # Tady bude stav 10 klíčů
        "active_users": 0
    }

global_store = get_global_store()
