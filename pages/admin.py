import streamlit as st
from shared import global_store 
from datetime import datetime

st.set_page_config(page_title="S.M.A.R.T. Admin", layout="wide", page_icon="🛡️")

# --- HESLO OPERÁTORA ---
with st.sidebar:
    st.title("🔐 Přihlášení")
    password = st.text_input("Zadejte Master Key", type="password")
    
    if password != "Rdkakrtx1@MilujiKocky<3":
        st.error("Nepovolený přístup k jádru!")
        st.stop()
    
    st.success("Přístup povolen, Pane.")
    
    if st.button("🔄 Obnovit data (Refresh)"):
        st.rerun()
    
    if st.button("🗑️ Vymazat historii chatu"):
        global_store["logs"] = []
        st.success("Historie vymazána.")
        st.rerun()

st.title("🛡️ Centrála Operátora (Real-Time)")

col1, col2 = st.columns([1, 2])

# --- LEVÝ SLOUPEC: STAV KLÍČŮ ---
with col1:
    st.subheader("🔋 Stav energetických jader")
    for i in range(1, 11):
        status = global_store["key_status"].get(i, "✅ OK")
        color = "green" if status == "✅ OK" else "red"
        st.markdown(f"**Jádro {i}:** :{color}[{status}]")
    
    if st.button("♻️ Resetovat všechna jádra"):
        global_store["key_status"] = {}
        st.success("Jádra byla restartována.")
        st.rerun()

# --- PRAVÝ SLOUPEC: MONITORING KOMUNIKACE ---
with col2:
    st.subheader("🕵️ Monitoring komunikace")
    
    if global_store["logs"]:
        for log in reversed(global_store["logs"]):
            # Expander teď ukazuje čas a náhled otázky
            with st.expander(f"🕒 {log['time']} | {log['user_text'][:40]}..."):
                st.write("**Uživatel:**")
                st.info(log['user_text'])
                st.write("**S.M.A.R.T. Odpověď:**")
                st.success(log['ai_text'])
    else:
        st.info("V síti nebyla zaznamenána žádná aktivita.")

st.caption("Poznámka: Pro nejnovější data klikněte na 'Obnovit data' vlevo.")

