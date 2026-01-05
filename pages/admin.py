import streamlit as st
from shared import global_store  # Připojení ke společnému mozku
from datetime import datetime

st.set_page_config(page_title="S.M.A.R.T. Admin", layout="wide", page_icon="🛡️")

# --- HESLO OPERÁTORA ---
with st.sidebar:
    st.title("🔐 Přihlášení")
    password = st.text_input("Zadejte Master Key", type="password")
    
    if password != "radek123":
        st.error("Nepovolený přístup k jádru!")
        st.stop()
    
    st.success("Přístup povolen, Pane.")
    
    # Tlačítka pro rychlou správu
    if st.button("🔄 Obnovit data (Refresh)"):
        st.rerun()
    
    if st.button("🗑️ Vymazat historii chatu"):
        global_store["logs"] = []
        st.success("Historie vymazána.")
        st.rerun()

st.title("🛡️ Centrála Operátora (Real-Time)")

# Rozdělení obrazovky na dva sloupce
col1, col2 = st.columns([1, 2])

# --- LEVÝ SLOUPEC: STAV KLÍČŮ ---
with col1:
    st.subheader("🔋 Stav energetických jader")
    # Procházíme všech 10 klíčů a zjišťujeme stav z global_store
    for i in range(1, 11):
        status = global_store["key_status"].get(i, "✅ OK")
        color = "green" if status == "✅ OK" else "red"
        st.markdown(f"**Jádro {i}:** :{color}[{status}]")
    
    if st.button("♻️ Resetovat všechna jádra"):
        global_store["key_status"] = {}
        st.success("Jádra byla restartována.")
        st.rerun()

# --- PRAVÝ SLOUPEC: HISTORIE TŘÍDY ---
with col2:
    st.subheader("🕵️ Monitoring komunikace")
    
    if global_store["logs"]:
        # Zobrazíme zprávy od nejnovější po nejstarší
        for log in reversed(global_store["logs"]):
            with st.expander(f"🕒 {log['time']} | Zpráva od uživatele"):
                st.write(log['text'])
    else:
        st.info("V síti nebyla zaznamenána žádná aktivita.")

# --- AUTO REFRESH (UPOZORNĚNÍ) ---
st.caption("Poznámka: Pro nejnovější data klikněte na 'Obnovit data' vlevo.")
