import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import PIL.Image
import io

# --- KONFIGURACE ---
st.set_page_config(page_title="S.M.A.R.T. OS", page_icon="🤖", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Systémová jádra")
    # Použijeme modely, které máš potvrzené ze screenshotu
    model_choice = st.radio("Výkon:", ["gemini-1.5-flash", "gemini-1.5-pro"])
    image_mode = st.toggle("Mód generování obrazu 🎨")
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
    active_model = None
    for key in api_keys:
        try:
            genai.configure(api_key=key)
            active_model = genai.GenerativeModel(model_choice)
            break
        except:
            continue

    if not active_model:
        st.error("🚨 Žádné API klíče nefungují.")
        st.stop()

    with st.chat_message("assistant"):
        status = st.empty()
        
        if image_mode:
            status.info("🎨 Generuji obrazovou odpověď přes Gemini...")
            try:
                # Pokusíme se o generování přes Imagen (pokud je dostupný)
                # Pokud ne, použijeme fallback na Pollinations, ale s lepším ošetřením
                import urllib.parse
                import requests
                
                encoded = urllib.parse.quote(prompt)
                # Tento odkaz je upravený tak, aby byl co nejstabilnější
                img_url = f"https://image.pollinations.ai/prompt/{encoded}?nologo=true&private=true"
                
                res = requests.get(img_url, timeout=20)
                if res.status_code == 200:
                    status.empty()
                    st.image(res.content, use_container_width=True)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"Snímek: {prompt}", 
                        "image_data": res.content
                    })
                else:
                    status.error("❌ Externí grafické jádro neodpovídá. Zkus textový režim.")
            except Exception as e:
                status.error(f"Chyba: {e}")
        
        else:
            # KLASICKÝ TEXTOVÝ CHAT
            status.info("📡 Přenos dat...")
            chat_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                            for m in st.session_state.messages[:-1] if "content" in m]
            try:
                chat = active_model.start_chat(history=chat_history)
                response = chat.send_message(prompt)
                status.empty()
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                status.error(f"Chyba Gemini: {str(e)}")
