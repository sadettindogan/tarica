import streamlit as st

st.set_page_config(page_title="TARIC", page_icon="🇪🇺", layout="wide")

URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en"

if "dar" not in st.session_state:
    st.session_state.dar = False

col1, col2 = st.columns([1, 8])

with col1:
    st.link_button("🇪🇺 TARIC'i Aç", URL)

with col2:
    if st.button("🔲 Daralt" if not st.session_state.dar else "⬜ Genişlet"):
        st.session_state.dar = not st.session_state.dar

if st.session_state.dar:
    st.markdown("""
        <style>
        .main .block-container { max-width: 400px !important; }
        </style>
    """, unsafe_allow_html=True)
