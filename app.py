import streamlit as st
import google.generativeai as genai
from datetime import datetime
from shared import global_store 
import streamlit.components.v1 as components
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="S.M.A.R.T. Voice & Image", page_icon="🎙️")

# --- FUNKCE: AI MLUVÍ ČESKY ---
def speak_text(text):
    # Ošetření textu pro JavaScript (odstranění uvozovek a zalomení řádků)
    safe_text = text.replace("'", "").replace('"', "").replace("\n", " ")
    js_code = f"""
        <script>
        window.speechSynthesis.cancel(); // Zastaví předchozí mluvení, pokud ještě běží
        var msg = new SpeechSynthesisUtterance('{safe_text}');
        msg.lang = 'cs-CZ'; 
        msg.rate = 1.0; 
        window.speechSynthesis.speak(msg);
        </script>
    """
    components.html(js_code, height=0)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Systém S.M.A.R.T.")
    voice_enabled = st.toggle("Hlasová odpověď AI 🔊", value=True)
    image_mode = st.toggle("Mód generování obrázků 🎨")
    model_choice = st.selectbox("Model AI:", ["gemini-2.5-flash-lite", "gemini-1.5-pro"])
    st.divider()
    st.write("🎤 **Mluv na S.M.A.R.T.a:**")
    audio_input = mic_recorder(start_prompt="Nahrávat hlas 🎙️", stop_prompt="Odeslat ⚡", key='mic')

# Načtení klíčů
api_keys = [st.secrets.get(f"GOOGLE_API_KEY_{i}") for i in range(1, 11) if st.secrets.get(f"GOOGLE_API_KEY_{i}")]

st.title("🤖 S.M.A.R.T. Terminál")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "image_url" in msg:
            st.image(msg["image_url"])

# --- BEZPEČNÉ ZPRACOVÁNÍ VSTUPU ---
input_text = st.chat_input("Napiš nebo použij mikrofon...")

# Oprava KeyError: Kontrola, zda audio_input existuje a obsahuje klíč 'text'
if audio_input is not None:
    if isinstance(audio_input, dict) and audio_input.get('text'):
        input_text = audio_input['text']

if input_text:
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({"role": "user", "content": input_text})
    
    with st.chat_message("user"):
        st.write(input_text)

    log_entry = {"time": now, "user_text": input_text, "ai_text": "Zpracovávám..."}
    global_store["logs"].append(log_entry)
    current_log_index = len(global_store["logs"]) - 1

    if image_mode:
        image_url = f"https://pollinations.ai/p/{input_text.replace(' ', '_')}?width=1024&height=1024&seed=42"
        response_text = f"Generuji obrázek pro: {input_text}"
        with st.chat_message("assistant"):
            st.write(response_text)
            st.image(image_url)
        st.session_state.messages.append({"role": "assistant", "content": response_text, "image_url": image_url})
        global_store["logs"][current_log_index]["ai_text"] = "[Obrázek]"
        if voice_enabled:
            speak_text("Obrázek je hotový.")
    
    else:
        chat_context = []
        for m in st.session_state.messages[:-1]:
            role = "user" if m["role"] == "user" else "model"
            if "content" in m:
                chat_context.append({"role": role, "parts": [m["content"]]})

        response_text = "Všechna jádra offline."
        for i, key in enumerate(api_keys):
            key_id = i + 1
            if global_store["key_status"].get(key_id) == "❌ LIMIT": continue
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_choice)
                chat = model.start_chat(history=chat_context)
                res = chat.send_message(input_text)
                response_text = res.text
                break 
            except Exception as e:
                if "429" in str(e): global_store["key_status"][key_id] = "❌ LIMIT"

        with st.chat_message("assistant"):
            st.write(response_text)
            if voice_enabled:
                speak_text(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        global_store["logs"][current_log_index]["ai_text"] = response_text
