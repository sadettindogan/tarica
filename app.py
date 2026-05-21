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
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "running" not in st.session_state:
    st.session_state.running = False
if "df" not in st.session_state:
    st.session_state.df = None

def taric_sorgula(goods_code, country_code, sim_date):
    """
    Playwright ile TARIC sitesine bağlanır, formu doldurur
    ve 'Retrieve Measures' butonuna basar. Tarayıcı görünür
    şekilde (headless=False) yeni bir pencerede açılır.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#taricCode", timeout=30000)

        # Goods Code
        page.fill("#taricCode", goods_code)

        # Ülke seç
        if country_code and country_code.strip() not in ("", "----------"):
            page.select_option("#taricArea", value=country_code)

        # Tarih
        page.fill("#SimDatePic", sim_date)
        page.dispatch_event("#SimDatePic", "change")
        time.sleep(1)

        # Sorgula
        page.click("button:has-text('Retrieve Measures')")

        # Sonuç yüklenene kadar bekle; pencere kullanıcıya açık kalır
        time.sleep(5)

        # Pencereyi açık bırakmak için kullanıcı kapatana dek bekle
        # (page.is_closed() False olduğu sürece döngüde kal)
        st.toast(f"✅ {goods_code} sorgulandı — tarayıcı penceresi açık.")
        while not page.is_closed():
            time.sleep(1)

        browser.close()

# --- UI ---
st.subheader("📋 Excel'den Yapıştır")
st.caption("Goods Code, Origin/Destination, Date sütunlarını Excel'den kopyalayıp yapıştırın")
pasted = st.text_area(
    "Buraya yapıştırın",
    height=120,
    placeholder="0101210000\tTR\t1.01.2024\n0202100000\tDE\t1.01.2024"
)

if pasted.strip():
    try:
        df = pd.read_csv(
            StringIO(pasted.strip()), sep="\t", header=None,
            names=["Goods Code", "Origin/Destination", "Date"]
        )
        df["Goods Code"] = (
            df["Goods Code"].astype(str).str.strip()
            .str.replace(".", "", regex=False).str[:10]
        )
        df["Origin/Destination"] = df["Origin/Destination"].astype(str).apply(ulke_kodu)
        df["Date"] = df["Date"].astype(str).str.strip()
        st.session_state.df = df
        st.session_state.current_index = 0
        st.session_state.running = True
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Yapıştırma hatası: {e}")

df = st.session_state.df

# Sorgulama arayüzü
if st.session_state.running and df is not None:
    i = st.session_state.current_index
    row = df.iloc[i]
    goods   = row["Goods Code"]
    country = row["Origin/Destination"]
    tarih   = row["Date"]

    st.info(f"**Sıradaki sorgu [{i+1}/{len(df)}]:** `{goods}` / `{country}` / `{tarih}`")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"🔍 Sorgula ({goods})", key=f"sorgula_{i}"):
            with st.spinner(f"{goods} sorgulanıyor, tarayıcı açılıyor…"):
                taric_sorgula(goods, country, tarih)

            if i + 1 < len(df):
                st.session_state.current_index += 1
                next_row = df.iloc[i + 1]
                st.info(
                    f"Sonraki: `{next_row['Goods Code']}` / "
                    f"`{next_row['Origin/Destination']}` / `{next_row['Date']}`"
                )
            else:
                st.success("🎉 Tüm sorgular tamamlandı!")
                st.session_state.running = False
            st.rerun()

    with col2:
        if st.button("⏹ Durdur", key="durdur"):
            st.session_state.running = False
            st.warning("Durduruldu.")
            st.rerun()
