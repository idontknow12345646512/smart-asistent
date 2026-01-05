import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store  # Importujeme sdílenou paměť pro admina

st.set_page_config(page_title="S.M.A.R.T. Chat", page_icon="🤖")

# --- NASTAVENÍ KLÍČŮ ---
# Načtení klíčů 1-10 ze Secrets
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")
st.caption("Školní komunikační rozhraní připojené k centrále")

# Lokální paměť pro konkrétního uživatele (aby si spolužáci nečetli navzájem chat)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie chatu daného uživatele
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- HLAVNÍ LOGIKA CHATU ---
if prompt := st.chat_input("Zadejte příkaz pro S.M.A.R.T.a..."):
    now = datetime.now().strftime("%H:%M:%S")
    
    # 1. ZÁPIS DO SDÍLENÉ PAMĚTI (Uvidíš to v Admin panelu v reálném čase)
    global_store["logs"].append({"time": now, "user": "Student", "text": prompt})
    
    # Uložíme do lokálního okna spolužáka
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. LOGIKA AI S ROTACÍ KLÍČŮ
    response_text = "Všechna systémová jádra jsou momentálně přetížena. Zkuste to za chvíli, Pane."
    
    for i, key in enumerate(api_keys):
        key_id = i + 1
        # Kontrola v globálním skladu, jestli tento klíč už není vyčerpaný
        if global_store["key_status"].get(key_id) == "❌ LIMIT":
            continue
        
        try:
            genai.configure(api_key=key)
            # Používáme 2.5 Flash Lite pro rychlost a stabilitu ve třídě
            model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
            res = model.generate_content(prompt)
            response_text = res.text
            break # Našli jsme funkční klíč, ukončíme hledání
            
        except Exception as e:
            # Pokud dojde k vyčerpání limitu, zapíšeme to do globálního skladu
            if "429" in str(e) or "Quota" in str(e):
                global_store["key_status"][key_id] = "❌ LIMIT"
                continue # Jdeme na další klíč
            else:
                response_text = f"Chyba spojení s jádrem {key_id}: {str(e)}"
    
    # Zobrazení odpovědi spolužákovi
    with st.chat_message("assistant"):
        st.write(response_text)
    
    st.session_state.messages.append({"role": "assistant", "content": response_text})
