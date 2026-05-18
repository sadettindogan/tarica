import streamlit as st
import subprocess
import sys
import time
import pandas as pd
import json
from io import StringIO

URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en"

st.set_page_config(page_title="TARIC", page_icon="🇪🇺")
st.title("🇪🇺 TARIC Consultation")

@st.cache_resource(show_spinner="Playwright kuruluyor...")
def install_playwright():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True
    )

install_playwright()

@st.cache_resource
def load_ulkeler():
    with open("ulkeler.json", "r", encoding="utf-8") as f:
        return json.load(f)

ulkeler = load_ulkeler()

def ulke_kodu(ulke_adi: str) -> str:
    key = ulke_adi.strip().upper()
    return ulkeler.get(key, ulke_adi.strip())

# Session state başlat
if "browser" not in st.session_state:
    st.session_state.browser = None
if "page" not in st.session_state:
    st.session_state.page = None
if "pw" not in st.session_state:
    st.session_state.pw = None
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "running" not in st.session_state:
    st.session_state.running = False
if "df" not in st.session_state:
    st.session_state.df = None

def taric_ara(page, goods_code, country_code, sim_date):
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#taricCode", timeout=30000)
    page.fill("#taricCode", goods_code)
    if country_code and country_code != "----------":
        page.select_option("#taricArea", value=country_code)
    page.fill("#SimDatePic", sim_date)
    page.dispatch_event("#SimDatePic", "change")
    time.sleep(2)
    page.click("button:has-text('Retrieve Measures')")
    time.sleep(5)

# --- UI ---
st.subheader("📋 Excel'den Yapıştır")
st.caption("Goods Code, Origin/Destination, Date sütunlarını Excel'den kopyalayıp yapıştırın")
pasted = st.text_area("Buraya yapıştırın", height=120, placeholder="0101210000\tTR\t1.01.2024\n0202100000\tDE\t1.01.2024")

if pasted.strip():
    try:
        df = pd.read_csv(StringIO(pasted.strip()), sep="\t", header=None,
                         names=["Goods Code", "Origin/Destination", "Date"])
        df["Goods Code"] = df["Goods Code"].astype(str).str.strip().str.replace(".", "", regex=False).str[:10]
        df["Origin/Destination"] = df["Origin/Destination"].astype(str).apply(ulke_kodu)
        df["Date"] = df["Date"].astype(str).str.strip()
        st.session_state.df = df
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Yapıştırma hatası: {e}")

df = st.session_state.df

# Tarayıcı aç butonu
if st.button("🌐 Siteyi Aç", disabled=(df is None)):
    from playwright.sync_api import sync_playwright
    if st.session_state.pw is None:
        st.session_state.pw = sync_playwright().start()
    if st.session_state.browser is None:
        st.session_state.browser = st.session_state.pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
    if st.session_state.page is None:
        st.session_state.page = st.session_state.browser.new_page(viewport={"width": 1280, "height": 900})
    st.session_state.page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    st.session_state.current_index = 0
    st.session_state.running = True
    st.success("✅ Tarayıcı açıldı! İlk sorgu için 'Ara' butonuna basın.")

# Ara / Sonraki butonu
if st.session_state.running and df is not None:
    i = st.session_state.current_index
    row = df.iloc[i]
    goods = row["Goods Code"]
    country = row["Origin/Destination"]
    tarih = row["Date"]

    st.info(f"**Sıradaki sorgu [{i+1}/{len(df)}]:** {goods} / {country} / {tarih}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"▶ Ara ({goods})", key=f"ara_{i}"):
            with st.spinner("Sorgulanıyor..."):
                taric_ara(st.session_state.page, goods, country, tarih)
            st.success(f"✅ {goods} / {country} / {tarih} sorgulandı!")

            if i + 1 < len(df):
                st.session_state.current_index += 1
                st.info(f"Sonraki: {df.iloc[i+1]['Goods Code']} / {df.iloc[i+1]['Origin/Destination']} / {df.iloc[i+1]['Date']}")
            else:
                st.success("🎉 Tüm sorgular tamamlandı!")
                st.session_state.running = False
            st.rerun()

    with col2:
        if st.button("⏹ Durdur", key="durdur"):
            st.session_state.running = False
            if st.session_state.browser:
                st.session_state.browser.close()
                st.session_state.browser = None
                st.session_state.page = None
            if st.session_state.pw:
                st.session_state.pw.stop()
                st.session_state.pw = None
            st.warning("Durduruldu.")
            st.rerun()
