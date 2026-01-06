import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import urllib.parse
import requests
from io import BytesIO

# --- KONFIGURACE ---
st.set_page_config(
    page_title="S.M.A.R.T. App",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- OPRAVENÁ FUNKCE PRO STAŽENÍ OBRÁZKU ---
def get_image_data(url):
    try:
        # Přidali jsme 'User-Agent', aby nás web neblokoval jako robota
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=30, headers=headers)
        
        # Kontrola, zda je odpověď opravdu obrázek
        content_type = response.headers.get('content-type', '')
        if response.status_code == 200 and 'image' in content_type:
            return response.content
        else:
            return None
    except Exception:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Konfigurace")
    model_choice = st.radio("Model:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    st.divider()
    image_mode = st.toggle("Mód generování obrázků 🎨")
    if st.button("🗑️ Vymazat historii"):
        st.session_state.messages = []
        st.rerun()

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

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
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    log_entry = {"time": now, "user_text": prompt, "ai_text": "Zpracovávám..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    if image_mode:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.write("🎨 Kreslím... (může to trvat 10-20 sekund)")
            
            encoded_prompt = urllib.parse.quote(prompt)
            seed = datetime.now().microsecond
            # Změna: Používáme stabilnější URL bez parametrů, které by mohly zlobit
            image_url = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&seed={seed}"
            
            img_bytes = get_image_data(image_url)
            
            if img_bytes:
                status_placeholder.empty()
                st.image(img_bytes, use_container_width=True)
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": f"Hotovo: {prompt}", 
                    "image_bytes": img_bytes
                })
                global_store["logs"][current_log_index]["ai_text"] = "[OBRÁZEK OK]"
            else:
                status_placeholder.error("❌ Generátor teď nestíhá. Zkus to prosím za chvilku nebo s jiným zadáním.")
    
    else:
        # TEXTOVÝ CHAT (Rotace klíčů)
        chat_context = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            if "content" in m:
                chat_context.append({"role": role, "parts": [m["content"]]})

        response_text = "⚠️ Jádra offline."
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
        global_store["logs"][current_log_index]["ai_text"] = response_text
