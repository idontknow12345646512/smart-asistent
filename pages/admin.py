import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="S.M.A.R.T. Admin", page_icon="🔐")

st.title("🔐 S.M.A.R.T. Administrace")

# Heslo pro přístup
pw = st.text_input("Zadejte administrátorské heslo", type="password")

if pw == st.secrets["ADMIN_PASSWORD"]:
    st.success("Přístup povolen")
    
    tab1, tab2, tab3 = st.tabs(["📊 Statistiky & Tabulky", "🧠 AI Konfigurace", "🛠 Systém"])
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    with tab1:
        st.subheader("Data z Google Sheets")
        try:
            # Načtení tabulky Users
            users_data = conn.read(worksheet="Users", ttl=0)
            st.write("**Tabulka Users (Historie chatů):**")
            st.dataframe(users_data, use_container_width=True)
            
            # Tlačítko pro stažení zálohy
            csv = users_data.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Stáhnout zálohu Users CSV", data=csv, file_name="smart_backup.csv")
            
        except Exception as e:
            st.error(f"Nepodařilo se načíst tabulky: {e}")

    with tab2:
        st.subheader("Nastavení inteligence")
        
        # Přepínač modelů
        current_model = st.session_state.get("selected_model", "gemini-2.5-flash")
        new_model = st.selectbox(
            "Aktivní AI Model:",
            ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
            index=["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"].index(current_model)
        )
        if new_model != current_model:
            st.session_state.selected_model = new_model
            st.success(f"Model změněn na {new_model}")

        st.divider()
        st.write("**Co by měla obsahovat AI stránka:**")
        st.info("""
        1. **Prompt Engineering:** Možnost změnit hlavní instrukci (System Instruction) bez přepisování kódu.
        2. **Temperature:** Posuvník pro kreativitu AI (0.0 = přesná, 1.0 = kreativní).
        3. **Token Limit:** Nastavení maximální délky odpovědi.
        4. **Usage Tracker:** Přehled kolik dotazů zbývá na jednotlivých API klíčích.
        """)

    with tab3:
        st.subheader("Správa systému")
        if st.button("🔥 Vymazat mezipaměť (Cache)"):
            st.cache_data.clear()
            st.success("Cache vymazána")

elif pw:
    st.error("Nesprávné heslo")
