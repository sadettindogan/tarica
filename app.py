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

def search_taric(goods_code: str, country_code: str, sim_date: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
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

        screenshot_path = f"/tmp/taric_{goods_code}_{country_code}.png"
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

    return screenshot_path

# --- UI ---
st.subheader("📋 Excel'den Yapıştır")
st.caption("Goods Code, Origin/Destination, Date sütunlarını Excel'den kopyalayıp yapıştırın")
pasted = st.text_area("Buraya yapıştırın", height=120, placeholder="0101210000\tTR\t1.01.2024\n0202100000\tDE\t1.01.2024")

df = None
if pasted.strip():
    try:
        df = pd.read_csv(StringIO(pasted.strip()), sep="\t", header=None,
                         names=["Goods Code", "Origin/Destination", "Date"])
        df["Goods Code"] = df["Goods Code"].astype(str).str.strip().str.replace(".", "", regex=False).str[:10]
        df["Origin/Destination"] = df["Origin/Destination"].astype(str).apply(ulke_kodu)
        df["Date"] = df["Date"].astype(str).str.strip()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Yapıştırma hatası: {e}")

st.link_button("🌐 Siteyi Aç", URL)
search_btn = st.button("🔍 Ara", disabled=(df is None))

if search_btn and df is not None:
    for i, row in df.iterrows():
        goods = row["Goods Code"]
        country = row["Origin/Destination"]
        tarih = row["Date"]
        with st.spinner(f"[{i+1}/{len(df)}] {goods} / {country} / {tarih} aranıyor..."):
            try:
                screenshot = search_taric(goods, country, tarih)
                st.success(f"✅ {goods} / {country} / {tarih}")
                st.image(screenshot, use_container_width=True)
                with open(screenshot, "rb") as f:
                    st.download_button(f"📥 İndir ({goods})", f, f"taric_{goods}_{country}.png", "image/png", key=f"dl_{i}")
            except Exception as e:
                st.error(f"❌ {goods} / {country}: {e}")
