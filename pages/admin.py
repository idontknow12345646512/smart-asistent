import streamlit as st

st.set_page_config(page_title="S.M.A.R.T. Admin", layout="wide")

# Heslo pro přístup
password = st.sidebar.text_input("Zadejte Master Key", type="password")
if password != "radek123":
    st.error("Přístup k centrále je omezen.")
    st.stop()

st.title("🛡️ Centrála Operátora")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🔋 Stav API klíčů")
    # Zobrazí stav všech 10 klíčů v reálném čase
    if "key_usage" in st.session_state:
        for key, status in st.session_state.key_usage.items():
            color = "green" if status == "✅ OK" else "red"
            st.markdown(f"**{key}:** :{color}[{status}]")
    
    if st.button("Resetovat všechna jádra"):
        st.session_state.key_usage = {f"Jádro {i}": "✅ OK" for i in range(1, 11)}
        st.rerun()

with col2:
    st.subheader("🕵️ Reálný čas: Historie chatu")
    # Zde vidíš vše, co kdo napsal na hlavní stránce
    if "global_chat_history" in st.session_state and st.session_state.global_chat_history:
        for log in reversed(st.session_state.global_chat_history):
            with st.expander(f"[{log['time']}] Zpráva od uživatele"):
                st.write(log['text'])
    else:
        st.write("V síti je momentálně klid.")

# Automatické osvěžení pro Admina (každých 10 sekund)
# st.empty()
# st.button("Aktualizovat data") # Nebo použít st_autorefresh z externí knihovny
