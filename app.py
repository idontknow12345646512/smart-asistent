import streamlit as st
import google.generativeai as genai

# --- KONFIGURACE KLÍČŮ ---
# Do Secrets v Streamlitu si přidej GOOGLE_API_KEY_1, GOOGLE_API_KEY_2 atd.
api_keys = [
    st.secrets.get("GOOGLE_API_KEY_1"),
    st.secrets.get("GOOGLE_API_KEY_2"),
    st.secrets.get("GOOGLE_API_KEY_3"),
    st.secrets.get("GOOGLE_API_KEY_4"),
    st.secrets.get("GOOGLE_API_KEY_5"),
    st.secrets.get("GOOGLE_API_KEY_6"),
    st.secrets.get("GOOGLE_API_KEY_7"),
    st.secrets.get("GOOGLE_API_KEY_8"),
    st.secrets.get("GOOGLE_API_KEY_9"),
    st.secrets.get("GOOGLE_API_KEY_10"),
    st.secrets.get("GOOGLE_API_KEY_11"),
    st.secrets.get("GOOGLE_API_KEY_12"),
    st.secrets.get("GOOGLE_API_KEY_13"),
    st.secrets.get("GOOGLE_API_KEY_14"),
    st.secrets.get("GOOGLE_API_KEY_15"),
    st.secrets.get("GOOGLE_API_KEY_16"),
    st.secrets.get("GOOGLE_API_KEY_17"),
    st.secrets.get("GOOGLE_API_KEY_18"),
    st.secrets.get("GOOGLE_API_KEY_19"),
    st.secrets.get("GOOGLE_API_KEY_20")
]
# Odfiltrujeme prázdné klíče
api_keys = [k for k in api_keys if k]

def get_smart_response(prompt, history):
    """Pokusí se získat odpověď postupně všemi klíči."""
    for key in api_keys:
        try:
            genai.configure(api_key=key)
            # Použijeme model, který ti minule fungoval
            model = genai.GenerativeModel(
                model_name="models/gemini-2.5-flash-lite",
                system_instruction="Jsi S.M.A.R.T., asistent jako Jarvis. Mluv česky a říkej mi Pane."
            )
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "Quota" in str(e):
                continue # Zkusíme další klíč v pořadí
            else:
                return f"Kritická chyba: {e}"
    return "Pane, všechny moje komunikační kanály jsou pro dnešek vyčerpány. Musíme počkat na reset limitů."

# --- ZBYTEK STREAMLIT APLIKACE ---
st.title("S.M.A.R.T. Multi-Core Terminal")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Vaše rozkazy, Pane?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Formátování historie pro Google
    formatted_history = []
    for m in st.session_state.messages[:-1]:
        role = "user" if m["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [m["content"]]})

    with st.chat_message("assistant"):
        with st.spinner("S.M.A.R.T. přepíná moduly..."):
            final_res = get_smart_response(prompt, formatted_history)
            st.write(final_res)
    
    st.session_state.messages.append({"role": "assistant", "content": final_res})
