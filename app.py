import streamlit as st
import pandas as pd
import json
from io import StringIO
from datetime import datetime
from urllib.parse import urlencode

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
    """Streamlit'e bağımlı olmayan, yeni sekmede açılan tıklanabilir buton."""
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
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "running" not in st.session_state:
    st.session_state.running = False
if "df" not in st.session_state:
    st.session_state.df = None

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

if st.session_state.running and df is not None:
    i = st.session_state.current_index
    row = df.iloc[i]
    goods   = row["Goods Code"]
    country = row["Origin/Destination"]
    tarih   = row["Date"]

    st.info(f"**Sıradaki sorgu [{i+1}/{len(df)}]:** `{goods}` / `{country}` / `{tarih}`")

    url = build_url(goods, country, tarih)

    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        # Doğrudan <a> linki — Streamlit'e gerek yok, tıklayınca anında açılır
        link_button(f"🔍 Sorgula ({goods})", url, key=f"link_{i}")

    with col2:
        # Sonraki satıra geç (opsiyonel, link açıldıktan sonra basılır)
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

    st.caption(f"🔗 URL: `{url}`")

if not st.session_state.running and df is not None and st.session_state.current_index >= len(df):
    st.success("🎉 Tüm sorgular tamamlandı!")
