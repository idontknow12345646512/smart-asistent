import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
import random

# --- KONFIGURACE PRO TELEFONY ---
st.set_page_config(
    page_title="S.M.A.R.T. App",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Funkce pro stažení obrázku s lepším ošetřením chyb
def get_image_data(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, timeout=40, headers=headers)
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            return response.content
    except Exception:
        return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ S.M.A.R.T. Config")
    model_choice = st.radio("Jádro AI:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    st.divider()
    image_mode = st.toggle("Mód generování obrázků 🎨")
    st.caption("Tip: Pokud obrázek nefunguje, zkus zadání v angličtině.")
    if st.button("🗑️ Vyčistit chat"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. App")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Zobrazení historie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_bytes" in msg and msg["image_bytes"]:
            st.image(msg["image_bytes"], use_container_width=True)

# --- VSTUP ---
if prompt := st.chat_input("Zadejte příkaz..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    if image_mode:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.info("🚀 Připravuji vizualizaci přes Turbo jádro...")
            
            # Zkusíme modernější model "turbo" pro vyšší stabilitu
            encoded_prompt = urllib.parse.quote(prompt)
            seed = random.randint(1, 999999)
            image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}&nologo=true&model=turbo"
            
            img_bytes = get_image_data(image_url)
            
            if img_bytes:
                placeholder.empty()
                st.image(img_bytes, use_container_width=True)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Snímek: {prompt}", 
                    "image_bytes": img_bytes
                })
            else:
                placeholder.error("📡 Spojení s kreslícím modulem selhalo. Zkuste to za 10 sekund.")
    else:
        # Klasický Gemini chat s rotací klíčů
        chat_context = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                        for m in st.session_state.messages[:-1] if "content" in m]

        response_text = "❌ Všechna jádra offline."
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
