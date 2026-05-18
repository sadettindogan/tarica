import streamlit as st
import subprocess
import sys
import time
from datetime import date

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

COUNTRIES = {
    "-- Seçiniz --": "----------",
    "Afghanistan - AF": "AF", "Albania - AL": "AL", "Algeria - DZ": "DZ",
    "Andorra - AD": "AD", "Angola - AO": "AO", "Argentina - AR": "AR",
    "Armenia - AM": "AM", "Australia - AU": "AU", "Austria - AT": "AT",
    "Azerbaijan - AZ": "AZ", "Bahrain - BH": "BH", "Bangladesh - BD": "BD",
    "Belarus - BY": "BY", "Belgium - BE": "BE", "Brazil - BR": "BR",
    "Bulgaria - BG": "BG", "Canada - CA": "CA", "Chile - CL": "CL",
    "China - CN": "CN", "Colombia - CO": "CO", "Croatia - HR": "HR",
    "Cuba - CU": "CU", "Cyprus - CY": "CY", "Czechia - CZ": "CZ",
    "Denmark - DK": "DK", "Ecuador - EC": "EC", "Egypt - EG": "EG",
    "Estonia - EE": "EE", "Ethiopia - ET": "ET", "European Union - EU": "EU",
    "Finland - FI": "FI", "France - FR": "FR", "Georgia - GE": "GE",
    "Germany - DE": "DE", "Ghana - GH": "GH", "Greece - GR": "GR",
    "Hong Kong - HK": "HK", "Hungary - HU": "HU", "Iceland - IS": "IS",
    "India - IN": "IN", "Indonesia - ID": "ID", "Iran - IR": "IR",
    "Iraq - IQ": "IQ", "Ireland - IE": "IE", "Israel - IL": "IL",
    "Italy - IT": "IT", "Japan - JP": "JP", "Jordan - JO": "JO",
    "Kazakhstan - KZ": "KZ", "Kenya - KE": "KE", "Kuwait - KW": "KW",
    "Latvia - LV": "LV", "Lebanon - LB": "LB", "Libya - LY": "LY",
    "Lithuania - LT": "LT", "Luxembourg - LU": "LU", "Malaysia - MY": "MY",
    "Malta - MT": "MT", "Mexico - MX": "MX", "Moldova - MD": "MD",
    "Mongolia - MN": "MN", "Montenegro - ME": "ME", "Morocco - MA": "MA",
    "Myanmar - MM": "MM", "Netherlands - NL": "NL", "New Zealand - NZ": "NZ",
    "Nigeria - NG": "NG", "North Korea - KP": "KP", "North Macedonia - MK": "MK",
    "Norway - NO": "NO", "Oman - OM": "OM", "Pakistan - PK": "PK",
    "Panama - PA": "PA", "Peru - PE": "PE", "Philippines - PH": "PH",
    "Poland - PL": "PL", "Portugal - PT": "PT", "Qatar - QA": "QA",
    "Romania - RO": "RO", "Russian Federation - RU": "RU", "Saudi Arabia - SA": "SA",
    "Senegal - SN": "SN", "Serbia - XS": "XS", "Singapore - SG": "SG",
    "Slovakia - SK": "SK", "Slovenia - SI": "SI", "Somalia - SO": "SO",
    "South Africa - ZA": "ZA", "South Korea - KR": "KR", "Spain - ES": "ES",
    "Sri Lanka - LK": "LK", "Sudan - SD": "SD", "Sweden - SE": "SE",
    "Switzerland - CH": "CH", "Syria - SY": "SY", "Taiwan - TW": "TW",
    "Tajikistan - TJ": "TJ", "Thailand - TH": "TH", "Tunisia - TN": "TN",
    "Türkiye - TR": "TR", "Uganda - UG": "UG", "Ukraine - UA": "UA",
    "United Arab Emirates - AE": "AE", "United Kingdom - GB": "GB",
    "United States - US": "US", "Uruguay - UY": "UY", "Uzbekistan - UZ": "UZ",
    "Venezuela - VE": "VE", "Viet Nam - VN": "VN", "Yemen - YE": "YE",
    "Zambia - ZM": "ZM", "Zimbabwe - ZW": "ZW",
}

def search_taric(goods_code: str, country_code: str, sim_date: str):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Goods code
        page.wait_for_selector("#taricCode", timeout=30000)
        page.fill("#taricCode", goods_code)

        # Ülke
        if country_code and country_code != "----------":
            page.select_option("#taricArea", value=country_code)

        # Tarih — önce temizle sonra yaz, sonra change tetikle
        page.fill("#SimDatePic", sim_date)
        page.dispatch_event("#SimDatePic", "change")

        time.sleep(2)

        # Retrieve Measures butonuna tıkla
        page.click("button:has-text('Retrieve Measures')")

        # Sonuçların yüklenmesini bekle
        time.sleep(5)

        screenshot_path = "/tmp/taric_result.png"
        page.screenshot(path=screenshot_path, full_page=True)
        browser.close()

    return screenshot_path

# --- UI ---

# Excel yapıştırma alanı
st.subheader("📋 Excel'den Yapıştır")
st.caption("Goods Code, Origin/Destination, Date sütunlarını Excel'den kopyalayıp yapıştırın")
pasted = st.text_area("Buraya yapıştırın", height=120, placeholder="0101210000\tTR\t18-05-2026\n0202100000\tDE\t18-05-2026")

import pandas as pd
from io import StringIO

df = None
if pasted.strip():
    try:
        df = pd.read_csv(StringIO(pasted.strip()), sep="\t", header=None,
                         names=["Goods Code", "Origin/Destination", "Date"])
        df["Goods Code"] = df["Goods Code"].astype(str).str.strip()
        df["Origin/Destination"] = df["Origin/Destination"].astype(str).str.strip()
        df["Date"] = df["Date"].astype(str).str.strip()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Yapıştırma hatası: {e}")

st.divider()

goods_code = st.text_input("📦 Goods Code (max 10 hane)", max_chars=10, placeholder="örn: 0101210000")
country_label = st.selectbox("🌍 Origin / Destination", options=list(COUNTRIES.keys()))
country_code = COUNTRIES[country_label]
sim_date = st.date_input("📅 Date", value=date.today())

# TARIC formatı: DD-MM-YYYY
sim_date_str = sim_date.strftime("%d-%m-%Y")

st.link_button("🌐 Siteyi Aç", URL)
search_btn = st.button("🔍 Ara", disabled=not goods_code)

if search_btn and goods_code:
    with st.spinner("Aranıyor..."):
        try:
            screenshot = search_taric(goods_code, country_code, sim_date_str)
            st.success("✅ Tamamlandı!")
            st.image(screenshot, caption=f"{goods_code} / {country_label} / {sim_date_str}", use_container_width=True)
            with open(screenshot, "rb") as f:
                st.download_button("📥 İndir", f, "taric_result.png", "image/png")
        except Exception as e:
            st.error(f"❌ Hata: {e}")
            st.code(str(e))
