import streamlit as st
import time

st.set_page_config(page_title="TARIC", page_icon="🇪🇺")

URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en"

if "started" not in st.session_state:
    st.session_state.started = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed" not in st.session_state:
    st.session_state.elapsed = None

col1, col2 = st.columns([1, 3])

with col1:
    if st.link_button("🇪🇺 TARIC'i Aç", URL):
        pass

    if st.button("▶ Sayacı Başlat"):
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.elapsed = None

    if st.session_state.started and st.button("⏹ Durdur"):
        st.session_state.elapsed = round(time.time() - st.session_state.start_time, 2)
        st.session_state.started = False

with col2:
    if st.session_state.elapsed is not None:
        st.metric("⏱ Açılma süresi", f"{st.session_state.elapsed} sn")
    elif st.session_state.started:
        placeholder = st.empty()
        while st.session_state.started:
            elapsed = round(time.time() - st.session_state.start_time, 2)
            placeholder.metric("⏱ Sayaç", f"{elapsed} sn")
            time.sleep(0.1)
            st.rerun()
    else:
        st.metric("⏱ Sayaç", "—")
