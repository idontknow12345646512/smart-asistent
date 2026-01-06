import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random

st.set_page_config(page_title="S.M.A.R.T. Ultimate", page_icon="🤖", layout="wide")

def fetch_img(url):
    try:
        # Náhodný User-Agent pro obcházení limitů
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36',
            'Mozilla/5.0 (Linux; Android 10; SM-G960F) Chrome/110.0.0.0'
        ]
        headers = {'User-Agent': random.choice(agents)}
        res = requests.get(url, timeout=25, headers=headers)
        if res.status_code == 200 and 'image' in res.headers.get('content-type', ''):
            return res.content
    except:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ S.M.A.R.T. Ovládání")
    model_choice = st.radio("Jádro AI:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    image_mode = st.toggle("Mód obrázků 🎨")
    if st.button("🗑️ Reset chatu"):
        st.session_state.messages = []
        st.rerun()

api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_bytes" in msg:
            st.image(msg["image_bytes"], use_container_width=True)

# --- LOGIKA VSTUPU ---
if prompt := st.chat_input("Zadejte příkaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if image_mode:
        with st.chat_message("assistant"):
            p = st.empty()
            encoded = urllib.parse.quote(prompt)
            seed = random.randint(1, 999999)
            
            # --- ZKOUŠÍME 3 RŮZNÁ JÁDRA ---
            p.info("🛰️ Zkouším Jádro 1 (Turbo)...")
            img = fetch_img(f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed={seed}&model=turbo")
            
            if not img:
                p.warning("🛰️ Jádro 1 selhalo. Zkouším Jádro 2 (Flux)...")
                img = fetch_img(f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed={seed}&model=flux")
                
            if not img:
                p.warning("🛰️ Jádro 2 selhalo. Zkouším Jádro 3 (Záložní)...")
                # Tento odkaz používá jinou cestu k serveru
                img = fetch_img(f"https://image.pollinations.ai/prompt/{encoded}?seed={seed}&width=1024&height=1024&nologo=true")

            if img:
                p.empty()
                st.image(img, use_container_width=True)
                st.session_state.messages.append({"role": "assistant", "content": f"Vizuál: {prompt}", "image_bytes": img})
            else:
                p.error("❌ Všechny generátory jsou přetížené. Školní síť vás možná blokuje.")
    
    else:
        # Klasický textový chat s rotací klíčů
        chat_context = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                        for m in st.session_state.messages[:-1] if "content" in m]
        
        response_text = "❌ Offline."
        for i, key in enumerate(api_keys):
            key_id = i + 1
            if global_store.get("key_status", {}).get(key_id) == "❌ LIMIT": continue
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
