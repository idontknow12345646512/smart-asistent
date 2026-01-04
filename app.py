import streamlit as st
import google.generativeai as genai

st.title("S.M.A.R.T. Diagnostika")

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    st.write("✅ Klíč načten. Prověřuji dostupné modely...")
    
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if available_models:
            st.success("Vaše API vidí tyto modely:")
            for model_name in available_models:
                st.write(f"- {model_name}")
            
            st.info("Zkopírujte jeden z těchto názvů výše a použijte ho v 'model_name=' ve svém kódu.")
        else:
            st.warning("Google nevrátil žádné modely. Váš klíč je pravděpodobně omezený.")
            
    except Exception as e:
        st.error(f"Nepodařilo se spojit s Googlem: {e}")
else:
    st.error("Klíč nenalezen v Secrets!")
