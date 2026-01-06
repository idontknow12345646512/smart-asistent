import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import random

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systémová jádra")
    # Opravené názvy modelů
    model_choice = st.radio("Výkon:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    image_mode = st.toggle("Grafický procesor (Imagen) 🎨")
    st.divider()
    if st.button("🗑️ Resetovat"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení chatu
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_data" in msg:
            st.image(msg["image_data"], use_container_width=True)

# --- HLAVNÍ LOGIKA ---
if prompt := st.chat_input("Příkaz pro S.M.A.R.T..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Nalezení funkčního klíče
    active_key = None
    for key in api_keys:
        try:
            genai.configure(api_key=key)
            # Zkusíme vytvořit model jen pro test klíče
            test_model = genai.GenerativeModel(model_choice)
            active_key = key
            break
        except:
            continue

    if not active_key:
        st.error("🚨 Žádné API klíče nefungují.")
        st.stop()

    with st.chat_message("assistant"):
        if image_mode:
            status = st.empty()
            status.info("🎨 Gemini Imagen připravuje vizualizaci...")
            
            try:
                # POUŽITÍ IMAGEN MODELU PŘÍMO PŘES GOOGLE API
                # Poznámka: Tento model musí být povolen ve tvém Google AI Studiu
                img_model = genai.GenerativeModel('imagen-3.0-generate-001')
                
                # Imagen vyžaduje specifické volání
                response = img_model.generate_content(prompt)
                
                # Získání obrázku z odpovědi
                if response.candidates[0].content.parts[0].inline_data:
                    img_data = response.candidates[0].content.parts[0].inline_data.data
                    status.empty()
                    st.image(img_data, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"✅ Vygenerováno přes Imagen: {prompt}", 
                        "image_data": img_data
                    })
                else:
                    status.error("❌ Model Imagen vrátil prázdná data. Zkontroluj, zda máš tento model v AI Studiu povolen.")
            
            except Exception as e:
                # Pokud Imagen selže (často kvůli regionálnímu omezení), Gemini to zkusí popsat aspoň textem
                status.error(f"Chyba Imagen modulu: {str(e)}")
                st.info("Tip: Imagen 3 vyžaduje specifické nastavení v Google Cloud. Pokud nejede, zkontroluj povolené modely v AI Studiu.")
        
        else:
            # KLASICKÝ TEXTOVÝ CHAT
            status = st.empty()
            status.info("📡 Přenos dat...")
            
            model = genai.GenerativeModel(model_choice)
            chat_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                            for m in st.session_state.messages[:-1] if "content" in m]
            
            try:
                chat = model.start_chat(history=chat_history)
                response = chat.send_message(prompt)
                status.empty()
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                status.error(f"Chyba Gemini: {str(e)}")
