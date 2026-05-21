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

# Session state
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "running" not in st.session_state:
    st.session_state.running = False
if "df" not in st.session_state:
    st.session_state.df = None
if "result_url" not in st.session_state:
    st.session_state.result_url = None

def taric_get_result_url(goods_code, country_code, sim_date):
    """
    headless=True ile formu doldurup 'Retrieve Measures'e basar,
    yönlendirilen sonuç URL'sini döndürür.
    """
    from playwright.sync_api import sync_playwright

    result_url = None
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#taricCode", timeout=30000)

        page.fill("#taricCode", goods_code)

        if country_code and country_code.strip() not in ("", "----------"):
            page.select_option("#taricArea", value=country_code)

        page.fill("#SimDatePic", sim_date)
        page.dispatch_event("#SimDatePic", "change")
        time.sleep(1)

        page.click("button:has-text('Retrieve Measures')")
        time.sleep(5)

        result_url = page.url
        browser.close()

    return result_url

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
        st.session_state.result_url = None
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

    # Önceki sorgu sonucu varsa linki göster
    if st.session_state.result_url:
        st.success("✅ Sorgu tamamlandı! Sonuçları yeni sekmede açmak için tıklayın:")
        st.markdown(
            f'<a href="{st.session_state.result_url}" target="_blank">'
            f'🔗 TARIC Sonuçlarını Aç → {st.session_state.result_url[:80]}...</a>',
            unsafe_allow_html=True
        )
        st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"🔍 Sorgula ({goods})", key=f"sorgula_{i}"):
            with st.spinner(f"`{goods}` sorgulanıyor…"):
                try:
                    url = taric_get_result_url(goods, country, tarih)
                    st.session_state.result_url = url
                except Exception as e:
                    st.error(f"Hata: {e}")
                    st.session_state.result_url = None

            if i + 1 < len(df):
                st.session_state.current_index += 1
            else:
                st.session_state.running = False

            st.rerun()

    with col2:
        if st.button("⏹ Durdur", key="durdur"):
            st.session_state.running = False
            st.session_state.result_url = None
            st.warning("Durduruldu.")
            st.rerun()

elif not st.session_state.running and st.session_state.result_url:
    st.success("🎉 Tüm sorgular tamamlandı!")
    st.markdown(
        f'<a href="{st.session_state.result_url}" target="_blank">'
        f'🔗 Son Sorgu Sonuçlarını Aç</a>',
        unsafe_allow_html=True
    )
