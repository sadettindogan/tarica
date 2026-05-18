"""
TARIC Consultation - Streamlit App
"""

import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import os

URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en"

st.set_page_config(
    page_title="TARIC Consultation",
    page_icon="🇪🇺",
    layout="wide"
)

st.title("🇪🇺 TARIC Consultation")
st.caption("EU Tariff & Trade Information System")


def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Streamlit Cloud: chromium sistem üzerinde kurulu olur
    # Lokal geliştirme için webdriver-manager kullan
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    except Exception:
        # Streamlit Cloud / Linux ortamı
        options.binary_location = "/usr/bin/chromium-browser"
        driver = webdriver.Chrome(
            service=Service("/usr/bin/chromedriver"),
            options=options
        )

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


def fetch_taric(wait_seconds: int = 5):
    driver = get_driver()
    try:
        driver.get(URL)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(wait_seconds)  # JS render için bekle

        screenshot_path = "/tmp/taric_screenshot.png"
        driver.save_screenshot(screenshot_path)
        title = driver.title
        current_url = driver.current_url
    finally:
        driver.quit()

    return screenshot_path, title, current_url


# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    wait_sec = st.slider("Sayfa yükleme bekleme süresi (sn)", 3, 15, 5)
    run_btn = st.button("🚀 Sayfayı Aç", use_container_width=True)

st.info(f"**Hedef URL:** {URL}")

if run_btn:
    with st.spinner("TARIC sayfası yükleniyor, lütfen bekleyin..."):
        try:
            screenshot_path, title, current_url = fetch_taric(wait_sec)

            col1, col2 = st.columns(2)
            col1.metric("Sayfa Başlığı", title or "—")
            col2.metric("Son URL", current_url[:60] + "..." if len(current_url) > 60 else current_url)

            st.success("✅ Sayfa başarıyla yüklendi!")
            st.image(screenshot_path, caption="TARIC Sayfası Ekran Görüntüsü", use_container_width=True)

            with open(screenshot_path, "rb") as f:
                st.download_button(
                    label="📥 Ekran Görüntüsünü İndir",
                    data=f,
                    file_name="taric_screenshot.png",
                    mime="image/png"
                )

        except Exception as e:
            st.error(f"❌ Hata oluştu: {e}")
            st.info("Chrome/Chromium kurulu değilse `packages.txt` dosyasını kontrol edin.")
else:
    st.markdown("""
    Sol panelden **🚀 Sayfayı Aç** butonuna tıklayarak TARIC sayfasının
    ekran görüntüsünü alabilirsiniz.
    
    > **Not:** Selenium headless modda çalışır; tarayıcı penceresi açılmaz.
    """)
