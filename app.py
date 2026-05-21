import streamlit as st
import pandas as pd
import json
from io import StringIO, BytesIO
from datetime import datetime
from urllib.parse import urlencode
from pypdf import PdfWriter, PdfReader

BASE_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp"

st.set_page_config(page_title="TARIC", page_icon="🇪🇺")
st.title("🇪🇺 TARIC Consultation")

@st.cache_resource
def load_ulkeler():
    with open("ulkeler.json", "r", encoding="utf-8") as f:
        return json.load(f)

ulkeler = load_ulkeler()

def ulke_kodu(ulke_adi: str) -> str:
    key = ulke_adi.strip().upper()
    return ulkeler.get(key, ulke_adi.strip())

def parse_date(date_str: str) -> str:
    for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return date_str.strip()

def build_url(goods_code: str, country_code: str, date_str: str) -> str:
    params = {
        "Lang": "en",
        "Taric": goods_code.strip(),
        "SimDate": parse_date(date_str),
        "action": "retrieve",
    }
    if country_code and country_code.strip() not in ("", "----------"):
        params["Area"] = country_code.strip()
    return BASE_URL + "?" + urlencode(params)

def link_button(label: str, url: str, key: str):
    btn_id = f"btn_{key}"
    st.components.v1.html(f"""
    <style>
      #{btn_id} {{
        display: inline-block;
        padding: 8px 18px;
        background-color: #FF4B4B;
        color: white !important;
        font-size: 15px;
        font-weight: 600;
        border-radius: 6px;
        text-decoration: none;
        font-family: sans-serif;
        cursor: pointer;
      }}
      #{btn_id}:hover {{ background-color: #cc3333; }}
    </style>
    <a id="{btn_id}" href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>
    """, height=50)

# Session state
for k, v in [("current_index", 0), ("running", False), ("df", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sekmeler ──────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔍 TARIC Sorgula", "📎 PDF Birleştir"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TARIC SORGULA
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
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

    if st.session_state.running and df is not None:
        i = st.session_state.current_index
        row = df.iloc[i]
        goods   = row["Goods Code"]
        country = row["Origin/Destination"]
        tarih   = row["Date"]

        st.info(f"**Sıradaki sorgu [{i+1}/{len(df)}]:** `{goods}` / `{country}` / `{tarih}`")

        url = build_url(goods, country, tarih)

        # PDF alma talimatı
        with st.expander("📄 PDF nasıl alınır?", expanded=False):
            st.markdown("""
1. **Sorgula** butonuna bas → TARIC sayfası yeni sekmede açılır
2. Tarayıcıda **Ctrl+P** (Yazdır) → **PDF olarak kaydet**
3. Daha fazla ayar → **Ölçek: %65** → **Kaydet**
4. PDF'i **"PDF Birleştir"** sekmesine yükle
""")

        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            link_button(f"🔍 Sorgula ({goods})", url, key=f"link_{i}")
        with col2:
            if st.button("⏭ Sonraki", key=f"next_{i}"):
                if i + 1 < len(df):
                    st.session_state.current_index += 1
                else:
                    st.session_state.running = False
                st.rerun()
        with col3:
            if st.button("⏹ Durdur", key="durdur"):
                st.session_state.running = False
                st.warning("Durduruldu.")
                st.rerun()

        st.caption(f"🔗 `{url}`")

    if not st.session_state.running and df is not None and st.session_state.current_index >= len(df):
        st.success("🎉 Tüm sorgular tamamlandı! PDF'leri birleştirmek için 'PDF Birleştir' sekmesine geç.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PDF BİRLEŞTİR
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📎 PDF Birleştir")
    st.caption("TARIC sayfalarından %65 ölçekle aldığınız PDF'leri yükleyin, sıralayın ve birleştirin.")

    uploaded = st.file_uploader(
        "PDF dosyalarını seçin (birden fazla seçebilirsiniz)",
        type="pdf",
        accept_multiple_files=True,
        key="pdf_uploader"
    )

    if uploaded:
        st.markdown(f"**{len(uploaded)} dosya yüklendi:**")

        # Sıralama: dosya adlarını göster, kullanıcı sırayı görebilsin
        names = [f.name for f in uploaded]
        for idx, name in enumerate(names, 1):
            st.write(f"{idx}. {name}")

        st.divider()

        if st.button("🔗 Birleştir ve İndir", type="primary"):
            writer = PdfWriter()
            hata = False
            for f in uploaded:
                try:
                    reader = PdfReader(BytesIO(f.read()))
                    for page in reader.pages:
                        writer.add_page(page)
                except Exception as e:
                    st.error(f"❌ {f.name} okunamadı: {e}")
                    hata = True
                    break

            if not hata:
                out = BytesIO()
                writer.write(out)
                out.seek(0)
                st.success(f"✅ {len(uploaded)} PDF başarıyla birleştirildi.")
                st.download_button(
                    label="⬇️ Birleştirilmiş PDF'i İndir",
                    data=out,
                    file_name="TARIC_birlesik.pdf",
                    mime="application/pdf",
                    type="primary"
                )
    else:
        st.info("Henüz PDF yüklenmedi. TARIC sayfalarından Ctrl+P → %65 ölçek → PDF kaydet, sonra buraya yükleyin.")
