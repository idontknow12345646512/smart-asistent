import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random
import time

# --- KONFIGURACE PRO MOBILNÍ APP ---
st.set_page_config(
    page_title="S.M.A.R.T. App",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Tato funkce zkusí stáhnout obrázek. Pokud narazí na chybu, vrátí None.
def fetch_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=25, headers=headers)
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            return response.content
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ S.M.A.R.T. Nastavení")
    model_choice = st.radio("Jádro AI:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    image_mode = st.toggle("Mód generování obrázků 🎨")
    st.divider()
    if st.button("🗑️ Vyčistit chat"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminal")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_bytes" in msg and msg["image_bytes"]:
            st.image(msg["image_bytes"], use_container_width=True)

# --- LOGIKA VSTUPU ---
if prompt := st.chat_input("Zadejte příkaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if image_mode:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.info("⏳ Aktivuji vizuální jádro (Pokus 1/2)...")
            
            encoded_prompt = urllib.parse.quote(prompt)
            seed = random.randint(1, 100000)
            
            # --- POKUS 1: Hlavní generátor ---
            url1 = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=turbo"
            img_bytes = fetch_image(url1)
            
            # --- POKUS 2: Záložní generátor (pokud první selže) ---
            if not img_bytes:
                placeholder.warning("⚠️ První jádro nestíhá, zkouším záložní modul...")
                url2 = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true&seed={seed}"
                img_bytes = fetch_image(url2)
            
            if img_bytes:
                placeholder.empty()
                st.image(img_bytes, use_container_width=True)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Vizuál: {prompt}", 
                    "image_bytes": img_bytes
                })
            else:
                placeholder.error("❌ Všechna vizuální jádra jsou momentálně přetížená. Zkus to za chvíli znovu.")
    
    else:
        # KLASICKÝ TEXTOVÝ CHAT (S rotací klíčů)
        chat_context = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                        for m in st.session_state.messages[:-1] if "content" in m]

        response_text = "❌ Systém offline."
        for i, key in enumerate(api_keys):
            key_id = i + 1
            if global_store["key_status"].get(key_id) == "❌ LIMIT": continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_choice)
                chat = model.start_chat(history=chat_context)
                res = chat.send_message(prompt)
                response_text = res.text
                break 
            except Exception as e:
                if "429" in str(e): global_store["key_status"][key_id] = "❌ LIMIT"

        with st.chat_message("assistant"):
            st.write(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
