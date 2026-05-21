import streamlit as st
import pandas as pd
import json
from io import StringIO
from datetime import datetime
from urllib.parse import urlencode

BASE_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp"

st.set_page_config(page_title="TARIC", page_icon="🇪🇺")
st.title("🇪🇺 TARIC Consultation")

st.markdown("""
<style>
  div.stButton > button[kind="primary"] {
    background-color: #21c45d !important;
    border-color: #21c45d !important;
    color: white !important;
  }
  div.stButton > button[kind="primary"]:hover {
    background-color: #16a34a !important;
    border-color: #16a34a !important;
  }
</style>
""", unsafe_allow_html=True)

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
        background-color: #21c45d;
        color: white !important;
        font-size: 15px;
        font-weight: 600;
        border-radius: 6px;
        text-decoration: none;
        font-family: sans-serif;
        cursor: pointer;
      }}
      #{btn_id}:hover {{ background-color: #16a34a; }}
    </style>
    <a id="{btn_id}" href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>
    """, height=50)

# Session state
for k, v in [("current_index", 0), ("running", False), ("df", None), ("last_pasted", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

st.subheader("📋 Excel'den Yapıştır")
st.caption("Goods Code, Origin/Destination, Date sütunlarını Excel'den kopyalayıp yapıştırın")
pasted = st.text_area(
    "Buraya yapıştırın",
    height=120,
    placeholder="0101210000\tTR\t1.01.2024\n0202100000\tDE\t1.01.2024"
)

# Sadece içerik değiştiğinde parse et — her rerun'da index sıfırlanmasın
if pasted.strip() and pasted.strip() != st.session_state.last_pasted:
    try:
        df_new = pd.read_csv(
            StringIO(pasted.strip()), sep="\t", header=None,
            names=["Goods Code", "Origin/Destination", "Date"]
        )
        df_new["Goods Code"] = (
            df_new["Goods Code"].astype(str).str.strip()
            .str.replace(".", "", regex=False).str[:10]
        )
        df_new["Origin/Destination"] = df_new["Origin/Destination"].astype(str).apply(ulke_kodu)
        df_new["Date"] = df_new["Date"].astype(str).str.strip()
        df_new.insert(0, "Veri No", range(1, len(df_new) + 1))
        st.session_state.df = df_new
        st.session_state.current_index = 0
        st.session_state.running = True
        st.session_state.last_pasted = pasted.strip()
    except Exception as e:
        st.error(f"Yapıştırma hatası: {e}")

if st.session_state.df is not None:
    st.dataframe(st.session_state.df, use_container_width=True, hide_index=True)

df = st.session_state.df

if st.session_state.running and df is not None:
    i = st.session_state.current_index
    total = len(df)
    row = df.iloc[i]
    goods   = row["Goods Code"]
    country = row["Origin/Destination"]
    tarih   = row["Date"]

    st.divider()

    # Progress bar
    st.progress((i + 1) / total, text=f"Veri No: {i + 1} / {total}")

    url = build_url(goods, country, tarih)

    # Sorgu butonu
    link_button(f"🔍 Sorgula ({i + 1}. Veri)", url, key=f"link_{i}")

    st.caption(f"🔗 `{url}`")

    st.divider()

    # ← Önceki / Sonraki → ok navigasyon
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        prev_disabled = (i == 0)
        if st.button("◀ Önceki", key=f"prev_{i}", disabled=prev_disabled, use_container_width=True):
            st.session_state.current_index -= 1
            st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align:center; padding-top:6px; font-size:14px; color:gray;'>"
            f"{i + 1} / {total}</div>",
            unsafe_allow_html=True
        )

    with col_next:
        if i + 1 < total:
            if st.button("Sonraki ▶", key=f"next_{i}", use_container_width=True, type="primary"):
                st.session_state.current_index += 1
                st.rerun()
        else:
            if st.button("✅ Bitir", key="bitir", use_container_width=True, type="primary"):
                st.session_state.running = False
                st.rerun()

    # Durdur
    if st.button("⏹ Durdur", key="durdur"):
        st.session_state.running = False
        st.warning("Durduruldu.")
        st.rerun()

if not st.session_state.running and df is not None and st.session_state.current_index >= len(df):
    st.success("🎉 Tüm sorgular tamamlandı!")
