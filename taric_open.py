"""
TARIC Consultation Sayfasını Açan Python Scripti
Gereksinim: pip install playwright && playwright install chromium
"""

from playwright.sync_api import sync_playwright
import time

URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en"

def open_taric():
    with sync_playwright() as p:
        # Tarayıcıyı başlat (headless=False → görünür pencere)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"[→] Açılıyor: {URL}")
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

        # Sayfanın tam yüklenmesini bekle
        try:
            page.wait_for_load_state("networkidle", timeout=30_000)
        except Exception:
            pass  # Zaman aşımı olursa devam et

        title = page.title()
        print(f"[✓] Sayfa başlığı: {title}")

        # Ekran görüntüsü al
        screenshot_path = "taric_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"[✓] Ekran görüntüsü kaydedildi: {screenshot_path}")

        # İnsan gibi 5 saniye bekle, sonra kapat
        print("[i] 5 saniye bekleniyor...")
        time.sleep(5)

        browser.close()
        print("[✓] Tarayıcı kapatıldı.")


if __name__ == "__main__":
    open_taric()
