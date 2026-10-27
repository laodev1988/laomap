import os
import sys
import glob
import gc
import io
import re
import time
import base64
import shutil
import zipfile
import math
import datetime
import threading
import tempfile
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.sax.saxutils import escape

# ==============================================================================
# 0. ຕັ້ງຄ່າເປີດພະລັງງານ MAX PERFORMANCE & ຄວບຄຸມແຮມບໍ່ໃຫ້ກາຍ 15 GB
# ==============================================================================
MAX_RAM_LIMIT_GB = 15.0
CPU_CORES = max(1, os.cpu_count() or 4)
FAST_THREADS = min(16, CPU_CORES)
os.environ["OMP_NUM_THREADS"] = str(FAST_THREADS)
os.environ["MKL_NUM_THREADS"] = str(FAST_THREADS)
os.environ["OPENBLAS_NUM_THREADS"] = str(FAST_THREADS)
os.environ["NUMEXPR_NUM_THREADS"] = str(FAST_THREADS)
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = str(2**50)

ADMIN_LOGO_URL = (
    "https://scontent.fvte1-2.fna.fbcdn.net/v/t39.30808-6/"
    "679045898_1504285534838596_7094396645673461718_n.png?"
    "stp=dst-png&cstp=mx1640x924&ctp=s1640x924&_nc_cat=105&"
    "_nc_map=urlgen_bucketless&ccb=1-7&_nc_sid=cc71e4&"
    "_nc_ohc=KJBHuZ_Th9oQ7kNvwE3S0Zr&"
    "_nc_oc=AdrIqLWuzbi6q__FW0JgkKvG2tb9sWFwOo3n1Z6zm2GAomitfrYurXQyBcN-RIy2Ddh4Ga67ASh0vSjn3s_pfSMS&"
    "_nc_zt=23&_nc_ht=scontent.fvte1-2.fna&_nc_gid=lBdAdc0fR2hdYB7AiDbJog&"
    "_nc_ss=7b2a8&oh=00_AQN7kg_iG4BpsRNvYEHY6NdgY6Ibd5YDnHxpWrkv3s5AKQ&oe=6ADD4396"
)
DEVELOPER_NAME = "Bounthavy Vixien"
DEVELOPER_PHONE = "02099197767"

# ພິກັດຂອບເຂດຊາຍແດນປະເທດລາວ (Laos National Polygon WGS84) ສຳລັບສ້າງຕາໜ່າງ Index ໝົດປະເທດ
LAOS_NATIONAL_BOUNDARY_WGS84 = [
    [101.67, 22.50], [102.15, 22.40], [102.38, 22.12], [102.77, 21.68],
    [103.00, 21.35], [103.22, 20.80], [103.92, 20.66], [104.48, 20.76],
    [104.88, 20.41], [104.63, 19.95], [103.97, 19.34], [104.22, 19.01],
    [105.05, 18.67], [105.45, 18.17], [105.82, 17.85], [106.45, 17.65],
    [106.63, 17.07], [106.56, 16.60], [107.03, 16.17], [107.55, 15.50],
    [107.62, 14.92], [107.54, 14.68], [106.92, 14.40], [106.52, 14.45],
    [106.02, 13.93], [105.21, 14.23], [105.45, 14.95], [105.52, 15.55],
    [105.05, 16.03], [104.75, 16.58], [104.73, 17.42], [104.18, 17.90],
    [103.40, 18.38], [102.63, 17.85], [102.12, 18.06], [101.47, 17.65],
    [101.05, 17.82], [101.20, 18.60], [101.28, 19.45], [100.56, 19.78],
    [100.38, 20.15], [100.09, 20.36], [100.42, 20.82], [100.85, 21.25],
    [101.18, 21.56], [101.60, 22.15], [101.67, 22.50]
]

# ຖານຂໍ້ມູນແຂວງ, ນະຄອນ ແລະ ເມືອງສຳຄັນໃນລາວ ສຳລັບການຄົ້ນຫາໄວທັນໃຈ (Instant Gazetteer)
LAOS_BUILT_IN_PLACES = [
    {"title": "🏛️ ນະຄອນຫຼວງວຽງຈັນ (Vientiane Capital)", "subtitle": "ນະຄອນຫຼວງວຽງຈັນ, ສປປ ລາວ", "lat": 17.9757, "lon": 102.6331, "zoom": 13, "bbox": (102.50, 17.88, 102.75, 18.08)},
    {"title": "🏛️ ແຂວງຈຳປາສັກ - ນະຄອນປາກເຊ (Champasak / Pakse)", "subtitle": "ນະຄອນປາກເຊ, ແຂວງຈຳປາສັກ", "lat": 15.1202, "lon": 105.7986, "zoom": 14, "bbox": (105.72, 15.06, 105.88, 15.18)},
    {"title": "🏙️ ເມືອງຈຳປາສັກ (Champasak District / Wat Phou)", "subtitle": "ເມືອງຈຳປາສັກ, ແຂວງຈຳປາສັກ", "lat": 14.8919, "lon": 105.8783, "zoom": 14, "bbox": (105.80, 14.83, 105.94, 14.95)},
    {"title": "🏛️ ແຂວງສະຫວັນນະເຂດ - ນະຄອນໄກສອນ ພົມວິຫານ (Savannakhet)", "subtitle": "ນະຄອນໄກສອນ ພົມວິຫານ, ແຂວງສະຫວັນນະເຂດ", "lat": 16.5565, "lon": 104.7538, "zoom": 14, "bbox": (104.70, 16.50, 104.82, 16.62)},
    {"title": "🏙️ ເມືອງພີນ (Phin District)", "subtitle": "ເມືອງພີນ, ແຂວງສະຫວັນນະເຂດ", "lat": 16.5414, "lon": 106.0125, "zoom": 14, "bbox": (105.95, 16.48, 106.08, 16.60)},
    {"title": "🏙️ ເມືອງເຊໂປນ (Xepon District)", "subtitle": "ເມືອງເຊໂປນ, ແຂວງສະຫວັນນະເຂດ", "lat": 16.6925, "lon": 106.2119, "zoom": 14, "bbox": (106.15, 16.63, 106.28, 16.75)},
    {"title": "🏙️ ເມືອງສອງຄອນ - ປາກຊ່ອງ (Songkhone / Pakxong)", "subtitle": "ເມືອງສອງຄອນ, ແຂວງສະຫວັນນະເຂດ", "lat": 16.2230, "lon": 105.2500, "zoom": 14, "bbox": (105.18, 16.16, 105.32, 16.28)},
    {"title": "🏙️ ເມືອງຈຳພອນ (Champhone District)", "subtitle": "ເມືອງຈຳພອນ, ແຂວງສະຫວັນນະເຂດ", "lat": 16.3860, "lon": 105.2180, "zoom": 14, "bbox": (105.15, 16.32, 105.28, 16.45)},
    {"title": "🏛️ ແຂວງຫຼວງພະບາງ (Luang Prabang)", "subtitle": "ນະຄອນຫຼວງພະບາງ, ແຂວງຫຼວງພະບາງ", "lat": 19.8856, "lon": 102.1347, "zoom": 14, "bbox": (102.08, 19.84, 102.20, 19.93)},
    {"title": "🏛️ ແຂວງຄຳມ່ວນ - ທ່າແຂກ (Khammouane / Thakhek)", "subtitle": "ເມືອງທ່າແຂກ, ແຂວງຄຳມ່ວນ", "lat": 17.4103, "lon": 104.8307, "zoom": 14, "bbox": (104.78, 17.36, 104.90, 17.46)},
    {"title": "🏛️ ແຂວງບໍລິຄຳໄຊ - ປາກຊັນ (Bolikhamxai / Paksan)", "subtitle": "ເມືອງປາກຊັນ, ແຂວງບໍລິຄຳໄຊ", "lat": 18.3797, "lon": 103.6586, "zoom": 14, "bbox": (103.60, 18.33, 103.72, 18.43)},
    {"title": "🏛️ ແຂວງວຽງຈັນ - ໂພນໂຮງ (Vientiane Province / Phonhong)", "subtitle": "ເມືອງໂພນໂຮງ, ແຂວງວຽງຈັນ", "lat": 18.4953, "lon": 102.4153, "zoom": 14, "bbox": (102.36, 18.44, 102.47, 18.55)},
    {"title": "🏞️ ເມືອງວັງວຽງ (Vang Vieng)", "subtitle": "ເມືອງວັງວຽງ, ແຂວງວຽງຈັນ", "lat": 18.9235, "lon": 102.4478, "zoom": 14, "bbox": (102.40, 18.88, 102.50, 18.97)},
    {"title": "🏛️ ແຂວງຊຽງຂວາງ - ໂພນສະຫວັນ (Xieng Khouang / Phonsavan)", "subtitle": "ເມືອງແປກ (ໂພນສະຫວັນ), ແຂວງຊຽງຂວາງ", "lat": 19.4500, "lon": 103.1833, "zoom": 14, "bbox": (103.12, 19.40, 103.25, 19.50)},
    {"title": "🏛️ ແຂວງໄຊຍະບູລີ (Xayaburi)", "subtitle": "ເມືອງໄຊຍະບູລີ, ແຂວງໄຊຍະບູລີ", "lat": 19.2576, "lon": 101.7103, "zoom": 14, "bbox": (101.66, 19.20, 101.76, 19.31)},
    {"title": "🏛️ ແຂວງອຸດົມໄຊ - ເມືອງໄຊ (Oudomxay / Muang Xay)", "subtitle": "ເມືອງໄຊ, ແຂວງອຸດົມໄຊ", "lat": 20.6922, "lon": 101.9836, "zoom": 14, "bbox": (101.93, 20.64, 102.04, 20.74)},
    {"title": "🏛️ ແຂວງຫຼວງນ້ຳທາ (Luang Namtha)", "subtitle": "ເມືອງຫຼວງນ້ຳທາ, ແຂວງຫຼວງນ້ຳທາ", "lat": 20.9497, "lon": 101.4019, "zoom": 14, "bbox": (101.35, 20.90, 101.45, 21.00)},
    {"title": "🏛️ ແຂວງບໍ່ແກ້ວ - ຫ້ວຍຊາຍ (Bokeo / Houayxay)", "subtitle": "ເມືອງຫ້ວຍຊາຍ, ແຂວງບໍ່ແກ້ວ", "lat": 20.2764, "lon": 100.4131, "zoom": 14, "bbox": (100.36, 20.22, 100.46, 20.32)},
    {"title": "🏛️ ແຂວງຜົ້ງສາລີ (Phongsaly)", "subtitle": "ເມືອງຜົ້ງສາລີ, ແຂວງຜົ້ງສາລີ", "lat": 21.6833, "lon": 102.1058, "zoom": 14, "bbox": (102.05, 21.63, 102.16, 21.73)},
    {"title": "🏛️ ແຂວງຫົວພັນ - ຊຳເໜືອ (Houaphanh / Xam Neua)", "subtitle": "ເມືອງຊຳເໜືອ, ແຂວງຫົວພັນ", "lat": 20.4197, "lon": 104.0439, "zoom": 14, "bbox": (103.99, 20.37, 104.10, 20.47)},
    {"title": "🏛️ ແຂວງສາລະວັນ (Salavan)", "subtitle": "ເມືອງສາລະວັນ, ແຂວງສາລະວັນ", "lat": 15.7167, "lon": 106.4167, "zoom": 14, "bbox": (106.36, 15.66, 106.47, 15.77)},
    {"title": "🏛️ ແຂວງເຊກອງ (Sekong / Lamam)", "subtitle": "ເມືອງລະມາມ, ແຂວງເຊກອງ", "lat": 15.3444, "lon": 106.7219, "zoom": 14, "bbox": (106.67, 15.29, 106.78, 15.40)},
    {"title": "🏛️ ແຂວງອັດຕະປື - ສາມັກຄີໄຊ (Attapeu / Samakkhixay)", "subtitle": "ເມືອງສາມັກຄີໄຊ, ແຂວງອັດຕະປື", "lat": 14.8106, "lon": 106.8317, "zoom": 14, "bbox": (106.78, 14.76, 106.89, 14.86)},
    {"title": "🏛️ ແຂວງໄຊສົມບູນ - ອະນຸວົງ (Xaisomboun / Anouvong)", "subtitle": "ເມືອງອະນຸວົງ, ແຂວງໄຊສົມບູນ", "lat": 18.9189, "lon": 103.0908, "zoom": 14, "bbox": (103.04, 18.87, 103.14, 18.97)},
]


def _bootstrap_single_file():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        in_streamlit = get_script_run_ctx() is not None
    except Exception:
        in_streamlit = False

    if not in_streamlit:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        st_dir = os.path.join(script_dir, ".streamlit")
        os.makedirs(st_dir, exist_ok=True)
        cfg_path = os.path.join(st_dir, "config.toml")
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write(
                    '[theme]\nbase="light"\nprimaryColor="#0284c7"\n'
                    'backgroundColor="#f8fafc"\nsecondaryBackgroundColor="#ffffff"\n'
                    'textColor="#0f172a"\n\n'
                    '[server]\nmaxUploadSize=8192\nmaxMessageSize=8192\n'
                )
        except Exception:
            pass
        sys.exit(subprocess.call([
            sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__),
            "--server.maxMessageSize=8192", "--server.maxUploadSize=8192"
        ]))


_bootstrap_single_file()

import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import folium
from folium.plugins import Draw, Fullscreen, MousePosition, MeasureControl, MiniMap
from streamlit_folium import st_folium
import shapefile  # pyshp

Image.MAX_IMAGE_PIXELS = None

try:
    cv2.setNumThreads(FAST_THREADS)
    cv2.ocl.setUseOpenCL(True)
except Exception:
    pass

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import rasterio
    from rasterio.windows import Window
    from rasterio.transform import from_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from pyproj import Transformer
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False


# ==============================================================================
# 1. ລະບົບຄວບຄຸມແຮມ (RAM GUARD), ໂຫຼດໂລໂກ້ແອັດມິນ & MODERN CYBER-GIS UI CSS
# ==============================================================================
def get_process_ram_gb():
    if HAS_PSUTIL:
        try:
            return round(psutil.Process(os.getpid()).memory_info().rss / (1024**3), 2)
        except Exception:
            pass
    return 0.35


def enforce_ram_guard(force_clean=False):
    cur_gb = get_process_ram_gb()
    if force_clean or cur_gb >= (MAX_RAM_LIMIT_GB - 1.0):
        st.cache_data.clear()
        gc.collect()
        cur_gb = get_process_ram_gb()
    return cur_gb


@st.cache_data(show_spinner=False, ttl=86400)
def get_admin_logo_css_src(logo_url):
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_admin_banner_logo.png")
    try:
        resp = requests.get(logo_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(cache_path, "wb") as f:
                f.write(resp.content)
            b64_str = base64.b64encode(resp.content).decode("ascii")
            return f"data:image/png;base64,{b64_str}"
    except Exception:
        pass

    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("ascii")
            return f"data:image/png;base64,{b64_str}"
        except Exception:
            pass
    return logo_url


st.set_page_config(
    page_title=f"GeoMap Ultra v36.1 — ພັດທະນາໂດຍ {DEVELOPER_NAME}",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

banner_bg_src = get_admin_logo_css_src(ADMIN_LOGO_URL)

st.markdown(f"""
    <style>
    .block-container {{
        padding-top: 2.2rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 98% !important;
    }}
    .hero-banner {{
        position: relative;
        background-image:
            linear-gradient(90deg, rgba(8, 15, 30, 0.88) 0%, rgba(12, 32, 58, 0.72) 50%, rgba(7, 22, 44, 0.86) 100%),
            url("{banner_bg_src}");
        background-size: cover;
        background-position: center center;
        background-repeat: no-repeat;
        padding: 18px 24px;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 14px;
        box-shadow: 0 10px 26px rgba(2, 132, 199, 0.28);
        border: 1.5px solid rgba(56, 189, 248, 0.55);
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        overflow: hidden;
    }}
    .hero-left {{
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1 1 560px;
    }}
    .hero-logo-thumb {{
        width: 74px;
        height: 74px;
        border-radius: 14px;
        object-fit: cover;
        border: 2px solid #38bdf8;
        box-shadow: 0 4px 14px rgba(56, 189, 248, 0.45);
        background-color: #0f172a;
        flex-shrink: 0;
    }}
    .hero-title {{
        margin: 0;
        font-size: 20.5px;
        font-weight: 800;
        color: #38bdf8;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.75);
        letter-spacing: 0.2px;
    }}
    .hero-sub {{
        margin: 5px 0 0 0;
        color: #f0f9ff;
        font-size: 13.3px;
        text-shadow: 0 1px 6px rgba(0, 0, 0, 0.85);
        line-height: 1.45;
    }}
    .dev-credit-badge {{
        background: rgba(15, 23, 42, 0.82);
        backdrop-filter: blur(8px);
        border: 1.5px solid #38bdf8;
        border-radius: 12px;
        padding: 8px 15px;
        text-align: right;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.45);
        flex-shrink: 0;
    }}
    .dev-name {{
        color: #facc15;
        font-size: 14px;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.3px;
    }}
    .dev-phone {{
        color: #e0f2fe;
        font-size: 13px;
        font-weight: 700;
        margin: 2px 0 0 0;
    }}
    .spec-card {{
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        border: 1.5px solid #7dd3fc;
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 6px;
        margin-bottom: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.04);
    }}
    .index-grid-box {{
        background: linear-gradient(135deg, #fefce8 0%, #f0fdf4 100%);
        border: 2px solid #0d9488;
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }}
    .metric-pill {{
        display: inline-block;
        background: #0f172a;
        color: #38bdf8;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12.5px;
        font-weight: 700;
        margin-right: 6px;
    }}
    .dl-monitor-card {{
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 2px solid #38bdf8;
        border-radius: 14px;
        padding: 16px 18px;
        color: #f8fafc;
        margin-top: 10px;
        margin-bottom: 14px;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.35);
    }}
    .gmap-search-box {{
        background: linear-gradient(135deg, #f8fafc 0%, #e0f2fe 100%);
        border: 1.5px solid #38bdf8;
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 10px;
    }}
    div.stButton > button {{
        font-weight: 700 !important;
        border-radius: 10px !important;
        padding: 0.48rem 0.7rem !important;
        font-size: 13.2px !important;
        transition: all 0.18s ease-in-out !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
    }}
    div.stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25) !important;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div class="hero-banner">
        <div class="hero-left">
            <img src="{banner_bg_src}" class="hero-logo-thumb" alt="Admin Logo" />
            <div>
                <div class="hero-title">🛰️ GeoMap Ultra v36.1 — ດາວໂຫຼດພາບດາວທຽມບໍ່ຈຳກັດຂະໜາດ (.ECW / .TIF) + ຕາໜ່າງ Index ໝົດປະເທດ & ເສັ້ນ Contour ໂຄ້ງມົນ</div>
                <div class="hero-sub">
                    🌍 ລວມລິ້ງພາບຖ່າຍດາວທຽມຟຣີ 26+ ແຫຼ່ງ • ຄົ້ນຫາບ້ານ/ເມືອງ/ແຂວງອັດສະລິຍະຄ້າຍ Google Maps • ສ້າງຕາໜ່າງ Index ໝົດປະເທດລາວ • ເສັ້ນລະດັບຄວາມສູງ Contour ໂຄ້ງມົນງາມໆ!
                </div>
            </div>
        </div>
        <div class="dev-credit-badge">
            <div class="dev-name">👨‍💻 ຜູ້ພັດທະນາ: {DEVELOPER_NAME}</div>
            <div class="dev-phone">📞 ເບີໂທ: {DEVELOPER_PHONE}</div>
        </div>
    </div>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. ຄັງລິ້ງພາບຖ່າຍດາວທຽມຟຣີ & ແຜນທີ່ GIS ທັງໝົດ 26+ ແຫຼ່ງ (FREE SATELLITE & GIS CATALOG)
# ==============================================================================
SATELLITE_CATEGORIES = {
    "🌟 1. ພາບຖ່າຍດາວທຽມຄວາມລະອຽດສູງສຸດ (Ultra-HD Optical Basemaps)": [
        "🛰️ Google Satellite Ultra-HD (ພາບດາວທຽມ Google 2x High-DPI ແຈ້ງສຸດຂີດ Zoom 22)",
        "🗺️ Google Hybrid Ultra-HD (ພາບດາວທຽມ Google + ຊື່ບ້ານ/ເສັ້ນທາງ/ຂອບເຂດ Zoom 22)",
        "🌍 Esri World Imagery Clarity (ພາບດາວທຽມ ArcGIS ໂໝດຄົມຊັດພິເສດ Clarity Beta Zoom 21)",
        "🌎 Esri World Imagery Standard (ພາບດາວທຽມມາດຕະຖານ Maxar/WorldView Zoom 21)",
        "✈️ Microsoft Bing VirtualEarth Aerial (ພາບດາວທຽມ Bing ຄວາມລະອຽດສູງ Zoom 21)",
        "🧭 Microsoft Bing Aerial Hybrid (ພາບດາວທຽມ Bing + ຊື່ສະຖານທີ່/ຖະໜົນ Zoom 21)",
        "🛰️ Yandex Satellite Imagery (ພາບດາວທຽມທາງເລືອກ Yandex Maps Zoom 19)",
        "🔥 Esri World Imagery Firefly (ພາບດາວທຽມໂທນມືດສຳລັບວາງຊ້ອນຂໍ້ມູນ GIS Zoom 20)"
    ],
    "📅 2. ພາບຖ່າຍດາວທຽມເລືອກວັນທີ/ເດືອນ/ປີ & ດັດຊະນີພືດພັນ/ແຫຼ່ງນ້ຳ (Time-Series & Multispectral)": [
        "📅 [ເລືອກປີ 2014-2026] Esri World Imagery Wayback (ພາບດາວທຽມຍ້ອນຫຼັງ 0.3m-0.5m)",
        "📅 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 L2A True Color (10m - ພາບສີຈິງ Planetary Computer STAC)",
        "🌿 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 Color Infrared NIR (10m - ພາບອິນຟຣາເຣດເບິ່ງປ່າໄມ້/ພືດ)",
        "🌳 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 NDVI Vegetation Index (10m - ດັດຊະນີຄວາມຂຽວພືດພັນ)",
        "💧 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 NDWI Water Index (10m - ດັດຊະນີແຫຼ່ງນ້ຳ/ຄວາມຊຸ່ມຊື່ນ)",
        "📅 [ເລືອກວັນທີ & % ເມກ] Landsat 8/9 Collection-2 True Color (30m - STAC API)",
        "☀️ [ເລືອກປີ 2018-2023] EOX Sentinel-2 Cloudless (ພາບດາວທຽມໄຮ້ເມກປະຈຳປີ 10m)",
        "📅 [ເລືອກວັນທີລາຍວັນ] NASA / USGS GIBS Harmonized Sentinel-2 & VIIRS (YYYY-MM-DD)",
        "📅 [ເລືອກເດືອນ/ປີ] Planet Scope / NICFI Tropical Forest Basemap (4.7m - YYYY-MM)"
    ],
    "🌲 3. ຂໍ້ມູນ GIS ຟຣີ: ການໃຊ້ທີ່ດິນໂລກ, ປ່າໄມ້ & ແຫຼ່ງນ້ຳ (Free Global Landcover & Environment)": [
        "🗺️ ESA WorldCover 10m (2021 v200 - ແຜນທີ່ການໃຊ້ທີ່ດິນ ແລະ ປ່າໄມ້ 10 ແມັດ ຟຣີຈາກ ESA)",
        "🌊 JRC Global Surface Water Occurrence (ແຜນທີ່ປະຫວັດແຫຼ່ງນ້ຳຜິວດິນໂລກ 30m)",
        "🌲 Global Forest Canopy / Tree Cover Density (ແຜນທີ່ຄວາມໜາແໜ້ນປ່າໄມ້)"
    ],
    "⛰️ 4. ຂໍ້ມູນລະດັບຄວາມສູງ DEM, ເງົາພູ 3D & ແຜນທີ່ເສັ້ນລະດັບ Contour (Elevation & Topo Maps)": [
        "⛰️ AWS Terrarium DEM Elevation (ຂໍ້ມູນຄວາມສູງນ້ຳທະເລແທ້ m ASL + Hillshade & ສົ່ງອອກ DEM .TIF)",
        "🏔️ Esri World Hillshade 3D (ພາບເງົາພູມສັນຖານ 3 ມິຕິ ຄວາມລະອຽດສູງສຳລັບຊ້ອນພາບດາວທຽມ)",
        "📐 OpenTopoMap Contour (ແຜນທີ່ເສັ້ນລະດັບຄວາມສູງ Contour & ພູມສັນຖານ)",
        "🏞️ Google Terrain Physical (ແຜນທີ່ພູມສັນຖານ + ເສັ້ນລະດັບຄວາມສູງ Google)",
        "🚴 CyclOSM Topo & Trails (ແຜນທີ່ເສັ້ນລະດັບຄວາມສູງ + ທາງຍ່າງປ່າ/ຫ້ວຍນ້ຳລະອຽດ)",
        "🗺️ OpenStreetMap Standard (ແຜນທີ່ເສັ້ນທາງ, ບ້ານ, ແມ່ນ້ຳ ແລະ ສະຖານທີ່ສຳຄັນ)",
        "🚑 OpenStreetMap Humanitarian HOT (ແຜນທີ່ໂຄງສ້າງພື້ນຖານ ແລະ ຊຸມຊົນ)",
        "🌑 CartoDB Dark Matter (ແຜນທີ່ພື້ນຫຼັງໂທນມືດສຳລັບວຽກ GIS)",
        "🔗 Custom XYZ / TMS / WMTS Tile URL (ໃສ່ລິ້ງພາບດາວທຽມ ຫຼື Drone Server ຂອງທ່ານເອງ)"
    ]
}

SATELLITE_PROVIDERS = {
    "🛰️ Google Satellite Ultra-HD (ພາບດາວທຽມ Google 2x High-DPI ແຈ້ງສຸດຂີດ Zoom 22)": {
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&scale=2", "type": "rgb", "max_z": 22
    },
    "🗺️ Google Hybrid Ultra-HD (ພາບດາວທຽມ Google + ຊື່ບ້ານ/ເສັ້ນທາງ/ຂອບເຂດ Zoom 22)": {
        "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}&scale=2", "type": "rgb", "max_z": 22
    },
    "🌍 Esri World Imagery Clarity (ພາບດາວທຽມ ArcGIS ໂໝດຄົມຊັດພິເສດ Clarity Beta Zoom 21)": {
        "url": "https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "type": "rgb", "max_z": 21
    },
    "🌎 Esri World Imagery Standard (ພາບດາວທຽມມາດຕະຖານ Maxar/WorldView Zoom 21)": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "type": "rgb", "max_z": 21
    },
    "✈️ Microsoft Bing VirtualEarth Aerial (ພາບດາວທຽມ Bing ຄວາມລະອຽດສູງ Zoom 21)": {
        "url": "https://ecn.t1.tiles.virtualearth.net/tiles/a{quadkey}.jpeg?g=14000", "type": "quadkey", "max_z": 21
    },
    "🧭 Microsoft Bing Aerial Hybrid (ພາບດາວທຽມ Bing + ຊື່ສະຖານທີ່/ຖະໜົນ Zoom 21)": {
        "url": "https://ecn.t1.tiles.virtualearth.net/tiles/h{quadkey}.jpeg?g=14000", "type": "quadkey", "max_z": 21
    },
    "🛰️ Yandex Satellite Imagery (ພາບດາວທຽມທາງເລືອກ Yandex Maps Zoom 19)": {
        "url": "https://sat01.maps.yandex.net/tiles?l=sat&x={x}&y={y}&z={z}", "type": "rgb", "max_z": 19
    },
    "🔥 Esri World Imagery Firefly (ພາບດາວທຽມໂທນມືດສຳລັບວາງຊ້ອນຂໍ້ມູນ GIS Zoom 20)": {
        "url": "https://fly.maptiles.arcgis.com/arcgis/rest/services/World_Imagery_Firefly/MapServer/tile/{z}/{y}/{x}", "type": "rgb", "max_z": 20
    },
    "📅 [ເລືອກປີ 2014-2026] Esri World Imagery Wayback (ພາບດາວທຽມຍ້ອນຫຼັງ 0.3m-0.5m)": {
        "url": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{release_id}/{z}/{y}/{x}", "type": "esri_wayback", "max_z": 20
    },
    "📅 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 L2A True Color (10m - ພາບສີຈິງ Planetary Computer STAC)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "stac_s2_true", "max_z": 18
    },
    "🌿 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 Color Infrared NIR (10m - ພາບອິນຟຣາເຣດເບິ່ງປ່າໄມ້/ພືດ)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "stac_s2_nir", "max_z": 18
    },
    "🌳 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 NDVI Vegetation Index (10m - ດັດຊະນີຄວາມຂຽວພືດພັນ)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "stac_s2_ndvi", "max_z": 18
    },
    "💧 [ເລືອກວັນທີ & % ເມກ] Sentinel-2 NDWI Water Index (10m - ດັດຊະນີແຫຼ່ງນ້ຳ/ຄວາມຊຸ່ມຊື່ນ)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "stac_s2_ndwi", "max_z": 18
    },
    "📅 [ເລືອກວັນທີ & % ເມກ] Landsat 8/9 Collection-2 True Color (30m - STAC API)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "stac_landsat", "max_z": 17
    },
    "☀️ [ເລືອກປີ 2018-2023] EOX Sentinel-2 Cloudless (ພາບດາວທຽມໄຮ້ເມກປະຈຳປີ 10m)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "eox_yearly", "max_z": 18
    },
    "📅 [ເລືອກວັນທີລາຍວັນ] NASA / USGS GIBS Harmonized Sentinel-2 & VIIRS (YYYY-MM-DD)": {
        "url": "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/HLS_S30_Nadir_BRDF_Adjusted_Reflectance/default/{date}/GoogleMapsCompatible_Level12/{z}/{y}/{x}.png", "type": "nasa_gibs_date", "max_z": 16
    },
    "📅 [ເລືອກເດືອນ/ປີ] Planet Scope / NICFI Tropical Forest Basemap (4.7m - YYYY-MM)": {
        "url": "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg", "type": "planet_monthly", "max_z": 18
    },
    "🗺️ ESA WorldCover 10m (2021 v200 - ແຜນທີ່ການໃຊ້ທີ່ດິນ ແລະ ປ່າໄມ້ 10 ແມັດ ຟຣີຈາກ ESA)": {
        "url": "https://services.terrascope.be/wmts/v2/wmts?service=WMTS&request=GetTile&version=1.0.0&layer=WORLDCOVER_2021_MAP&style=default&tilematrixset=GoogleMapsCompatible&TileMatrix=EPSG:3857:{z}&TileRow={y}&TileCol={x}&format=image/png", "type": "rgb", "max_z": 18
    },
    "🌊 JRC Global Surface Water Occurrence (ແຜນທີ່ປະຫວັດແຫຼ່ງນ້ຳຜິວດິນໂລກ 30m)": {
        "url": "https://storage.googleapis.com/global-surface-water/tiles2021/occurrence/{z}/{x}/{y}.png", "type": "rgb", "max_z": 16
    },
    "🌲 Global Forest Canopy / Tree Cover Density (ແຜນທີ່ຄວາມໜາແໜ້ນປ່າໄມ້)": {
        "url": "https://tiles.globalforestwatch.org/umd_tree_cover_density_2010/v1.8/tcd_30/{z}/{x}/{y}.png", "type": "rgb", "max_z": 16
    },
    "⛰️ AWS Terrarium DEM Elevation (ຂໍ້ມູນຄວາມສູງນ້ຳທະເລແທ້ m ASL + Hillshade & ສົ່ງອອກ DEM .TIF)": {
        "url": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png", "type": "dem_terrarium", "max_z": 15
    },
    "🏔️ Esri World Hillshade 3D (ພາບເງົາພູມສັນຖານ 3 ມິຕິ ຄວາມລະອຽດສູງສຳລັບຊ້ອນພາບດາວທຽມ)": {
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}", "type": "rgb", "max_z": 19
    },
    "📐 OpenTopoMap Contour (ແຜນທີ່ເສັ້ນລະດັບຄວາມສູງ Contour & ພູມສັນຖານ)": {
        "url": "https://tile.opentopomap.org/{z}/{x}/{y}.png", "type": "rgb", "max_z": 17
    },
    "🏞️ Google Terrain Physical (ແຜນທີ່ພູມສັນຖານ + ເສັ້ນລະດັບຄວາມສູງ Google)": {
        "url": "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}&scale=2", "type": "rgb", "max_z": 20
    },
    "🚴 CyclOSM Topo & Trails (ແຜນທີ່ເສັ້ນລະດັບຄວາມສູງ + ທາງຍ່າງປ່າ/ຫ້ວຍນ້ຳລະອຽດ)": {
        "url": "https://a.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png", "type": "rgb", "max_z": 19
    },
    "🗺️ OpenStreetMap Standard (ແຜນທີ່ເສັ້ນທາງ, ບ້ານ, ແມ່ນ້ຳ ແລະ ສະຖານທີ່ສຳຄັນ)": {
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "type": "rgb", "max_z": 19
    },
    "🚑 OpenStreetMap Humanitarian HOT (ແຜນທີ່ໂຄງສ້າງພື້ນຖານ ແລະ ຊຸມຊົນ)": {
        "url": "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", "type": "rgb", "max_z": 19
    },
    "🌑 CartoDB Dark Matter (ແຜນທີ່ພື້ນຫຼັງໂທນມືດສຳລັບວຽກ GIS)": {
        "url": "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png", "type": "rgb", "max_z": 20
    },
    "🔗 Custom XYZ / TMS / WMTS Tile URL (ໃສ່ລິ້ງພາບດາວທຽມ ຫຼື Drone Server ຂອງທ່ານເອງ)": {
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&scale=2", "type": "custom_xyz", "max_z": 22
    }
}

ESRI_WAYBACK_RELEASES = {
    "2026 / ລ່າສຸດ (Latest High-Res WorldView)": "current",
    "2025 (Release 2025 High-Res)": "60013",
    "2024 (Release 2024 High-Res)": "41468",
    "2023 (Release 2023 High-Res)": "25982",
    "2022 (Release 2022 High-Res)": "43182",
    "2021 (Release 2021 High-Res)": "1049",
    "2020 (Release 2020 High-Res)": "29260",
    "2019 (Release 2019 High-Res)": "6036",
    "2018 (Release 2018 High-Res)": "13161",
    "2016 (Release 2016 High-Res)": "3515",
    "2014 (Release 2014 Archive)": "10"
}

EOX_CLOUDLESS_YEARS = {
    "2023 (Sentinel-2 Cloudless 2023)": "s2cloudless-2023_3857",
    "2022 (Sentinel-2 Cloudless 2022)": "s2cloudless-2022_3857",
    "2021 (Sentinel-2 Cloudless 2021)": "s2cloudless-2021_3857",
    "2020 (Sentinel-2 Cloudless 2020)": "s2cloudless-2020_3857",
    "2019 (Sentinel-2 Cloudless 2019)": "s2cloudless-2019_3857",
    "2018 (Sentinel-2 Cloudless 2018)": "s2cloudless-2018_3857",
}


def init_session_state():
    enforce_ram_guard()
    default_save_dir = "D:/GIS_Downloaded_Maps" if os.path.exists("D:/") else os.path.expanduser("~/Desktop/GIS_Downloaded_Maps")
    defaults = {
        "geo_bounds": (105.6400, 16.7000, 105.6900, 16.7450),
        "map_init_center": [16.7225, 105.6650],
        "map_init_zoom": 15,
        "dl_map_cmd_counter": 0,
        "boundary_features": [],
        "boundary_fields": [],
        "village_name_field": "",
        "selected_village_indices": [],
        "boundary_polygons_wgs84": [],
        "boundary_name": "",
        "index_grid_cells": [],
        "index_grid_size_km": 10,
        "selected_index_sheet_codes": [],
        "show_index_grid_on_map": True,
        "save_folder": default_save_dir,
        "save_filename": "satellite_area_01",
        "save_format": ".tif",
        "stac_scenes": [],
        "user_custom_xyz_url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&scale=2",
        "preview_rgb": None,
        "preview_caption": "",
        "free_gis_zip_bytes": None,
        "free_gis_zip_name": "",
        "gmap_search_results": [],
        "gmap_last_query": "",
        "gmap_selected_pin": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()


# ==============================================================================
# 3. ຟັງຊັນຈັດການພິກັດ UTM ZONE 48N & ລະບົບຄົ້ນຫາອັດສະລິຍະຄ້າຍ GOOGLE MAPS
# ==============================================================================
def lonlat_to_utm48n(lon, lat):
    a, f, k0, lon0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(105.0)
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    lat_rad, lon_rad = math.radians(lat), math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
    T = math.tan(lat_rad) ** 2
    C = ep2 * math.cos(lat_rad) ** 2
    A = math.cos(lat_rad) * (lon_rad - lon0)
    M = a * (
        (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat_rad
        - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * lat_rad)
        + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * lat_rad)
        - (35 * e2 ** 3 / 3072) * math.sin(6 * lat_rad)
    )
    easting = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000.0
    northing = k0 * (M + N * math.tan(lat_rad) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24 + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720))
    return easting, northing


def utm48n_to_lonlat(easting, northing):
    a, f, k0, lon0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(105.0)
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    x, y = easting - 500000.0, northing
    M = y / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    phi1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1) ** 2)
    T1 = math.tan(phi1) ** 2
    C1 = ep2 * math.cos(phi1) ** 2
    R1 = a * (1 - e2) / ((1 - e2 * math.sin(phi1) ** 2) ** 1.5)
    D = x / (N1 * k0)
    lat = phi1 - (N1 * math.tan(phi1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / math.cos(phi1)
    return math.degrees(lon), math.degrees(lat)


def calc_wgs84_ring_area_m2(ring_wgs84):
    if len(ring_wgs84) < 3:
        return 0.0
    utm_pts = np.array([lonlat_to_utm48n(pt[0], pt[1]) for pt in ring_wgs84], dtype=np.float64)
    x, y = utm_pts[:, 0], utm_pts[:, 1]
    return max(0.0, float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))))


def compute_bbox_from_polygons(polys, buffer_pct=0.01):
    all_lons = [pt[0] for ring in polys for pt in ring]
    all_lats = [pt[1] for ring in polys for pt in ring]
    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)
    dlon = max(0.0002, (max_lon - min_lon) * buffer_pct)
    dlat = max(0.0002, (max_lat - min_lat) * buffer_pct)
    return (min_lon - dlon, min_lat - dlat, max_lon + dlon, max_lat + dlat)


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_online_place_suggestions(query_str):
    q = query_str.strip()
    if not q:
        return []

    results = []
    seen_coords = set()

    def _add_candidate(title, subtitle, lat, lon, zoom=16, bbox=None, source_tag="🌍"):
        for s_lat, s_lon in seen_coords:
            if abs(lat - s_lat) < 0.0015 and abs(lon - s_lon) < 0.0015:
                return
        seen_coords.add((lat, lon))
        if not bbox:
            pad = 0.012 if zoom >= 15 else (0.035 if zoom >= 13 else 0.08)
            bbox = (lon - pad, lat - pad, lon + pad, lat + pad)
        results.append({
            "title": title,
            "subtitle": subtitle,
            "lat": float(lat),
            "lon": float(lon),
            "zoom": int(zoom),
            "bbox": tuple(float(x) for x in bbox),
            "source_tag": source_tag
        })

    coord_match = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*$", q)
    if coord_match:
        v1, v2 = float(coord_match.group(1)), float(coord_match.group(2))
        if -90.0 <= v1 <= 90.0 and -180.0 <= v2 <= 180.0:
            _add_candidate(f"📍 ພິກັດ Lat/Lon: {v1:.6f}, {v2:.6f}", "ພິກັດ WGS84 ໂດຍກົງ", v1, v2, zoom=17, source_tag="🎯")
        elif -90.0 <= v2 <= 90.0 and -180.0 <= v1 <= 180.0:
            _add_candidate(f"📍 ພິກັດ Lon/Lat: {v2:.6f}, {v1:.6f}", "ພິກັດ WGS84 ໂດຍກົງ", v2, v1, zoom=17, source_tag="🎯")
        elif 100000.0 <= v1 <= 900000.0 and 1000000.0 <= v2 <= 3000000.0:
            lon_u, lat_u = utm48n_to_lonlat(v1, v2)
            _add_candidate(f"📍 ພິກັດ UTM 48N: E={v1:,.0f}, N={v2:,.0f}", f"Lat: {lat_u:.6f}, Lon: {lon_u:.6f}", lat_u, lon_u, zoom=17, source_tag="🎯")

    q_low = q.lower()
    for item in LAOS_BUILT_IN_PLACES:
        if q_low in item["title"].lower() or q_low in item["subtitle"].lower():
            _add_candidate(item["title"], item["subtitle"], item["lat"], item["lon"], zoom=item["zoom"], bbox=item["bbox"], source_tag="🇱🇦")

    headers = {"User-Agent": "Mozilla/5.0 GeoMapUltra/36.1", "Accept-Language": "lo,th,en"}

    def _query_arcgis():
        out = []
        try:
            r = requests.get(
                "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
                params={
                    "SingleLine": q,
                    "f": "json",
                    "maxLocations": 10,
                    "outFields": "Match_addr,LongLabel,ShortLabel,Addr_type,Type,City,Region,Country",
                    "location": "104.8,17.5",
                    "distance": 800000
                },
                headers=headers,
                timeout=6
            )
            if r.status_code == 200:
                for c in r.json().get("candidates", []):
                    loc = c.get("location", {})
                    if "y" not in loc or "x" not in loc:
                        continue
                    lat_c, lon_c = float(loc["y"]), float(loc["x"])
                    attrs = c.get("attributes", {})
                    short_n = attrs.get("ShortLabel") or c.get("address") or q
                    long_n = attrs.get("LongLabel") or attrs.get("Match_addr") or short_n
                    addr_t = str(attrs.get("Addr_type", "")).lower()
                    ext = c.get("extent")
                    bbox_c = (float(ext["xmin"]), float(ext["ymin"]), float(ext["xmax"]), float(ext["ymax"])) if ext and "xmin" in ext else None
                    z_c = 13 if addr_t in ("administrativearea", "region") else (15 if addr_t in ("locality", "city") else 16)
                    out.append((f"📍 {short_n}", long_n, lat_c, lon_c, z_c, bbox_c, "🗺️"))
        except Exception:
            pass
        return out

    def _query_nominatim():
        out = []
        try:
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "jsonv2", "addressdetails": 1, "limit": 10, "accept-language": "lo,th,en"},
                headers=headers,
                timeout=6
            )
            if r.status_code == 200:
                for hit in r.json():
                    lat_c, lon_c = float(hit["lat"]), float(hit["lon"])
                    disp = hit.get("display_name", q)
                    parts = [p.strip() for p in disp.split(",") if p.strip()]
                    short_n = parts[0] if parts else q
                    sub_n = ", ".join(parts[1:4]) if len(parts) > 1 else disp
                    bb = hit.get("boundingbox")
                    bbox_c = None
                    if bb and len(bb) == 4:
                        s_lat, n_lat, w_lon, e_lon = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
                        if abs(e_lon - w_lon) > 0.001 and abs(n_lat - s_lat) > 0.001:
                            bbox_c = (w_lon, s_lat, e_lon, n_lat)
                    cat_t = str(hit.get("type", "")).lower()
                    z_c = 12 if cat_t in ("state", "province", "administrative") else (15 if cat_t in ("city", "town", "village", "hamlet") else 16)
                    out.append((f"📍 {short_n}", sub_n, lat_c, lon_c, z_c, bbox_c, "🌍"))
        except Exception:
            pass
        return out

    def _query_photon():
        out = []
        try:
            r = requests.get(
                "https://photon.komoot.io/api/",
                params={"q": q, "lat": 17.5, "lon": 104.8, "limit": 8},
                headers=headers,
                timeout=5
            )
            if r.status_code == 200:
                for feat in r.json().get("features", []):
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if len(coords) >= 2:
                        lon_c, lat_c = float(coords[0]), float(coords[1])
                        props = feat.get("properties", {})
                        nm = props.get("name") or q
                        city_st = ", ".join([str(props.get(k)) for k in ("city", "county", "state", "country") if props.get(k)])
                        ext = props.get("extent")
                        bbox_c = (float(ext[0]), float(ext[1]), float(ext[2]), float(ext[3])) if ext and len(ext) == 4 else None
                        out.append((f"📍 {nm}", city_st or nm, lat_c, lon_c, 15, bbox_c, "🧭"))
        except Exception:
            pass
        return out

    with ThreadPoolExecutor(max_workers=3) as ex:
        f_arc = ex.submit(_query_arcgis)
        f_nom = ex.submit(_query_nominatim)
        f_pho = ex.submit(_query_photon)
        for fut in (f_arc, f_nom, f_pho):
            for cand in fut.result():
                _add_candidate(*cand)

    def _sort_priority(item):
        in_laos = (13.8 <= item["lat"] <= 22.6) and (100.0 <= item["lon"] <= 107.8)
        return (0 if item["source_tag"] == "🎯" else (1 if item["source_tag"] == "🇱🇦" else (2 if in_laos else 3)))

    results.sort(key=_sort_priority)
    return results[:15]


def search_all_places_with_local_boundaries(query_str):
    q = query_str.strip()
    if not q:
        return []

    combined = []
    q_low = q.lower()

    feats = st.session_state.get("boundary_features", [])
    v_field = st.session_state.get("village_name_field", "NAME")
    for f in feats:
        attrs = f.get("attrs", {})
        all_vals_str = " | ".join(str(v) for v in attrs.values() if v)
        if q_low in all_vals_str.lower():
            v_name = attrs.get(v_field) or all_vals_str[:40] or f"ຂອບເຂດ #{f['idx']+1}"
            bb = f["bbox"]
            c_lat = (bb[1] + bb[3]) / 2.0
            c_lon = (bb[0] + bb[2]) / 2.0
            combined.append({
                "title": f"🏘️ [ຂອບເຂດທີ່ນຳເຂົ້າ] {v_name}",
                "subtitle": f"ຈາກໄຟລ໌ {st.session_state.get('boundary_name', 'Shapefile/KML')} ({all_vals_str[:60]})",
                "lat": c_lat,
                "lon": c_lon,
                "zoom": 16,
                "bbox": bb,
                "source_tag": "📂",
                "village_idx": f["idx"]
            })

    online_res = fetch_online_place_suggestions(q)
    combined.extend(online_res)
    return combined[:15]


def jump_to_selected_search_place(place_item):
    if not place_item:
        return

    if "village_idx" in place_item:
        update_active_village_selection([place_item["village_idx"]])

    lat_c = float(place_item["lat"])
    lon_c = float(place_item["lon"])
    zoom_c = int(place_item.get("zoom", 16))
    bbox_c = place_item.get("bbox")
    if not bbox_c:
        pad = 0.012 if zoom_c >= 15 else 0.03
        bbox_c = (lon_c - pad, lat_c - pad, lon_c + pad, lat_c + pad)

    st.session_state["map_init_center"] = [lat_c, lon_c]
    st.session_state["map_init_zoom"] = zoom_c
    st.session_state["geo_bounds"] = bbox_c
    st.session_state["gmap_selected_pin"] = {
        "title": place_item["title"],
        "subtitle": place_item["subtitle"],
        "lat": lat_c,
        "lon": lon_c
    }

    clean_name = re.sub(r'[\\/*?:"<>|\s📍🏛️🏙️🏘️🏞️🌍🗺️🧭🇱🇦🎯\[\]]+', "_", place_item["title"]).strip("_")[:35]
    if clean_name:
        st.session_state["save_filename"] = f"sat_{clean_name}"

    st.session_state["dl_map_cmd_counter"] += 1


def pick_folder_native_windows(title_str="ເລືອກໂຟນເດີສຳລັບເກັບໄຟລ໌ພາບດາວທຽມ"):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        folder_path = filedialog.askdirectory(title=title_str)
        root.destroy()
        return folder_path
    except Exception:
        return ""


def pick_file_native_windows(title_str="ເລືອກໄຟລ໌", file_types=None):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        if file_types is None:
            file_types = [("GIS Files", "*.shp *.kml *.zip *.geojson *.tif *.tiff"), ("All Files", "*.*")]
        file_path = filedialog.askopenfilename(title=title_str, filetypes=file_types)
        root.destroy()
        return file_path
    except Exception:
        return ""


# ==============================================================================
# 4. ລະບົບສ້າງຕາໜ່າງ INDEX ແຜນທີ່ອອນໄລ ໝົດປະເທດລາວ (ONLINE NATIONAL MAP INDEX GRID)
# ==============================================================================
@st.cache_data(show_spinner=False)
def generate_utm_index_grid_cells(scope_mode="laos_national", grid_size_km=10.0, custom_rings_wgs84=None, custom_bbox_wgs84=None):
    step_m = int(round(float(grid_size_km) * 1000.0))
    step_m = max(500, step_m)

    if scope_mode == "laos_national":
        target_rings = [LAOS_NATIONAL_BOUNDARY_WGS84]
    elif scope_mode == "custom_boundary" and custom_rings_wgs84:
        target_rings = custom_rings_wgs84
    else:
        bw, bs, be, bn = custom_bbox_wgs84 or (105.6400, 16.7000, 105.6900, 16.7450)
        target_rings = [[[bw, bs], [be, bs], [be, bn], [bw, bn]]]

    utm_rings = []
    min_e, max_e = 1e12, -1e12
    min_n, max_n = 1e12, -1e12

    for r in target_rings:
        u_pts = [lonlat_to_utm48n(pt[0], pt[1]) for pt in r]
        if len(u_pts) >= 3:
            arr = np.array(u_pts, dtype=np.float64)
            min_e = min(min_e, float(np.min(arr[:, 0])))
            max_e = max(max_e, float(np.max(arr[:, 0])))
            min_n = min(min_n, float(np.min(arr[:, 1])))
            max_n = max(max_n, float(np.max(arr[:, 1])))
            utm_rings.append(arr)

    start_e = int(math.floor(min_e / step_m) * step_m)
    end_e = int(math.ceil(max_e / step_m) * step_m)
    start_n = int(math.floor(min_n / step_m) * step_m)
    end_n = int(math.ceil(max_n / step_m) * step_m)

    nx = max(1, (end_e - start_e) // step_m)
    ny = max(1, (end_n - start_n) // step_m)

    if scope_mode == "laos_national" and (nx * ny > 25000):
        step_m = max(step_m, 5000)
        grid_size_km = step_m / 1000.0
        start_e = int(math.floor(min_e / step_m) * step_m)
        end_e = int(math.ceil(max_e / step_m) * step_m)
        start_n = int(math.floor(min_n / step_m) * step_m)
        end_n = int(math.ceil(max_n / step_m) * step_m)
        nx = max(1, (end_e - start_e) // step_m)
        ny = max(1, (end_n - start_n) // step_m)

    sub_res = 4
    mask_w, mask_h = nx * sub_res, ny * sub_res
    poly_mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
    for arr in utm_rings:
        px_pts = np.zeros_like(arr, dtype=np.int32)
        px_pts[:, 0] = np.clip(np.round(((arr[:, 0] - start_e) / float(end_e - start_e)) * mask_w), 0, mask_w - 1).astype(np.int32)
        px_pts[:, 1] = np.clip(np.round(((end_n - arr[:, 1]) / float(end_n - start_n)) * mask_h), 0, mask_h - 1).astype(np.int32)
        cv2.fillPoly(poly_mask, [px_pts.reshape((-1, 1, 2))], 255)

    poly_mask = cv2.dilate(poly_mask, np.ones((3, 3), np.uint8), iterations=1)
    cell_hit_grid = cv2.resize(poly_mask, (nx, ny), interpolation=cv2.INTER_AREA) > 0

    cells = []
    size_tag = f"{int(grid_size_km)}K" if float(grid_size_km).is_integer() else f"{grid_size_km}K"
    seq_id = 1

    for r_idx in range(ny):
        n_top = end_n - r_idx * step_m
        n_bot = n_top - step_m
        row_num = r_idx + 1
        for c_idx in range(nx):
            if not cell_hit_grid[r_idx, c_idx]:
                continue
            e_left = start_e + c_idx * step_m
            e_right = e_left + step_m
            col_num = c_idx + 1

            lon_sw, lat_sw = utm48n_to_lonlat(e_left, n_bot)
            lon_se, lat_se = utm48n_to_lonlat(e_right, n_bot)
            lon_ne, lat_ne = utm48n_to_lonlat(e_right, n_top)
            lon_nw, lat_nw = utm48n_to_lonlat(e_left, n_top)

            sheet_code = f"IDX{size_tag}_R{row_num:03d}_C{col_num:03d}"
            utm_label = f"E{e_left//1000:03d}_N{n_bot//1000:04d}"

            ring_wgs = [
                [round(lon_sw, 6), round(lat_sw, 6)],
                [round(lon_se, 6), round(lat_se, 6)],
                [round(lon_ne, 6), round(lat_ne, 6)],
                [round(lon_nw, 6), round(lat_nw, 6)]
            ]
            ring_utm = [
                [float(e_left), float(n_bot)],
                [float(e_right), float(n_bot)],
                [float(e_right), float(n_top)],
                [float(e_left), float(n_top)]
            ]
            cells.append({
                "id": seq_id,
                "sheet_code": sheet_code,
                "utm_code": utm_label,
                "row": row_num,
                "col": col_num,
                "size_km": float(grid_size_km),
                "area_km2": round((step_m / 1000.0) ** 2, 2),
                "e_min": e_left, "e_max": e_right,
                "n_min": n_bot, "n_max": n_top,
                "ring_wgs84": ring_wgs,
                "ring_utm": ring_utm,
                "center_wgs84": [round((lat_sw + lat_ne) / 2.0, 6), round((lon_sw + lon_ne) / 2.0, 6)],
                "bbox_wgs84": (min(lon_sw, lon_nw), min(lat_sw, lat_se), max(lon_se, lon_ne), max(lat_nw, lat_ne))
            })
            seq_id += 1

    return cells


def export_index_grid_shapefile_zip(cells, coord_sys="UTM48N"):
    prj_wkt = (
        'PROJCS["WGS_1984_UTM_Zone_48N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",105.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
        if coord_sys == "UTM48N" else
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )
    s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYGON)
    w.field("GRID_ID", "N", 10)
    w.field("SHEET_CODE", "C", 30)
    w.field("UTM_GRID", "C", 25)
    w.field("ROW_NUM", "N", 8)
    w.field("COL_NUM", "N", 8)
    w.field("SIZE_KM", "N", 8, 1)
    w.field("AREA_KM2", "N", 10, 2)
    w.field("EAST_MIN", "N", 12, 0)
    w.field("EAST_MAX", "N", 12, 0)
    w.field("NORTH_MIN", "N", 12, 0)
    w.field("NORTH_MAX", "N", 12, 0)

    for c in cells:
        ring = list(c["ring_utm"]) if coord_sys == "UTM48N" else list(c["ring_wgs84"])
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        w.poly([ring])
        w.record(
            c["id"], c["sheet_code"], c["utm_code"], c["row"], c["col"],
            c["size_km"], c["area_km2"], c["e_min"], c["e_max"], c["n_min"], c["n_max"]
        )
    w.close()

    sz_label = f"{int(cells[0]['size_km'])}x{int(cells[0]['size_km'])}km" if cells else "Grid"
    fname_base = f"Laos_Index_Grid_{sz_label}_{coord_sys}"
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{fname_base}.shp", s_io.getvalue())
        zf.writestr(f"{fname_base}.shx", x_io.getvalue())
        zf.writestr(f"{fname_base}.dbf", d_io.getvalue())
        zf.writestr(f"{fname_base}.prj", prj_wkt.encode("utf-8"))
        zf.writestr(f"{fname_base}.cpg", b"UTF-8")
    return zip_buf.getvalue()


def export_index_grid_kml_bytes(cells):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document><name>Laos_Map_Index_Grid</name>',
        '<Style id="idxStyle"><LineStyle><color>ff00d7ff</color><width>2</width></LineStyle><PolyStyle><color>1500d7ff</color><fill>1</fill><outline>1</outline></PolyStyle></Style>'
    ]
    for c in cells:
        r = c["ring_wgs84"]
        c_str = " ".join([f"{lon:.6f},{lat:.6f},0" for lon, lat in r] + [f"{r[0][0]:.6f},{r[0][1]:.6f},0"])
        desc = f"ລະຫັດ: {c['sheet_code']} | UTM: {c['utm_code']} | ຂະໜາດ: {c['size_km']}x{c['size_km']} km ({c['area_km2']} km²)"
        lines.append(
            f'<Placemark><name>{c["sheet_code"]}</name><description>{escape(desc)}</description>'
            f'<styleUrl>#idxStyle</styleUrl>'
            f'<Polygon><outerBoundaryIs><LinearRing><coordinates>{c_str}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>'
        )
    lines.append('</Document></kml>')
    return "\n".join(lines).encode("utf-8")


# ==============================================================================
# 5. ລະບົບຄົ້ນຫາພາບດາວທຽມຕາມວັນທີ (STAC API / GIBS / WAYBACK / EOX)
# ==============================================================================
@st.cache_data(show_spinner=False, ttl=1800)
def search_stac_satellite_scenes_by_date(west, south, east, north, prov_type="stac_s2_true", start_date="2025-01-01", end_date="2026-12-31", max_cloud=30):
    collection_id = "landsat-c2-l2" if prov_type == "stac_landsat" else "sentinel-2-l2a"
    stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
    payload = {
        "collections": [collection_id],
        "bbox": [float(west), float(south), float(east), float(north)],
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": float(max_cloud)}},
        "limit": 30,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }
    scenes = []
    try:
        resp = requests.post(stac_url, json=payload, timeout=12)
        if resp.status_code == 200:
            for feat in resp.json().get("features", []):
                item_id = feat.get("id", "")
                props = feat.get("properties", {})
                dt_str = props.get("datetime", "")[:10]
                cloud_pct = round(float(props.get("eo:cloud_cover", 0.0)), 1)
                platform = props.get("platform", collection_id).upper()

                if prov_type == "stac_s2_true":
                    tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item={item_id}&assets=visual&format=png"
                elif prov_type == "stac_s2_nir":
                    tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item={item_id}&assets=B08&assets=B04&assets=B03&color_formula=gamma+RGB+2.2,saturation+1.4,sigmoidal+RGB+12+0.5&format=png"
                elif prov_type == "stac_s2_ndvi":
                    tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item={item_id}&expression=(B08-B04)/(B08+B04)&rescale=-0.2,0.85&colormap_name=ylgn&format=png"
                elif prov_type == "stac_s2_ndwi":
                    tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item={item_id}&expression=(B03-B08)/(B03+B08)&rescale=-0.5,0.5&colormap_name=rdbu&format=png"
                else:
                    tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=landsat-c2-l2&item={item_id}&assets=red&assets=green&assets=blue&color_formula=gamma+RGB+2.7,saturation+1.5,sigmoidal+RGB+15+0.55&format=png"

                scenes.append({
                    "item_id": item_id, "date": dt_str, "cloud": cloud_pct, "platform": platform,
                    "label": f"📅 ວັນທີ: {dt_str} | ☁️ ເມກ: {cloud_pct}% | 🛰️ {platform} ({item_id[:20]}...)",
                    "tile_url": tile_url
                })
    except Exception:
        pass
    return scenes


def render_provider_date_controls(provider_choice, w_b, s_b, e_b, n_b, key_prefix="main"):
    prov_type = SATELLITE_PROVIDERS[provider_choice]["type"]
    custom_url = ""

    if prov_type in ("stac_s2_true", "stac_s2_nir", "stac_s2_ndvi", "stac_s2_ndwi", "stac_landsat"):
        dc1, dc2, dc3, dc4 = st.columns([1.2, 1.2, 1.2, 1.8])
        with dc1:
            s_dt = st.date_input("ຕັ້ງແຕ່ວັນທີ:", value=datetime.date(2025, 1, 1), key=f"{key_prefix}_s_dt")
        with dc2:
            e_dt = st.date_input("ຫາວັນທີ:", value=datetime.date.today(), key=f"{key_prefix}_e_dt")
        with dc3:
            m_cld = st.slider("☁️ ເມກສູງສຸດ (%):", 0, 80, 25, 5, key=f"{key_prefix}_cld")
        with dc4:
            st.write("")
            if st.button("🔍 ຄົ້ນຫາພາບຖ່າຍດາວທຽມຕາມວັນທີ", type="primary", use_container_width=True, key=f"{key_prefix}_btn_stac"):
                with st.spinner("🛰️ ກຳລັງຄົ້ນຫາພາບຖ່າຍດາວທຽມຈາກ Microsoft Planetary Computer..."):
                    st.session_state["stac_scenes"] = search_stac_satellite_scenes_by_date(
                        w_b, s_b, e_b, n_b, prov_type=prov_type, start_date=str(s_dt), end_date=str(e_dt), max_cloud=m_cld
                    )
        if st.session_state.get("stac_scenes"):
            sel_sc = st.selectbox("✅ ເລືອກວັນທີພາບຖ່າຍທີ່ພົບ:", options=st.session_state["stac_scenes"], format_func=lambda s: s["label"], key=f"{key_prefix}_sel_sc")
            custom_url = sel_sc["tile_url"]

    elif prov_type == "nasa_gibs_date":
        nc1, nc2 = st.columns([1.5, 3.0])
        with nc1:
            nasa_dt = st.date_input("📅 ເລືອກວັນທີ (YYYY-MM-DD):", value=datetime.date.today() - datetime.timedelta(days=4), key=f"{key_prefix}_nasa_dt")
        with nc2:
            nasa_ly = st.selectbox(
                "🛰️ ຊັ້ນຂໍ້ມູນ NASA GIBS ລາຍວັນ:",
                [
                    ("HLS_S30_Nadir_BRDF_Adjusted_Reflectance", "Harmonized Sentinel-2 True Color (30m)"),
                    ("HLS_L30_Nadir_BRDF_Adjusted_Reflectance", "Harmonized Landsat 8/9 True Color (30m)"),
                    ("VIIRS_SNPP_CorrectedReflectance_TrueColor", "VIIRS Suomi-NPP Daily True Color"),
                    ("MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS Terra Daily True Color")
                ],
                format_func=lambda x: x[1], key=f"{key_prefix}_nasa_ly"
            )
        lvl = "GoogleMapsCompatible_Level12" if "HLS" in nasa_ly[0] else "GoogleMapsCompatible_Level9"
        ext_f = "png" if "HLS" in nasa_ly[0] else "jpg"
        custom_url = f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{nasa_ly[0]}/default/{nasa_dt.strftime('%Y-%m-%d')}/{lvl}/{{z}}/{{y}}/{{x}}.{ext_f}"

    elif prov_type == "planet_monthly":
        pc1, pc2, pc3 = st.columns([1.2, 1.2, 2.5])
        with pc1:
            pl_y = st.selectbox("📅 ເລືອກປີ (Planet):", [2026, 2025, 2024, 2023, 2022, 2021, 2020], index=1, key=f"{key_prefix}_ply")
        with pc2:
            pl_m = st.selectbox("📅 ເລືອກເດືອນ:", [f"{m:02d}" for m in range(1, 13)], index=0, key=f"{key_prefix}_plm")
        with pc3:
            pl_k = st.text_input("🔑 Planet NICFI API Key (ຖ້າມີ):", value="", type="password", key=f"{key_prefix}_plk")
        if pl_k.strip():
            custom_url = f"https://tiles.planet.com/basemaps/v1/planet-tiles/planet_medres_visual_{pl_y}-{pl_m}_mosaic/gmap/{{z}}/{{x}}/{{y}}.png?api_key={pl_k.strip()}"
        else:
            custom_url = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg"

    elif prov_type == "esri_wayback":
        wb_sel = st.selectbox("📅 ເລືອກປີພາບຖ່າຍຍ້ອນຫຼັງ Esri Wayback (0.3m - 0.5m):", list(ESRI_WAYBACK_RELEASES.keys()), key=f"{key_prefix}_wb")
        rel_id = ESRI_WAYBACK_RELEASES[wb_sel]
        custom_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" if rel_id == "current" else f"https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{rel_id}/{{z}}/{{y}}/{{x}}"

    elif prov_type == "eox_yearly":
        ey_sel = st.selectbox("☀️ ເລືອກປີພາບຖ່າຍໄຮ້ເມກ EOX Sentinel-2 Cloudless:", list(EOX_CLOUDLESS_YEARS.keys()), key=f"{key_prefix}_eox")
        layer_id = EOX_CLOUDLESS_YEARS[ey_sel]
        custom_url = f"https://tiles.maps.eox.at/wmts/1.0.0/{layer_id}/default/g/{{z}}/{{y}}/{{x}}.jpg"

    elif prov_type == "custom_xyz":
        st.session_state["user_custom_xyz_url"] = st.text_input(
            "🔗 ວາງລິ້ງ Tile Server (XYZ / TMS / WMTS ທີ່ມີ {z}, {x}, {y}):",
            value=st.session_state["user_custom_xyz_url"],
            key=f"{key_prefix}_custom_xyz"
        )
        custom_url = st.session_state["user_custom_xyz_url"].strip()

    return custom_url


# ==============================================================================
# 6. ຟັງຊັນອ່ານຂອບເຂດບ້ານ (.SHP / .ZIP / .KML / .GEOJSON)
# ==============================================================================
def parse_kml_to_village_features(kml_bytes):
    text = kml_bytes.decode("utf-8", errors="ignore")
    placemarks = re.findall(r"<Placemark[^>]*>(.*?)</Placemark>", text, flags=re.DOTALL | re.IGNORECASE) or [text]
    features = []
    for idx, pm in enumerate(placemarks):
        name_m = re.search(r"<name[^>]*>(.*?)</name>", pm, flags=re.DOTALL | re.IGNORECASE)
        v_name = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", name_m.group(1).strip()).strip() if name_m else f"ຂອບເຂດ #{idx+1}"
        coord_blocks = re.findall(r"<coordinates[^>]*>(.*?)</coordinates>", pm, flags=re.DOTALL | re.IGNORECASE)
        rings = []
        for block in coord_blocks:
            pts = []
            for token in block.strip().split():
                parts = token.split(",")
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        if abs(lon) > 180.0 or abs(lat) > 90.0:
                            lon, lat = utm48n_to_lonlat(lon, lat)
                        pts.append([lon, lat])
                    except Exception:
                        pass
            if len(pts) >= 3:
                rings.append(pts)
        if rings:
            features.append({"idx": len(features), "attrs": {"NAME": v_name}, "rings": rings, "bbox": compute_bbox_from_polygons(rings)})
    return features, ["NAME"]


def parse_geojson_to_village_features(geojson_bytes):
    try:
        data = json.loads(geojson_bytes.decode("utf-8", errors="ignore"))
        feats_in = data.get("features", [data]) if isinstance(data, dict) else []
        features = []
        fields_set = set()
        for idx, f in enumerate(feats_in):
            props = f.get("properties") or {"NAME": f"ຂອບເຂດ #{idx+1}"}
            for k in props.keys():
                fields_set.add(str(k))
            geom = f.get("geometry") or {}
            gtype = geom.get("type", "")
            coords = geom.get("coordinates", [])
            rings = []
            if gtype == "Polygon":
                for r in coords:
                    if len(r) >= 3:
                        rings.append([[float(p[0]), float(p[1])] for p in r])
            elif gtype == "MultiPolygon":
                for poly in coords:
                    for r in poly:
                        if len(r) >= 3:
                            rings.append([[float(p[0]), float(p[1])] for p in r])
            if rings:
                attr_clean = {str(k): str(v) for k, v in props.items()}
                features.append({"idx": len(features), "attrs": attr_clean, "rings": rings, "bbox": compute_bbox_from_polygons(rings)})
        fields = sorted(list(fields_set)) or ["NAME"]
        return features, fields
    except Exception:
        return [], []


def parse_shapefile_to_village_features(shp_source, is_zip=False):
    sf = None
    for enc in ["utf-8", "cp874", "latin1"]:
        try:
            if is_zip:
                with zipfile.ZipFile(io.BytesIO(shp_source), "r") as zf:
                    shp_names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
                    if not shp_names:
                        return [], []
                    base = shp_names[0][:-4]
                    dbf_n = [n for n in zf.namelist() if n.lower() == (base + ".dbf").lower()]
                    shx_n = [n for n in zf.namelist() if n.lower() == (base + ".shx").lower()]
                    sf = shapefile.Reader(
                        shp=io.BytesIO(zf.read(shp_names[0])),
                        shx=io.BytesIO(zf.read(shx_n[0])) if shx_n else None,
                        dbf=io.BytesIO(zf.read(dbf_n[0])) if dbf_n else None,
                        encoding=enc
                    )
            else:
                sf = shapefile.Reader(shp_source, encoding=enc) if isinstance(shp_source, str) else shapefile.Reader(shp=io.BytesIO(shp_source), encoding=enc)
            _ = sf.records()
            break
        except Exception:
            sf = None
    if sf is None:
        return [], []
    fields = [f[0] for f in sf.fields[1:]] or ["ID"]
    records = sf.records() if sf else []
    features = []
    for idx, shp in enumerate(sf.shapes()):
        if not shp.points:
            continue
        parts = list(shp.parts) + [len(shp.points)]
        rings = []
        for i in range(len(parts) - 1):
            pts_wgs = []
            for x, y in shp.points[parts[i]:parts[i+1]]:
                lon, lat = utm48n_to_lonlat(x, y) if (abs(x) > 180.0 or abs(y) > 90.0) else (float(x), float(y))
                pts_wgs.append([lon, lat])
            if len(pts_wgs) >= 3:
                rings.append(pts_wgs)
        if rings:
            attr_dict = {}
            if idx < len(records):
                for f_i, f_name in enumerate(fields):
                    val = records[idx][f_i] if f_i < len(records[idx]) else ""
                    attr_dict[f_name] = val.decode("utf-8", errors="ignore").strip() if isinstance(val, bytes) else str(val).strip()
            else:
                attr_dict = {"ID": f"#{idx+1}"}
            features.append({"idx": len(features), "attrs": attr_dict, "rings": rings, "bbox": compute_bbox_from_polygons(rings)})
    return features, fields


def update_active_village_selection(selected_indices):
    feats = st.session_state["boundary_features"]
    if not feats:
        return
    selected_indices = selected_indices or [0]
    st.session_state["selected_village_indices"] = selected_indices
    chosen_rings = []
    chosen_names = []
    v_field = st.session_state.get("village_name_field", "NAME")

    for f in feats:
        if f["idx"] in selected_indices:
            chosen_rings.extend(f["rings"])
            raw_n = f["attrs"].get(v_field, f"village_{f['idx']+1}")
            safe_n = re.sub(r'[\\/*?:"<>|\s]+', "_", str(raw_n)).strip("_")
            if safe_n:
                chosen_names.append(safe_n)

    if chosen_rings:
        st.session_state["boundary_polygons_wgs84"] = chosen_rings
        new_bbox = compute_bbox_from_polygons(chosen_rings, buffer_pct=0.015)
        st.session_state["geo_bounds"] = new_bbox
        st.session_state["map_init_center"] = [(new_bbox[1] + new_bbox[3]) / 2.0, (new_bbox[0] + new_bbox[2]) / 2.0]
        st.session_state["map_init_zoom"] = 15
        st.session_state["dl_map_cmd_counter"] += 1
        if len(selected_indices) == 1 and chosen_names:
            st.session_state["save_filename"] = f"sat_{chosen_names[0]}"
        elif chosen_names:
            st.session_state["save_filename"] = f"sat_{chosen_names[0]}_{len(selected_indices)}areas"


def extract_drawn_rings_from_map_data(map_data):
    rings = []
    if not map_data:
        return rings
    raw_list = map_data.get("all_drawings") or []
    if not raw_list and map_data.get("last_active_drawing"):
        raw_list = [map_data["last_active_drawing"]]
    for d in raw_list:
        geom = d.get("geometry", {})
        if geom.get("type") == "Polygon":
            coords = geom.get("coordinates", [[]])[0]
            if len(coords) >= 3:
                r = [[float(c[0]), float(c[1])] for c in coords]
                if len(r) > 3 and r[0] == r[-1]:
                    r = r[:-1]
                rings.append(r)
    return rings


# ==============================================================================
# 7. ລະບົບດາວໂຫຼດພາບດາວທຽມແບບບໍ່ຈຳກັດຂະໜາດ (UNLIMITED NATIVE DOWNLOADER & ECW/DEM)
# ==============================================================================
def tile_xy_to_quadkey(x, y, z):
    quadkey = []
    for i in range(z, 0, -1):
        digit = 0
        mask = 1 << (i - 1)
        if (x & mask) != 0:
            digit += 1
        if (y & mask) != 0:
            digit += 2
        quadkey.append(str(digit))
    return "".join(quadkey)


def deg2xy_float(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x = (lon_deg + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def calculate_download_grid_specs(west, south, east, north, zoom, tile_px=512):
    x_min_f, y_min_f = deg2xy_float(north, west, int(zoom))
    x_max_f, y_max_f = deg2xy_float(south, east, int(zoom))
    tx_min, ty_min = int(math.floor(x_min_f)), int(math.floor(y_min_f))
    tx_max, ty_max = int(math.floor(x_max_f)), int(math.floor(y_max_f))
    nx, ny = max(1, tx_max - tx_min + 1), max(1, ty_max - ty_min + 1)

    crop_x0 = max(0, int(round((x_min_f - tx_min) * tile_px)))
    crop_y0 = max(0, int(round((y_min_f - ty_min) * tile_px)))
    crop_x1 = min(nx * tile_px, max(crop_x0 + 64, int(round((x_max_f - tx_min) * tile_px))))
    crop_y1 = min(ny * tile_px, max(crop_y0 + 64, int(round((y_max_f - ty_min) * tile_px))))

    exact_w = max(64, crop_x1 - crop_x0)
    exact_h = max(64, crop_y1 - crop_y0)

    e_w, n_s = lonlat_to_utm48n(west, south)
    e_e, n_n = lonlat_to_utm48n(east, north)
    width_m = abs(e_e - e_w)
    height_m = abs(n_n - n_s)
    area_km2 = round((width_m * height_m) / 1e6, 2)
    gsd_m = max(0.01, round(width_m / float(max(1, exact_w)), 4))

    raw_bytes = float(exact_w) * float(exact_h) * 3.0
    est_tif_mb = round((raw_bytes * 0.45) / (1024**2), 1)
    est_ecw_mb = round((raw_bytes * 0.12) / (1024**2), 1)
    return {
        "tx_min": tx_min, "ty_min": ty_min, "tx_max": tx_max, "ty_max": ty_max,
        "nx": nx, "ny": ny, "total_tiles": nx * ny,
        "crop_x0": crop_x0, "crop_y0": crop_y0, "crop_x1": crop_x1, "crop_y1": crop_y1,
        "exact_w": exact_w, "exact_h": exact_h, "gsd_m": gsd_m,
        "area_km2": area_km2, "est_tif_mb": est_tif_mb, "est_ecw_mb": est_ecw_mb
    }


def build_tile_url(provider_name, x, y, z, custom_tile_tpl=""):
    if custom_tile_tpl:
        url = custom_tile_tpl.format(x=x, y=y, z=z)
        if "mt1.google.com" in url:
            url = url.replace("mt1.google.com", f"mt{(x + y) % 4}.google.com")
        return url
    p_info = SATELLITE_PROVIDERS[provider_name]
    if p_info["type"] == "quadkey":
        return p_info["url"].format(quadkey=tile_xy_to_quadkey(x, y, z))
    url = p_info["url"].format(x=x, y=y, z=z)
    if "mt1.google.com" in url:
        url = url.replace("mt1.google.com", f"mt{(x + y) % 4}.google.com")
    return url


def download_single_tile_session(session, url, ix, iy, target_tile_px=512):
    for _ in range(3):
        try:
            resp = session.get(url, timeout=12)
            if resp.status_code == 200:
                tile = Image.open(io.BytesIO(resp.content)).convert("RGB")
                if tile.size != (target_tile_px, target_tile_px):
                    tile = tile.resize((target_tile_px, target_tile_px), Image.Resampling.LANCZOS)
                return ix, iy, np.ascontiguousarray(tile, dtype=np.uint8)
        except Exception:
            pass
    return ix, iy, None


def decode_terrarium_dem_to_meters_and_color_hillshade(rgb_arr):
    r = rgb_arr[:, :, 0].astype(np.float32)
    g = rgb_arr[:, :, 1].astype(np.float32)
    b = rgb_arr[:, :, 2].astype(np.float32)
    elev_m = np.clip((r * 256.0 + g + (b / 256.0)) - 32768.0, -500.0, 9000.0)
    valid = elev_m[elev_m > -100.0]
    e_min, e_max = (float(np.percentile(valid, 2)), float(np.percentile(valid, 98))) if len(valid) > 10 else (0.0, 1000.0)
    norm_u8 = np.clip((elev_m - e_min) * 255.0 / max(1.0, e_max - e_min), 0, 255).astype(np.uint8)
    color_rgb = cv2.cvtColor(cv2.applyColorMap(norm_u8, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    gx = cv2.Sobel(elev_m, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(elev_m, cv2.CV_32F, 0, 1, ksize=3)
    slope = np.sqrt(gx ** 2 + gy ** 2)
    shade = np.clip(1.0 - (slope / (np.percentile(slope, 95) + 1.0)) * 0.45, 0.4, 1.0)
    return elev_m, np.ascontiguousarray((color_rgb.astype(np.float32) * shade[:, :, None]), dtype=np.uint8)


def write_world_and_prj_files(file_path, west, south, east, north, width, height, coord_sys="UTM48N"):
    base, ext = os.path.splitext(file_path)
    wld_map = {
        ".tif": ".tfw", ".tiff": ".tfw",
        ".ecw": ".eww", ".jp2": ".j2w",
        ".png": ".pgw", ".jpg": ".jgw", ".jpeg": ".jgw"
    }
    wld_ext = wld_map.get(ext.lower(), ".wld")

    e_w, n_s = lonlat_to_utm48n(west, south)
    e_e, n_n = lonlat_to_utm48n(east, north)
    gsd_m = max(0.01, round(abs(e_e - e_w) / float(max(1, width)), 4))

    if coord_sys == "UTM48N":
        px_x = (e_e - e_w) / float(max(1, width))
        px_y = -(n_n - n_s) / float(max(1, height))
        ul_x, ul_y = e_w + (px_x / 2.0), n_n + (px_y / 2.0)
        prj_wkt = (
            'PROJCS["WGS_1984_UTM_Zone_48N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
            'SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
            'UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
            'PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],'
            'PARAMETER["Central_Meridian",105.0],PARAMETER["Scale_Factor",0.9996],'
            'PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
        )
    else:
        px_x = (east - west) / float(max(1, width))
        px_y = -(north - south) / float(max(1, height))
        ul_x, ul_y = west + (px_x / 2.0), north + (px_y / 2.0)
        prj_wkt = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'

    for ext_w in set([wld_ext, ".wld"]):
        with open(base + ext_w, "w", encoding="utf-8") as f:
            f.write(f"{px_x:.10f}\n0.0\n0.0\n{px_y:.10f}\n{ul_x:.10f}\n{ul_y:.10f}\n")

    with open(base + ".prj", "w", encoding="utf-8") as f:
        f.write(prj_wkt)

    gt_0 = e_w if coord_sys == "UTM48N" else west
    gt_3 = n_n if coord_sys == "UTM48N" else north
    aux_xml = (
        f'<PAMDataset>\n'
        f'  <SRS>{escape(prj_wkt)}</SRS>\n'
        f'  <GeoTransform>{gt_0:.8f}, {px_x:.10f}, 0.0, {gt_3:.8f}, 0.0, {px_y:.10f}</GeoTransform>\n'
        f'</PAMDataset>\n'
    )
    with open(file_path + ".aux.xml", "w", encoding="utf-8") as f:
        f.write(aux_xml)

    return gsd_m


def find_gdal_translate_exe():
    exe = shutil.which("gdal_translate")
    if exe:
        return exe
    search_patterns = [
        "C:/Program Files/QGIS*/bin/gdal_translate.exe",
        "C:/OSGeo4W*/bin/gdal_translate.exe",
        "C:/Program Files (x86)/QGIS*/bin/gdal_translate.exe",
        os.path.join(sys.prefix, "Library", "bin", "gdal_translate.exe"),
    ]
    for pat in search_patterns:
        matches = sorted(glob.glob(pat), reverse=True)
        if matches:
            return matches[0]
    return None


def convert_raster_to_ecw_or_gis_wavelet(src_tif_path, target_ecw_path, west, south, east, north, width, height, coord_sys="UTM48N"):
    gdal_exe = find_gdal_translate_exe()
    converted_native_ecw = False

    if gdal_exe and os.path.isfile(src_tif_path):
        try:
            res = subprocess.run(
                [gdal_exe, "-of", "ECW", "-co", "TARGET=90", src_tif_path, target_ecw_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600
            )
            if res.returncode == 0 and os.path.isfile(target_ecw_path) and os.path.getsize(target_ecw_path) > 512:
                converted_native_ecw = True
        except Exception:
            pass

    if not converted_native_ecw and HAS_RASTERIO and os.path.isfile(src_tif_path):
        try:
            with rasterio.open(src_tif_path) as src:
                profile = src.profile.copy()
                profile.update(driver="ECW")
                with rasterio.open(target_ecw_path, "w", **profile) as dst:
                    for b_i in range(1, src.count + 1):
                        dst.write(src.read(b_i), b_i)
                if os.path.isfile(target_ecw_path) and os.path.getsize(target_ecw_path) > 512:
                    converted_native_ecw = True
        except Exception:
            pass

    if not converted_native_ecw and os.path.isfile(src_tif_path):
        if os.path.abspath(src_tif_path) != os.path.abspath(target_ecw_path):
            shutil.copy2(src_tif_path, target_ecw_path)

    write_world_and_prj_files(target_ecw_path, west, south, east, north, width, height, coord_sys=coord_sys)
    return converted_native_ecw


class NonStopBackgroundDownloadManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.status = "idle"
        self.completed_tiles = 0
        self.total_tiles = 1
        self.pct = 0
        self.message = ""
        self.out_file_path = ""
        self.w_out = 0
        self.h_out = 0
        self.gsd_m = 1.0
        self.pause_flag = False
        self.cancel_flag = False

    def start_download(
        self, west, south, east, north, zoom, provider_name, out_file_path,
        clip_polygons_wgs84=None, custom_tile_tpl="", tile_px=512, coord_sys="UTM48N"
    ):
        with self.lock:
            if self.status in ("running", "paused"):
                return False
            self.status = "running"
            self.completed_tiles, self.total_tiles, self.pct = 0, 1, 0
            self.out_file_path = out_file_path
            self.pause_flag, self.cancel_flag = False, False
            self.message = "⏳ ກຳລັງກຽມຕາໜ່າງພິກັດພາບດາວທຽມຄວາມລະອຽດສູງສຸດ (ບໍ່ຈຳກັດຂະໜາດ)..."

        clip_copy = [list(ring) for ring in clip_polygons_wgs84] if clip_polygons_wgs84 else None
        self.thread = threading.Thread(
            target=self._worker,
            args=(west, south, east, north, zoom, provider_name, out_file_path, clip_copy, custom_tile_tpl, tile_px, coord_sys),
            daemon=True
        )
        self.thread.start()
        return True

    def pause(self):
        with self.lock:
            if self.status == "running":
                self.pause_flag = True
                self.status = "paused"
                self.message = f"⏸️ ຢຸດຊົ່ວຄາວທີ່ {self.pct}% ({self.completed_tiles:,}/{self.total_tiles:,} ແຜ່ນ)"

    def resume(self):
        with self.lock:
            if self.status == "paused":
                self.pause_flag = False
                self.status = "running"
                self.message = f"▶️ ກຳລັງດາວໂຫຼດຕໍ່ຈາກ {self.pct}%..."

    def cancel(self):
        with self.lock:
            if self.status in ("running", "paused"):
                self.cancel_flag = True
                self.pause_flag = False
                self.message = "🛑 ກຳລັງຍົກເລີກການດາວໂຫຼດ..."

    def _worker(self, west, south, east, north, zoom, provider_name, out_file_path, clip_polygons_wgs84, custom_tile_tpl, tile_px, coord_sys):
        mmap_file_path = ""
        try:
            p_info = SATELLITE_PROVIDERS[provider_name]
            actual_zoom = min(int(zoom), p_info.get("max_z", 22))
            is_dem = (p_info["type"] == "dem_terrarium")
            tile_px = int(tile_px)

            specs = calculate_download_grid_specs(west, south, east, north, actual_zoom, tile_px=tile_px)
            tx_min, ty_min = specs["tx_min"], specs["ty_min"]
            nx, ny = specs["nx"], specs["ny"]
            crop_x0, crop_y0 = specs["crop_x0"], specs["crop_y0"]
            crop_x1, crop_y1 = specs["crop_x1"], specs["crop_y1"]
            exact_w, exact_h = specs["exact_w"], specs["exact_h"]

            tile_mask = np.ones((ny, nx), dtype=np.uint8)
            if clip_polygons_wgs84 and len(clip_polygons_wgs84) > 0 and (nx * ny > 9):
                poly_grid = np.zeros((ny * 8, nx * 8), dtype=np.uint8)
                for ring in clip_polygons_wgs84:
                    pts_g = [[int(round((deg2xy_float(lat, lon, actual_zoom)[0] - tx_min) * 8)), int(round((deg2xy_float(lat, lon, actual_zoom)[1] - ty_min) * 8))] for lon, lat in ring]
                    if len(pts_g) >= 3:
                        cv2.fillPoly(poly_grid, [np.array(pts_g, dtype=np.int32)], 255)
                poly_grid = cv2.dilate(poly_grid, np.ones((3, 3), np.uint8), iterations=1)
                tile_mask = cv2.resize(poly_grid, (nx, ny), interpolation=cv2.INTER_NEAREST) > 0

            total_tiles = max(1, int(np.sum(tile_mask)))
            with self.lock:
                self.total_tiles, self.w_out, self.h_out = total_tiles, exact_w, exact_h
                self.message = f"🛰️ [0%] ກຳລັງດາວໂຫຼດພາບຄວາມລະອຽດສູງສຸດ Zoom {actual_zoom}: 0 / {total_tiles:,} ແຜ່ນ (ຂະໜາດແທ້ {exact_w:,} x {exact_h:,} px)..."

            out_dir = os.path.dirname(out_file_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            ext_low = os.path.splitext(out_file_path)[1].lower()
            session = requests.Session()
            max_dl_threads = min(40, CPU_CORES * 3)
            adapter = HTTPAdapter(pool_connections=max_dl_threads, pool_maxsize=max_dl_threads)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            session.headers.update({"User-Agent": "Mozilla/5.0 GeoMapUltra/36.1"})

            raw_canvas_bytes = int(ny) * int(nx) * int(tile_px) * int(tile_px) * 3
            if raw_canvas_bytes > int(1.2 * (1024**3)):
                mmap_file_path = os.path.join(out_dir or tempfile.gettempdir(), f"_geomap_stream_{int(time.time())}.mmap")
                canvas_arr = np.memmap(mmap_file_path, dtype=np.uint8, mode="w+", shape=(ny * tile_px, nx * tile_px, 3))
            else:
                canvas_arr = np.zeros((ny * tile_px, nx * tile_px, 3), dtype=np.uint8)

            completed = 0
            row_step = 4
            for ry_start in range(0, ny, row_step):
                while self.pause_flag and not self.cancel_flag:
                    time.sleep(0.25)
                if self.cancel_flag:
                    del canvas_arr
                    if mmap_file_path and os.path.exists(mmap_file_path):
                        try:
                            os.remove(mmap_file_path)
                        except Exception:
                            pass
                    with self.lock:
                        self.status, self.message = "cancelled", "🛑 ຍົກເລີກການດາວໂຫຼດແລ້ວ!"
                    return

                ry_end = min(ny, ry_start + row_step)
                batch_tasks = [
                    (build_tile_url(provider_name, tx_min + ix, ty_min + iy, actual_zoom, custom_tile_tpl), ix, iy)
                    for iy in range(ry_start, ry_end) for ix in range(nx) if tile_mask[iy, ix]
                ]
                if batch_tasks:
                    with ThreadPoolExecutor(max_workers=max_dl_threads) as executor:
                        futures = [executor.submit(download_single_tile_session, session, t[0], t[1], t[2], tile_px) for t in batch_tasks]
                        for fut in as_completed(futures):
                            if self.cancel_flag:
                                break
                            ix, iy, tile_arr = fut.result()
                            if tile_arr is not None:
                                canvas_arr[iy * tile_px:(iy + 1) * tile_px, ix * tile_px:(ix + 1) * tile_px] = tile_arr
                            completed += 1
                            pct = min(92, int((completed / float(total_tiles)) * 92))
                            with self.lock:
                                self.completed_tiles, self.pct = completed, pct
                                if not self.pause_flag and not self.cancel_flag:
                                    self.message = f"🛰️ [{pct}%] ກຳລັງດາວໂຫຼດ Zoom {actual_zoom}: {completed:,} / {total_tiles:,} ແຜ່ນ ({exact_w:,} x {exact_h:,} px)..."

            with self.lock:
                self.pct = 95
                self.message = f"💾 [95%] ກຳລັງຕັດຂອບເຂດ ແລະ ບັນທຶກໄຟລ໌ GIS ຄວາມລະອຽດສູງ ({exact_w:,} x {exact_h:,} px)..."

            cropped_view = canvas_arr[crop_y0:crop_y1, crop_x0:crop_x1]
            dem_elev_m = None
            if is_dem:
                dem_elev_m, cropped_view = decode_terrarium_dem_to_meters_and_color_hillshade(np.asarray(cropped_view))

            if clip_polygons_wgs84 and len(clip_polygons_wgs84) > 0:
                clip_mask = np.zeros((exact_h, exact_w), dtype=np.uint8)
                for ring in clip_polygons_wgs84:
                    pts_px = [[int(round(((lon - west) / max(1e-9, east - west)) * exact_w)), int(round(((north - lat) / max(1e-9, north - south)) * exact_h))] for lon, lat in ring]
                    if len(pts_px) >= 3:
                        cv2.fillPoly(clip_mask, [np.array(pts_px, dtype=np.int32)], 255)
                strip_h = 2048
                for sy in range(0, exact_h, strip_h):
                    ey = min(exact_h, sy + strip_h)
                    m_strip = clip_mask[sy:ey, :, None] > 0
                    cropped_view[sy:ey] = np.where(m_strip, cropped_view[sy:ey], 0)
                if dem_elev_m is not None:
                    dem_elev_m = np.where(clip_mask > 0, dem_elev_m, -9999.0)
                del clip_mask

            e_w, n_s = lonlat_to_utm48n(west, south)
            e_e, n_n = lonlat_to_utm48n(east, north)

            if HAS_RASTERIO:
                target_crs = "EPSG:32648" if coord_sys == "UTM48N" else "EPSG:4326"
                target_transform = from_bounds(e_w, n_s, e_e, n_n, exact_w, exact_h) if coord_sys == "UTM48N" else from_bounds(west, south, east, north, exact_w, exact_h)

                if is_dem and dem_elev_m is not None:
                    dem_raw_path = os.path.splitext(out_file_path)[0] + "_DEM_Elevation_Meters.tif"
                    with rasterio.open(
                        dem_raw_path, "w", driver="GTiff", height=exact_h, width=exact_w, count=1, dtype=np.float32,
                        crs=target_crs, transform=target_transform, nodata=-9999.0, compress="lzw", tiled=True
                    ) as dst_dem:
                        dst_dem.write(dem_elev_m.astype(np.float32), 1)
                    write_world_and_prj_files(dem_raw_path, west, south, east, north, exact_w, exact_h, coord_sys=coord_sys)

            if ext_low in (".tif", ".tiff", ".ecw", ".jp2") and HAS_RASTERIO:
                temp_tif_path = out_file_path if ext_low in (".tif", ".tiff") else (os.path.splitext(out_file_path)[0] + "_master_temp.tif")
                with rasterio.open(
                    temp_tif_path, "w", driver="GTiff", height=exact_h, width=exact_w, count=3, dtype=np.uint8,
                    crs=target_crs, transform=target_transform,
                    compress="jpeg" if ext_low == ".ecw" else "lzw",
                    tiled=True, blockxsize=256, blockysize=256, BIGTIFF="YES"
                ) as dst:
                    strip_h = 1024
                    for sy in range(0, exact_h, strip_h):
                        ey = min(exact_h, sy + strip_h)
                        sub_arr = np.ascontiguousarray(cropped_view[sy:ey])
                        win = Window(0, sy, exact_w, ey - sy)
                        for c in range(3):
                            dst.write(sub_arr[:, :, c], c + 1, window=win)

                if ext_low == ".ecw":
                    with self.lock:
                        self.pct = 98
                        self.message = "🔄 [98%] ກຳລັງແປງໄຟລ໌ເປັນ .ECW (Enhanced Compression Wavelet) ພ້ອມໄຟລ໌ພິກັດ .eww/.prj..."
                    convert_raster_to_ecw_or_gis_wavelet(temp_tif_path, out_file_path, west, south, east, north, exact_w, exact_h, coord_sys=coord_sys)
                    if os.path.exists(temp_tif_path) and os.path.abspath(temp_tif_path) != os.path.abspath(out_file_path):
                        try:
                            os.remove(temp_tif_path)
                        except Exception:
                            pass
                elif ext_low == ".jp2":
                    gdal_exe = find_gdal_translate_exe()
                    if gdal_exe:
                        subprocess.run([gdal_exe, "-of", "JP2OpenJPEG", temp_tif_path, out_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if not os.path.exists(out_file_path):
                        shutil.move(temp_tif_path, out_file_path)
                    elif os.path.exists(temp_tif_path):
                        try:
                            os.remove(temp_tif_path)
                        except Exception:
                            pass
            else:
                cv2.imwrite(out_file_path, cv2.cvtColor(np.ascontiguousarray(cropped_view), cv2.COLOR_RGB2BGR))

            gsd_m = write_world_and_prj_files(out_file_path, west, south, east, north, exact_w, exact_h, coord_sys=coord_sys)

            del cropped_view
            del canvas_arr
            if mmap_file_path and os.path.exists(mmap_file_path):
                try:
                    os.remove(mmap_file_path)
                except Exception:
                    pass
            gc.collect()

            with self.lock:
                self.w_out, self.h_out, self.gsd_m, self.pct = exact_w, exact_h, gsd_m, 100
                self.status = "completed"
                self.message = f"🎉 [100%] ດາວໂຫຼດພາບຄວາມລະອຽດສູງສຸດ `{out_file_path}` ({exact_w:,} x {exact_h:,} px | GSD: {gsd_m} m/px) ສຳເລັດແລ້ວ!"

        except Exception as ex:
            if mmap_file_path and os.path.exists(mmap_file_path):
                try:
                    os.remove(mmap_file_path)
                except Exception:
                    pass
            with self.lock:
                self.status, self.message = "error", f"❌ ເກີດຂໍ້ຜິດພາດ: {ex}"


@st.cache_resource
def get_global_download_manager():
    return NonStopBackgroundDownloadManager()


dl_mgr = get_global_download_manager()


def fetch_bbox_rgb_preview(west, south, east, north, zoom, provider_name, custom_tile_tpl="", max_tiles_cap=64):
    p_info = SATELLITE_PROVIDERS[provider_name]
    actual_zoom = min(int(zoom), p_info.get("max_z", 22))
    x_min_f, y_min_f = deg2xy_float(north, west, actual_zoom)
    x_max_f, y_max_f = deg2xy_float(south, east, actual_zoom)
    tx_min, ty_min = int(math.floor(x_min_f)), int(math.floor(y_min_f))
    tx_max, ty_max = int(math.floor(x_max_f)), int(math.floor(y_max_f))
    nx, ny = max(1, tx_max - tx_min + 1), max(1, ty_max - ty_min + 1)

    while (nx * ny > max_tiles_cap) and actual_zoom > 12:
        actual_zoom -= 1
        x_min_f, y_min_f = deg2xy_float(north, west, actual_zoom)
        x_max_f, y_max_f = deg2xy_float(south, east, actual_zoom)
        tx_min, ty_min = int(math.floor(x_min_f)), int(math.floor(y_min_f))
        tx_max, ty_max = int(math.floor(x_max_f)), int(math.floor(y_max_f))
        nx, ny = max(1, tx_max - tx_min + 1), max(1, ty_max - ty_min + 1)

    crop_x0 = max(0, int(round((x_min_f - tx_min) * 256)))
    crop_y0 = max(0, int(round((y_min_f - ty_min) * 256)))
    crop_x1 = min(nx * 256, max(crop_x0 + 32, int(round((x_max_f - tx_min) * 256))))
    crop_y1 = min(ny * 256, max(crop_y0 + 32, int(round((y_max_f - ty_min) * 256))))

    canvas_arr = np.zeros((ny * 256, nx * 256, 3), dtype=np.uint8)
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=24, pool_maxsize=24)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "Mozilla/5.0 GeoMapUltra/36.1"})

    tasks = [(build_tile_url(provider_name, tx_min + ix, ty_min + iy, actual_zoom, custom_tile_tpl), ix, iy) for iy in range(ny) for ix in range(nx)]
    with ThreadPoolExecutor(max_workers=min(24, len(tasks) or 1)) as executor:
        futures = [executor.submit(download_single_tile_session, session, t[0], t[1], t[2], 256) for t in tasks]
        for fut in as_completed(futures):
            ix, iy, tile_arr = fut.result()
            if tile_arr is not None:
                canvas_arr[iy*256:(iy+1)*256, ix*256:(ix+1)*256] = tile_arr

    patch = np.ascontiguousarray(canvas_arr[crop_y0:crop_y1, crop_x0:crop_x1], dtype=np.uint8)
    elev_m = None
    if p_info["type"] == "dem_terrarium":
        elev_m, patch = decode_terrarium_dem_to_meters_and_color_hillshade(patch)
    return patch, elev_m, actual_zoom


# ==============================================================================
# 8. ລະບົບສ້າງເສັ້ນລະດັບຄວາມສູງໂຄ້ງມົນ (SMOOTH CARTOGRAPHIC CONTOURS) & OSM VECTOR
# ==============================================================================
def split_contour_at_raster_border_and_smooth(cnt_pts, w, h, border_margin=2.5, chaikin_iters=4, is_closed_loop=True):
    pts = np.asarray(cnt_pts, dtype=np.float64).reshape(-1, 2)
    if len(pts) < 6:
        return []

    on_border = (
        (pts[:, 0] <= border_margin) |
        (pts[:, 0] >= (w - 1 - border_margin)) |
        (pts[:, 1] <= border_margin) |
        (pts[:, 1] >= (h - 1 - border_margin))
    )

    segments = []
    if not np.any(on_border):
        segments.append((pts, True))
    else:
        first_b = int(np.argmax(on_border))
        pts_rot = np.roll(pts, -first_b, axis=0)
        b_rot = np.roll(on_border, -first_b)

        cur_seg = []
        for pt, is_b in zip(pts_rot, b_rot):
            if not is_b:
                cur_seg.append(pt)
            else:
                if len(cur_seg) >= 5:
                    segments.append((np.array(cur_seg, dtype=np.float64), False))
                cur_seg = []
        if len(cur_seg) >= 5:
            segments.append((np.array(cur_seg, dtype=np.float64), False))

    smoothed_segments = []
    for seg_pts, closed_flag in segments:
        cnt_cv = seg_pts.astype(np.float32).reshape((-1, 1, 2))
        approx = cv2.approxPolyDP(cnt_cv, 0.85, closed_flag).reshape(-1, 2).astype(np.float64)
        if len(approx) < (4 if closed_flag else 3):
            approx = seg_pts

        coords = approx
        for _ in range(max(1, int(chaikin_iters))):
            if closed_flag:
                p0 = coords
                p1 = np.roll(coords, -1, axis=0)
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1
                new_c = np.empty((len(coords) * 2, 2), dtype=np.float64)
                new_c[0::2] = q
                new_c[1::2] = r
                coords = new_c
            else:
                if len(coords) < 3:
                    break
                p0 = coords[:-1]
                p1 = coords[1:]
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1
                inner = np.empty((len(p0) * 2, 2), dtype=np.float64)
                inner[0::2] = q
                inner[1::2] = r
                coords = np.vstack([coords[0:1], inner, coords[-1:]])

            if len(coords) > 2500:
                break

        if len(coords) >= 7:
            if closed_flag:
                pad_c = np.vstack([coords[-2:], coords, coords[:2]])
                sm_x = np.convolve(pad_c[:, 0], [0.1, 0.2, 0.4, 0.2, 0.1], mode="valid")
                sm_y = np.convolve(pad_c[:, 1], [0.1, 0.2, 0.4, 0.2, 0.1], mode="valid")
                coords = np.column_stack([sm_x, sm_y])
                coords = np.vstack([coords, coords[0:1]])
            else:
                sm_x = np.convolve(coords[:, 0], [0.15, 0.2, 0.3, 0.2, 0.15], mode="valid")
                sm_y = np.convolve(coords[:, 1], [0.15, 0.2, 0.3, 0.2, 0.15], mode="valid")
                coords = np.vstack([coords[0:2], np.column_stack([sm_x, sm_y]), coords[-2:]])

        final_cv = cv2.approxPolyDP(coords.astype(np.float32).reshape((-1, 1, 2)), 0.22, closed_flag).reshape(-1, 2)
        if closed_flag and len(final_cv) >= 4:
            if not np.allclose(final_cv[0], final_cv[-1]):
                final_cv = np.vstack([final_cv, final_cv[0:1]])
        if len(final_cv) >= 3:
            smoothed_segments.append(final_cv)

    return smoothed_segments


def generate_smooth_cartographic_contours(
    elev_grid, west, south, east, north,
    interval_m=10, smooth_sigma=2.6, min_length_m=120.0, chaikin_iters=4
):
    eh_raw, ew_raw = elev_grid.shape[:2]
    scale_up = 2 if max(eh_raw, ew_raw) <= 1400 else 1
    ew, eh = ew_raw * scale_up, eh_raw * scale_up
    elev_up = cv2.resize(elev_grid.astype(np.float32), (ew, eh), interpolation=cv2.INTER_CUBIC) if scale_up > 1 else elev_grid.astype(np.float32).copy()

    sigma_px = max(1.0, float(smooth_sigma) * scale_up)
    ksize = int(math.ceil(sigma_px * 3) * 2 + 1)
    elev_smooth = cv2.GaussianBlur(elev_up, (ksize, ksize), sigma_px)
    elev_smooth = cv2.GaussianBlur(elev_smooth, (5, 5), sigma_px * 0.6)

    valid_vals = elev_smooth[elev_smooth > -100.0]
    if valid_vals.size < 50:
        return []

    step = max(1, int(interval_m))
    index_step = step * 5
    min_e = int(math.floor(float(np.min(valid_vals)) / step) * step)
    max_e = int(math.ceil(float(np.max(valid_vals)) / step) * step)

    e_w, n_s = lonlat_to_utm48n(west, south)
    e_e, n_n = lonlat_to_utm48n(east, north)
    m_per_px = max(0.5, abs(e_e - e_w) / float(max(1, ew)))
    min_arc_px = float(min_length_m) / m_per_px

    contours_out = []
    for lev in range(max(0, min_e), min(8500, max_e + step), step):
        bin_m = (elev_smooth >= float(lev)).astype(np.uint8) * 255
        cnts, _ = cv2.findContours(bin_m, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        is_index_contour = (lev % index_step == 0)
        c_type = "INDEX" if is_index_contour else "INTERMED"

        for c in cnts:
            arc_px = cv2.arcLength(c, True)
            if arc_px < min_arc_px:
                continue
            smooth_segs = split_contour_at_raster_border_and_smooth(
                c, ew, eh, border_margin=3.0, chaikin_iters=chaikin_iters
            )
            for seg_px in smooth_segs:
                diffs = np.diff(seg_px, axis=0)
                seg_len_m = float(np.sum(np.hypot(diffs[:, 0], diffs[:, 1]))) * m_per_px
                if seg_len_m < float(min_length_m):
                    continue

                wgs_line = [
                    (
                        west + (float(px) / float(ew - 1)) * (east - west),
                        north - (float(py) / float(eh - 1)) * (north - south)
                    )
                    for px, py in seg_px
                ]
                contours_out.append({
                    "elev_m": float(lev),
                    "type": c_type,
                    "length_m": round(seg_len_m, 1),
                    "coords_wgs": wgs_line
                })

    return contours_out


def fetch_free_osm_vector_gis_zip(
    west, south, east, north, coord_sys="UTM48N",
    include_contours=True, contour_interval_m=10,
    contour_smooth_sigma=2.8, min_contour_len_m=150.0
):
    overpass_urls = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    bbox_str = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"
    query = f"""
    [out:json][timeout:45];
    (
      way["highway"]({bbox_str});
      way["waterway"]({bbox_str});
      way["natural"="water"]({bbox_str});
      way["building"]({bbox_str});
      way["landuse"]({bbox_str});
    );
    out body;
    >;
    out skel qt;
    """
    osm_json = None
    for ov_url in overpass_urls:
        try:
            r = requests.post(ov_url, data={"data": query}, timeout=45)
            if r.status_code == 200:
                osm_json = r.json()
                break
        except Exception:
            pass

    nodes_map = {}
    roads_list, rivers_list, buildings_list, landuse_list = [], [], [], []

    if osm_json and "elements" in osm_json:
        for el in osm_json["elements"]:
            if el.get("type") == "node":
                nodes_map[el["id"]] = (float(el["lon"]), float(el["lat"]))

        for el in osm_json["elements"]:
            if el.get("type") == "way":
                tags = el.get("tags", {})
                nds = el.get("nodes", [])
                coords_wgs = [nodes_map[nid] for nid in nds if nid in nodes_map]
                if len(coords_wgs) < 2:
                    continue
                name_str = str(tags.get("name:lo") or tags.get("name") or "")[:80]

                if "highway" in tags:
                    roads_list.append({"type": str(tags["highway"])[:40], "name": name_str, "coords": coords_wgs})
                elif "waterway" in tags:
                    rivers_list.append({"type": str(tags["waterway"])[:40], "name": name_str, "coords": coords_wgs})
                elif "building" in tags and len(coords_wgs) >= 3:
                    buildings_list.append({"type": str(tags["building"])[:40], "name": name_str, "coords": coords_wgs})
                elif ("landuse" in tags or tags.get("natural") == "water") and len(coords_wgs) >= 3:
                    l_type = str(tags.get("landuse") or tags.get("natural", "water"))[:40]
                    landuse_list.append({"type": l_type, "name": name_str, "coords": coords_wgs})

    prj_wkt = (
        'PROJCS["WGS_1984_UTM_Zone_48N",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",105.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
        if coord_sys == "UTM48N" else
        'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    )

    def _transform_pts(coords_wgs):
        return [list(lonlat_to_utm48n(lon, lat)) if coord_sys == "UTM48N" else [lon, lat] for lon, lat in coords_wgs]

    contours_count = 0
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if roads_list:
            s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
            w = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYLINE)
            w.field("ID", "N", 10)
            w.field("ROAD_TYPE", "C", 50)
            w.field("NAME", "C", 100)
            for i, item in enumerate(roads_list, 1):
                w.line([_transform_pts(item["coords"])])
                w.record(i, item["type"], item["name"])
            w.close()
            zf.writestr("01_OSM_Roads_Line.shp", s_io.getvalue())
            zf.writestr("01_OSM_Roads_Line.shx", x_io.getvalue())
            zf.writestr("01_OSM_Roads_Line.dbf", d_io.getvalue())
            zf.writestr("01_OSM_Roads_Line.prj", prj_wkt.encode("utf-8"))
            zf.writestr("01_OSM_Roads_Line.cpg", b"UTF-8")

        if rivers_list:
            s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
            w = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYLINE)
            w.field("ID", "N", 10)
            w.field("WATER_TYPE", "C", 50)
            w.field("NAME", "C", 100)
            for i, item in enumerate(rivers_list, 1):
                w.line([_transform_pts(item["coords"])])
                w.record(i, item["type"], item["name"])
            w.close()
            zf.writestr("02_OSM_Rivers_Streams.shp", s_io.getvalue())
            zf.writestr("02_OSM_Rivers_Streams.shx", x_io.getvalue())
            zf.writestr("02_OSM_Rivers_Streams.dbf", d_io.getvalue())
            zf.writestr("02_OSM_Rivers_Streams.prj", prj_wkt.encode("utf-8"))
            zf.writestr("02_OSM_Rivers_Streams.cpg", b"UTF-8")

        if buildings_list:
            s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
            w = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYGON)
            w.field("ID", "N", 10)
            w.field("BLDG_TYPE", "C", 50)
            w.field("AREA_M2", "N", 12, 2)
            for i, item in enumerate(buildings_list, 1):
                ring = _transform_pts(item["coords"])
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                a_m2 = round(calc_wgs84_ring_area_m2(item["coords"]), 2)
                w.poly([ring])
                w.record(i, item["type"], a_m2)
            w.close()
            zf.writestr("03_OSM_Buildings_Polygon.shp", s_io.getvalue())
            zf.writestr("03_OSM_Buildings_Polygon.shx", x_io.getvalue())
            zf.writestr("03_OSM_Buildings_Polygon.dbf", d_io.getvalue())
            zf.writestr("03_OSM_Buildings_Polygon.prj", prj_wkt.encode("utf-8"))
            zf.writestr("03_OSM_Buildings_Polygon.cpg", b"UTF-8")

        if landuse_list:
            s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
            w = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYGON)
            w.field("ID", "N", 10)
            w.field("LANDUSE", "C", 50)
            w.field("AREA_HA", "N", 12, 4)
            for i, item in enumerate(landuse_list, 1):
                ring = _transform_pts(item["coords"])
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                a_ha = round(calc_wgs84_ring_area_m2(item["coords"]) / 10000.0, 4)
                w.poly([ring])
                w.record(i, item["type"], a_ha)
            w.close()
            zf.writestr("04_OSM_Landuse_Water_Polygon.shp", s_io.getvalue())
            zf.writestr("04_OSM_Landuse_Water_Polygon.shx", x_io.getvalue())
            zf.writestr("04_OSM_Landuse_Water_Polygon.dbf", d_io.getvalue())
            zf.writestr("04_OSM_Landuse_Water_Polygon.prj", prj_wkt.encode("utf-8"))
            zf.writestr("04_OSM_Landuse_Water_Polygon.cpg", b"UTF-8")

        if include_contours:
            _, elev_grid, _ = fetch_bbox_rgb_preview(
                west, south, east, north, zoom=15,
                provider_name="⛰️ AWS Terrarium DEM Elevation (ຂໍ້ມູນຄວາມສູງນ້ຳທະເລແທ້ m ASL + Hillshade & ສົ່ງອອກ DEM .TIF)",
                max_tiles_cap=36
            )
            if elev_grid is not None and elev_grid.size > 100:
                smooth_contours = generate_smooth_cartographic_contours(
                    elev_grid, west, south, east, north,
                    interval_m=contour_interval_m,
                    smooth_sigma=contour_smooth_sigma,
                    min_length_m=min_contour_len_m,
                    chaikin_iters=4
                )
                if smooth_contours:
                    s_io, x_io, d_io = io.BytesIO(), io.BytesIO(), io.BytesIO()
                    w_cnt = shapefile.Writer(shp=s_io, shx=x_io, dbf=d_io, shapeType=shapefile.POLYLINE)
                    w_cnt.field("ID", "N", 10)
                    w_cnt.field("ELEV_M", "N", 10, 1)
                    w_cnt.field("CONT_TYPE", "C", 15)
                    w_cnt.field("LENGTH_M", "N", 12, 1)
                    w_cnt.field("LABEL", "C", 20)

                    for cid_cnt, c_item in enumerate(smooth_contours, 1):
                        w_cnt.line([_transform_pts(c_item["coords_wgs"])])
                        w_cnt.record(
                            cid_cnt,
                            c_item["elev_m"],
                            c_item["type"],
                            c_item["length_m"],
                            f"{int(c_item['elev_m'])}m"
                        )
                    w_cnt.close()
                    contours_count = len(smooth_contours)
                    zf.writestr(f"05_Smooth_Contours_{contour_interval_m}m.shp", s_io.getvalue())
                    zf.writestr(f"05_Smooth_Contours_{contour_interval_m}m.shx", x_io.getvalue())
                    zf.writestr(f"05_Smooth_Contours_{contour_interval_m}m.dbf", d_io.getvalue())
                    zf.writestr(f"05_Smooth_Contours_{contour_interval_m}m.prj", prj_wkt.encode("utf-8"))
                    zf.writestr(f"05_Smooth_Contours_{contour_interval_m}m.cpg", b"UTF-8")

    return zip_buf.getvalue(), {
        "roads": len(roads_list),
        "rivers": len(rivers_list),
        "buildings": len(buildings_list),
        "landuse": len(landuse_list),
        "contours": contours_count
    }


# ==============================================================================
# 9. ແຖບເຄື່ອງມືດ້ານຊ້າຍ (SIDEBAR: ຄົ້ນຫາອັດສະລິຍະຄ້າຍ GOOGLE MAPS & ນຳເຂົ້າຂອບເຂດບ້ານ)
# ==============================================================================
with st.sidebar:
    st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0f172a,#0369a1);padding:10px 12px;border-radius:12px;color:white;margin-bottom:12px;border:1px solid #38bdf8;display:flex;align-items:center;gap:10px;">
            <img src="{banner_bg_src}" style="width:46px;height:46px;border-radius:10px;object-fit:cover;border:1.5px solid #facc15;" />
            <div style="line-height:1.3;">
                <div style="font-weight:800;color:#facc15;font-size:13px;">👨‍💻 {DEVELOPER_NAME}</div>
                <div style="font-size:12px;color:#e0f2fe;">📞 ເບີໂທ: {DEVELOPER_PHONE}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🧭 1. ຄົ້ນຫາບ້ານ / ໂດດໄປຫາພິກັດ")
    st.markdown('<div class="gmap-search-box">', unsafe_allow_html=True)
    search_place = st.text_input(
        "🔍 ພິມຊື່ບ້ານ / ເມືອງ / ແຂວງ / ພິກັດ (ຄ້າຍ Google Maps):",
        placeholder="ເຊັ່ນ: ຈຳປາ, ປາກເຊ, ສະຫວັນນະເຂດ, 16.55, 104.75...",
        key="gmap_search_input"
    )

    s_btn1, s_btn2 = st.columns([1.6, 1.0])
    with s_btn1:
        trigger_search = st.button("🔍 ຄົ້ນຫາລາຍຊື່ສະຖານທີ່", type="primary", use_container_width=True)
    with s_btn2:
        clear_search = st.button("✖️ ລ້າງໝຸດ", use_container_width=True)

    if clear_search:
        st.session_state["gmap_search_results"] = []
        st.session_state["gmap_last_query"] = ""
        st.session_state["gmap_selected_pin"] = None
        st.session_state["dl_map_cmd_counter"] += 1
        st.rerun()

    if search_place.strip() and (trigger_search or search_place.strip() != st.session_state.get("gmap_last_query", "")):
        st.session_state["gmap_last_query"] = search_place.strip()
        with st.spinner(f"🔎 ກຳລັງຄົ້ນຫາ '{search_place.strip()}'..."):
            found_places = search_all_places_with_local_boundaries(search_place.strip())
            st.session_state["gmap_search_results"] = found_places
            if found_places:
                jump_to_selected_search_place(found_places[0])
                st.rerun()
            else:
                st.warning("⚠️ ບໍ່ພົບຊື່ສະຖານທີ່ນີ້! ລອງພິມຊື່ເມືອງ/ແຂວງ ຫຼື ພາສາອັງກິດ.")

    if st.session_state.get("gmap_search_results"):
        res_list = st.session_state["gmap_search_results"]
        st.caption(f"✅ ພົບ **{len(res_list)} ສະຖານທີ່** ທີ່ກົງກັບ `{st.session_state.get('gmap_last_query', '')}` (ຄລິກເລືອກເພື່ອບິນໄປຫາທັນທີ):")

        selected_idx = st.selectbox(
            "📍 ເລືອກສະຖານທີ່ຈາກລາຍການທີ່ພົບ:",
            options=list(range(len(res_list))),
            format_func=lambda i: f"{res_list[i]['title']} — {res_list[i]['subtitle']}",
            key="gmap_suggestion_selectbox"
        )

        if st.button("🚀 ບິນໄປຫາຈຸດທີ່ເລືອກນີ້ທັນທີ!", type="primary", use_container_width=True):
            jump_to_selected_search_place(res_list[selected_idx])
            st.rerun()

        st.markdown("**⚡ ຄລິກດ່ວນເພື່ອໄປຫາຈຸດທີ່ຕ້ອງການ:**")
        for idx_q, item_q in enumerate(res_list[:5]):
            btn_lbl = f"{item_q['title']} ({item_q['subtitle'][:28]}...)" if len(item_q["subtitle"]) > 28 else f"{item_q['title']} ({item_q['subtitle']})"
            if st.button(btn_lbl, key=f"quick_jump_btn_{idx_q}", use_container_width=True):
                jump_to_selected_search_place(item_q)
                st.rerun()

    if st.session_state.get("gmap_selected_pin"):
        pin = st.session_state["gmap_selected_pin"]
        p_e, p_n = lonlat_to_utm48n(pin["lon"], pin["lat"])
        st.success(
            f"📍 **ຈຸດທີ່ປັກໝຸດປັດຈຸບັນ:** {pin['title']}\n\n"
            f"🌐 **Lat/Lon:** `{pin['lat']:.6f}, {pin['lon']:.6f}`\n\n"
            f"🧭 **UTM 48N:** `E {p_e:,.1f}, N {p_n:,.1f}`"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("📍 ໂດດໄປຫາພິກັດ UTM 48N ຫຼື Lat/Lon"):
        coord_mode_in = st.radio("ລະບົບພິກັດ:", ["UTM Zone 48N (ແມັດ)", "WGS84 (Lat, Lon)"], horizontal=True)
        if "UTM" in coord_mode_in:
            u_east = st.number_input("Easting (X):", value=566373.0, step=500.0)
            u_north = st.number_input("Northing (Y):", value=1859587.0, step=500.0)
            if st.button("🎯 ໄປຫາພິກັດ UTM", use_container_width=True):
                lon_j, lat_j = utm48n_to_lonlat(u_east, u_north)
                jump_to_selected_search_place({
                    "title": f"📍 ພິກັດ UTM: E={u_east:,.0f}, N={u_north:,.0f}",
                    "subtitle": f"WGS84: {lat_j:.6f}, {lon_j:.6f}",
                    "lat": lat_j, "lon": lon_j, "zoom": 16
                })
                st.rerun()
        else:
            w_lat = st.number_input("Latitude (ເສັ້ນຂະໜານ):", value=16.7225, format="%.6f")
            w_lon = st.number_input("Longitude (ເສັ້ນແວງ):", value=105.6650, format="%.6f")
            if st.button("🎯 ໄປຫາພິກັດ Lat/Lon", use_container_width=True):
                jump_to_selected_search_place({
                    "title": f"📍 ພິກັດ WGS84: {w_lat:.6f}, {w_lon:.6f}",
                    "subtitle": "ພິກັດ Lat/Lon ໂດຍກົງ",
                    "lat": w_lat, "lon": w_lon, "zoom": 16
                })
                st.rerun()

    st.divider()
    st.markdown("### 📂 2. ນຳເຂົ້າຂອບເຂດບ້ານ (.SHP / .KML)")
    up_bound = st.file_uploader("ອັບໂຫຼດ .zip (Shapefile), .shp, .kml, .geojson:", type=["zip", "shp", "kml", "geojson"])
    if up_bound is not None:
        sig = f"{up_bound.name}_{up_bound.size}"
        if st.session_state.get("last_b_sig") != sig:
            raw_b = up_bound.getvalue()
            nm_low = up_bound.name.lower()
            if nm_low.endswith(".kml"):
                feats, f_names = parse_kml_to_village_features(raw_b)
            elif nm_low.endswith(".geojson") or nm_low.endswith(".json"):
                feats, f_names = parse_geojson_to_village_features(raw_b)
            else:
                feats, f_names = parse_shapefile_to_village_features(raw_b, is_zip=nm_low.endswith(".zip"))
            if feats:
                st.session_state["last_b_sig"] = sig
                st.session_state["boundary_features"] = feats
                st.session_state["boundary_fields"] = f_names
                st.session_state["village_name_field"] = f_names[0]
                st.session_state["boundary_name"] = up_bound.name
                update_active_village_selection([0])
                st.rerun()

    if st.button("📂 ເລືອກໄຟລ໌ .SHP / .KML ຈາກຄອມ", use_container_width=True):
        picked_b = pick_file_native_windows("ເລືອກໄຟລ໌ຂອບເຂດ", [("Boundary (*.shp;*.kml;*.zip;*.geojson)", "*.shp *.kml *.zip *.geojson")])
        if picked_b and os.path.isfile(picked_b):
            with open(picked_b, "rb") as f:
                raw_b = f.read()
            nm_low = picked_b.lower()
            if nm_low.endswith(".kml"):
                feats, f_names = parse_kml_to_village_features(raw_b)
            elif nm_low.endswith(".geojson"):
                feats, f_names = parse_geojson_to_village_features(raw_b)
            else:
                feats, f_names = parse_shapefile_to_village_features(picked_b if nm_low.endswith(".shp") else raw_b, is_zip=nm_low.endswith(".zip"))
            if feats:
                st.session_state["boundary_features"] = feats
                st.session_state["boundary_fields"] = f_names
                st.session_state["village_name_field"] = f_names[0]
                st.session_state["boundary_name"] = os.path.basename(picked_b)
                update_active_village_selection([0])
                st.rerun()

    if st.session_state["boundary_features"]:
        feats_list = st.session_state["boundary_features"]
        f_opts = st.session_state.get("boundary_fields", ["NAME"])
        f_field = st.selectbox("ຖັນຊື່ບ້ານ (Attribute Field):", options=f_opts, index=0)
        st.session_state["village_name_field"] = f_field
        sel_v = st.multiselect(
            f"🏘️ ເລືອກບ້ານທີ່ຕ້ອງການ ({len(feats_list)} ຂອບເຂດ):",
            options=[f["idx"] for f in feats_list],
            default=st.session_state.get("selected_village_indices", [0]),
            format_func=lambda idx: f"🏘️ {feats_list[idx]['attrs'].get(f_field, f'#{idx+1}')}"
        )
        if sel_v and sel_v != st.session_state.get("selected_village_indices"):
            update_active_village_selection(sel_v)
            st.rerun()

        if st.button("🗑️ ລ້າງຂອບເຂດບ້ານອອກ", use_container_width=True):
            st.session_state["boundary_features"] = []
            st.session_state["boundary_polygons_wgs84"] = []
            st.session_state["dl_map_cmd_counter"] += 1
            st.rerun()

    st.divider()
    cur_ram = enforce_ram_guard()
    st.caption(f"🛡️ ສະຖານະແຮມ: **{cur_ram} GB** / {MAX_RAM_LIMIT_GB} GB | CPU: {FAST_THREADS} Threads")


# ==============================================================================
# 10. ກ່ອງສ້າງຕາໜ່າງ INDEX ແຜນທີ່ໝົດປະເທດລາວແບບອອນໄລ (5x5 km, 10x10 km, 20x20 km...)
# ==============================================================================
with st.expander("🗺️ ສ້າງຕາໜ່າງ Index ແຜນທີ່ອອນໄລ ໝົດປະເທດລາວ ຫຼື ຕາມຂອບເຂດ (5×5 km, 10×10 km, 20×20 km, 50×50 km...)", expanded=True):
    st.markdown('<div class="index-grid-box">', unsafe_allow_html=True)
    ix_c1, ix_c2, ix_c3, ix_c4 = st.columns([1.4, 1.3, 1.3, 1.2])
    with ix_c1:
        idx_scope_choice = st.selectbox(
            "🌍 1. ຂອບເຂດການສ້າງຕາໜ່າງ Index:",
            options=[
                ("laos_national", "🇱🇦 ໝົດປະເທດລາວ (All Laos National Index)"),
                ("custom_boundary", "🏘️ ຕາມຂອບເຂດບ້ານ/ເມືອງ ທີ່ນຳເຂົ້າ (.SHP/.KML)"),
                ("current_view", "🖥️ ຕາມຂອບເຂດໜ້າຈໍແຜນທີ່ປັດຈຸບັນ")
            ],
            index=0,
            format_func=lambda x: x[1]
        )
    with ix_c2:
        idx_size_km = st.selectbox(
            "📏 2. ຂະໜາດຕາໜ່າງ Index (ກິໂລແມັດ):",
            options=[1, 2, 5, 10, 20, 25, 50],
            index=3,
            format_func=lambda km: f"📐 ຂະໜາດ {km} × {km} ກິໂລແມັດ ({km*km:,} km²/ຫ້ອງ)"
        )
    with ix_c3:
        st.write("")
        if st.button(f"⚡ ສ້າງຕາໜ່າງ Index ({idx_size_km}×{idx_size_km} km) ດຽວນີ້!", type="primary", use_container_width=True):
            with st.spinner(f"🗺️ ກຳລັງສ້າງຕາໜ່າງ Index {idx_size_km}×{idx_size_km} km..."):
                cells_gen = generate_utm_index_grid_cells(
                    scope_mode=idx_scope_choice[0],
                    grid_size_km=float(idx_size_km),
                    custom_rings_wgs84=st.session_state.get("boundary_polygons_wgs84"),
                    custom_bbox_wgs84=st.session_state.get("geo_bounds")
                )
                st.session_state["index_grid_cells"] = cells_gen
                st.session_state["index_grid_size_km"] = idx_size_km
                st.session_state["selected_index_sheet_codes"] = []
                if idx_scope_choice[0] == "laos_national":
                    st.session_state["map_init_center"] = [18.25, 103.85]
                    st.session_state["map_init_zoom"] = 7
                st.session_state["dl_map_cmd_counter"] += 1
                st.rerun()
    with ix_c4:
        st.write("")
        st.session_state["show_index_grid_on_map"] = st.checkbox("👁️ ສະແດງຕາໜ່າງເທິງແຜນທີ່", value=st.session_state["show_index_grid_on_map"])
        if st.session_state["index_grid_cells"]:
            if st.button("🗑️ ລ້າງຕາໜ່າງ Index", use_container_width=True):
                st.session_state["index_grid_cells"] = []
                st.session_state["selected_index_sheet_codes"] = []
                st.session_state["dl_map_cmd_counter"] += 1
                st.rerun()

    if st.session_state["index_grid_cells"]:
        grid_cells = st.session_state["index_grid_cells"]
        sz_cur = st.session_state["index_grid_size_km"]
        st.success(f"✅ ສ້າງຕາໜ່າງ Index ຂະໜາດ **{sz_cur}×{sz_cur} ກິໂລແມັດ** ສຳເລັດແລ້ວ! ຈຳນວນທັງໝົດ: **{len(grid_cells):,} ຫ້ອງແຜນທີ່ (Sheets)** — ສາມາດເລືອກຫ້ອງ Index ລຸ່ມນີ້ເພື່ອຊູມໄປຫາ ແລະ ດາວໂຫຼດພາບດາວທຽມຕາມຫ້ອງ Index ໄດ້ທັນທີ ຫຼື ດາວໂຫຼດຕາໜ່າງທັງໝົດເປັນ Shapefile (.ZIP) / .KML!")

        ig_col1, ig_col2, ig_col3 = st.columns([2.2, 1.3, 1.3])
        with ig_col1:
            sheet_map = {c["sheet_code"]: c for c in grid_cells}
            sel_codes = st.multiselect(
                f"🎯 ເລືອກລະຫັດຫ້ອງ Index (Sheet Code) ເພື່ອຊູມຫາ ແລະ ຕັດດາວໂຫຼດພາບດາວທຽມສະເພາະຫ້ອງ ({len(grid_cells):,} ຫ້ອງ):",
                options=list(sheet_map.keys()),
                default=st.session_state.get("selected_index_sheet_codes", []),
                format_func=lambda code: f"🗂️ {code} ({sheet_map[code]['utm_code']} | {sheet_map[code]['size_km']}x{sheet_map[code]['size_km']} km)"
            )
            if sel_codes != st.session_state.get("selected_index_sheet_codes", []):
                st.session_state["selected_index_sheet_codes"] = sel_codes
                if sel_codes:
                    sel_rings = [sheet_map[c]["ring_wgs84"] for c in sel_codes if c in sheet_map]
                    st.session_state["boundary_polygons_wgs84"] = sel_rings
                    nb = compute_bbox_from_polygons(sel_rings, buffer_pct=0.02)
                    st.session_state["geo_bounds"] = nb
                    st.session_state["map_init_center"] = [(nb[1] + nb[3]) / 2.0, (nb[0] + nb[2]) / 2.0]
                    st.session_state["map_init_zoom"] = 13 if sz_cur >= 10 else 14
                    st.session_state["save_filename"] = f"sat_{sel_codes[0]}" if len(sel_codes) == 1 else f"sat_{sel_codes[0]}_{len(sel_codes)}sheets"
                    st.session_state["dl_map_cmd_counter"] += 1
                    st.rerun()

        with ig_col2:
            st.write("")
            st.download_button(
                f"📦 ດາວໂຫຼດ Index ({len(grid_cells):,} ຫ້ອງ) ເປັນ Shapefile (.ZIP)",
                data=export_index_grid_shapefile_zip(grid_cells, coord_sys="UTM48N"),
                file_name=f"Laos_Index_Grid_{sz_cur}x{sz_cur}km_UTM48N.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
        with ig_col3:
            st.write("")
            st.download_button(
                f"🌍 ດາວໂຫຼດ Index ({len(grid_cells):,} ຫ້ອງ) ເປັນ Google Earth (.KML)",
                data=export_index_grid_kml_bytes(grid_cells),
                file_name=f"Laos_Index_Grid_{sz_cur}x{sz_cur}km.kml",
                mime="application/vnd.google-earth.kml+xml",
                use_container_width=True
            )
    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# 11. ໜ້າຈໍຫຼັກ: ຕັ້ງຄ່າແຫຼ່ງພາບຖ່າຍດາວທຽມ & ໂຟນເດີດາວໂຫຼດ
# ==============================================================================
with st.container(border=True):
    cat_col, prov_col = st.columns([1.4, 2.6])
    with cat_col:
        selected_cat = st.selectbox(
            "🗂️ 1. ໝວດໝູ່ພາບຖ່າຍດາວທຽມ & ຂໍ້ມູນ GIS ຟຣີ:",
            options=list(SATELLITE_CATEGORIES.keys()),
            index=0
        )
    with prov_col:
        dl_provider = st.selectbox(
            "🛰️ 2. ເລືອກແຫຼ່ງພາບຖ່າຍດາວທຽມ / ຊັ້ນຂໍ້ມູນ GIS (26+ ແຫຼ່ງຟຣີ):",
            options=SATELLITE_CATEGORIES[selected_cat],
            index=0
        )

    w_b, s_b, e_b, n_b = st.session_state["geo_bounds"]
    custom_dl_url = render_provider_date_controls(dl_provider, w_b, s_b, e_b, n_b, key_prefix="main_dl")

    st.divider()
    sv_c1, sv_c2, sv_c3, sv_c4 = st.columns([1.05, 1.95, 1.35, 1.85])
    with sv_c1:
        st.write("")
        if st.button("📂 ເລືອກໂຟນເດີເກັບ", use_container_width=True):
            picked_dir = pick_folder_native_windows()
            if picked_dir:
                st.session_state["save_folder"] = picked_dir
                st.rerun()
    with sv_c2:
        st.session_state["save_folder"] = st.text_input("📁 ໂຟນເດີເກັບໄຟລ໌ພາບ:", value=st.session_state["save_folder"])
    with sv_c3:
        st.session_state["save_filename"] = st.text_input("📝 ຊື່ໄຟລ໌ພາບ:", value=st.session_state["save_filename"])
    with sv_c4:
        st.session_state["save_format"] = st.selectbox(
            "🖼️ ນາມສະກຸນໄຟລ໌ GIS:",
            options=[".ecw", ".tif", ".jp2", ".jpg", ".png"],
            index=1 if st.session_state.get("save_format") == ".tif" else 0,
            format_func=lambda ext: {
                ".ecw": ".ECW (Enhanced Compression Wavelet + .eww/.prj ສຳລັບ GIS)",
                ".tif": ".TIF (BigTIFF GeoTIFF ຝັງພິກັດມາດຕະຖານ GIS ບໍ່ຈຳກັດຂະໜາດ)",
                ".jp2": ".JP2 (JPEG2000 Wavelet + ໄຟລ໌ພິກັດ .j2w/.prj)",
                ".jpg": ".JPG (ໄຟລ໌ເບົາ + ໄຟລ໌ພິກັດ .jgw/.prj)",
                ".png": ".PNG (ພາບຄົມຊັດ + ໄຟລ໌ພິກັດ .pgw/.prj)"
            }[ext]
        )

    dl_p1, dl_p2, dl_p3, dl_p4 = st.columns([1.6, 1.4, 1.6, 1.4])
    with dl_p1:
        max_z = SATELLITE_PROVIDERS[dl_provider].get("max_z", 22)
        dl_zoom = st.slider("🔍 ຄວາມລະອຽດພາບ (Zoom 13–22 ບໍ່ຈຳກັດ):", 13, max_z, min(20, max_z), 1)
    with dl_p2:
        tile_res_choice = st.selectbox(
            "💎 ຄວາມຄົມຊັດແຜ່ນພາບ (Tile DPI):",
            options=[512, 256],
            index=0,
            format_func=lambda px: "512x512 px (Ultra-HD 2x ແຈ້ງສຸດຂີດ)" if px == 512 else "256x256 px (ມາດຕະຖານ ໂຫຼດໄວ)"
        )
    with dl_p3:
        dl_crs_choice = st.selectbox(
            "🧭 ພິກັດຝັງໃນໄຟລ໌ພາບ:",
            options=["UTM48N", "WGS84"],
            index=0,
            format_func=lambda c: "UTM Zone 48N (EPSG:32648 - ແນະນຳສຳລັບລາວ)" if c == "UTM48N" else "WGS84 Lat/Lon (EPSG:4326)"
        )
    with dl_p4:
        st.write("")
        clip_dl_boundary = st.checkbox("✂️ ຕັດພາບຕາມຂອບເຂດບ້ານ / ຫ້ອງ Index / ກອບທີ່ຂີດ", value=True)
        overlay_hybrid_labels = st.checkbox("🏷️ ສະແດງຊື່ບ້ານ/ຖະໜົນຊ້ອນເທິງແຜນທີ່", value=False)


# ==============================================================================
# 12. ແຜນທີ່ອອນໄລ INTERACTIVE (ເບິ່ງອອນໄລ + ໝຸດຄົ້ນຫາ GOOGLE MAPS + ຕາໜ່າງ INDEX)
# ==============================================================================
m_dl = folium.Map(
    location=st.session_state["map_init_center"],
    zoom_start=st.session_state["map_init_zoom"],
    tiles=None, control_scale=True, max_zoom=22
)

p_info_dl = SATELLITE_PROVIDERS[dl_provider]
if custom_dl_url:
    folium.TileLayer(tiles=custom_dl_url, attr=dl_provider, name=dl_provider, max_zoom=22, max_native_zoom=p_info_dl["max_z"]).add_to(m_dl)
elif p_info_dl["type"] != "quadkey":
    folium.TileLayer(tiles=p_info_dl["url"], attr=dl_provider, name=dl_provider, max_zoom=22, max_native_zoom=p_info_dl["max_z"]).add_to(m_dl)
else:
    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}&scale=2", attr="Google", name="Google Ultra-HD", max_zoom=22, max_native_zoom=22).add_to(m_dl)

if overlay_hybrid_labels:
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=h&x={x}&y={y}&z={z}&scale=2",
        attr="Google Labels", name="ຊື່ບ້ານ ແລະ ເສັ້ນທາງ", overlay=True, opacity=0.85, max_zoom=22
    ).add_to(m_dl)

if st.session_state.get("gmap_selected_pin"):
    pin_info = st.session_state["gmap_selected_pin"]
    p_e, p_n = lonlat_to_utm48n(pin_info["lon"], pin_info["lat"])
    popup_html = f"""
    <div style="font-family:sans-serif; min-width:220px;">
        <b style="color:#0284c7; font-size:14px;">{escape(pin_info['title'])}</b><br>
        <span style="color:#475569; font-size:12px;">{escape(pin_info['subtitle'])}</span><hr style="margin:6px 0;">
        <b>WGS84:</b> {pin_info['lat']:.6f}, {pin_info['lon']:.6f}<br>
        <b>UTM 48N:</b> E {p_e:,.1f}, N {p_n:,.1f}
    </div>
    """
    folium.Marker(
        location=[pin_info["lat"], pin_info["lon"]],
        popup=folium.Popup(popup_html, max_width=300, show=True),
        tooltip=f"📍 {pin_info['title']}",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m_dl)
    folium.CircleMarker(
        location=[pin_info["lat"], pin_info["lon"]],
        radius=18,
        color="#ef4444",
        weight=3,
        fill=True,
        fill_color="#facc15",
        fill_opacity=0.25
    ).add_to(m_dl)

if st.session_state.get("show_index_grid_on_map") and st.session_state.get("index_grid_cells"):
    cells_to_draw = st.session_state["index_grid_cells"]
    if len(cells_to_draw) > 3500:
        vw, vs, ve, vn = st.session_state["geo_bounds"]
        in_view = [
            c for c in cells_to_draw
            if not (c["bbox_wgs84"][2] < vw - 0.5 or c["bbox_wgs84"][0] > ve + 0.5 or c["bbox_wgs84"][3] < vs - 0.5 or c["bbox_wgs84"][1] > vn + 0.5)
        ]
        cells_to_draw = in_view[:3500] if in_view else cells_to_draw[:3500]

    sel_set = set(st.session_state.get("selected_index_sheet_codes", []))
    geojson_feats = []
    for c in cells_to_draw:
        ring_closed = c["ring_wgs84"] + [c["ring_wgs84"][0]]
        is_sel = c["sheet_code"] in sel_set
        geojson_feats.append({
            "type": "Feature",
            "properties": {
                "sheet_code": c["sheet_code"],
                "utm_code": c["utm_code"],
                "size_str": f"{c['size_km']}x{c['size_km']} km ({c['area_km2']} km²)",
                "is_selected": is_sel
            },
            "geometry": {"type": "Polygon", "coordinates": [ring_closed]}
        })

    folium.GeoJson(
        {"type": "FeatureCollection", "features": geojson_feats},
        name="Map Index Grid",
        style_function=lambda feat: {
            "color": "#ff0055" if feat["properties"]["is_selected"] else "#facc15",
            "weight": 3.5 if feat["properties"]["is_selected"] else 1.4,
            "fillColor": "#ff0055" if feat["properties"]["is_selected"] else "#fef08a",
            "fillOpacity": 0.25 if feat["properties"]["is_selected"] else 0.04
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["sheet_code", "utm_code", "size_str"],
            aliases=["🗂️ ລະຫັດ Index:", "🧭 ພິກັດ UTM:", "📐 ຂະໜາດ:"],
            localize=True
        )
    ).add_to(m_dl)

for ring in st.session_state.get("boundary_polygons_wgs84", []):
    area_ha_b = round(calc_wgs84_ring_area_m2(ring) / 10000.0, 2)
    folium.Polygon(
        locations=[[pt[1], pt[0]] for pt in ring],
        color="#00e5ff", weight=3.5, fill=True, fill_color="#00e5ff", fill_opacity=0.12,
        tooltip=f"🏘️ ຂອບເຂດທີ່ເລືອກ ({area_ha_b:,.2f} ເຮັກຕາ)"
    ).add_to(m_dl)

Draw(
    export=True, filename="drawn_boundary.geojson", position="topleft",
    draw_options={
        "polyline": True, "circle": False, "marker": True, "circlemarker": False,
        "polygon": {"allowIntersection": False, "showArea": True, "shapeOptions": {"color": "#22c55e", "weight": 3, "fillOpacity": 0.15}},
        "rectangle": {"shapeOptions": {"color": "#22c55e", "weight": 3, "fillOpacity": 0.15}}
    },
    edit_options={"edit": True, "remove": True}
).add_to(m_dl)

Fullscreen(position="topright", title="ຂະຫຍາຍເຕັມຈໍ").add_to(m_dl)
MeasureControl(position="topright", primary_length_unit="meters", secondary_length_unit="kilometers", primary_area_unit="hectares").add_to(m_dl)
MousePosition(position="bottomright", separator=" | Lon: ", prefix="Lat: ").add_to(m_dl)
MiniMap(toggle_display=True, position="bottomleft").add_to(m_dl)

dl_map_data = st_folium(
    m_dl, width=None, height=620,
    returned_objects=["all_drawings", "last_active_drawing", "last_object_clicked", "bounds", "center", "zoom"],
    key=f"dl_map_{st.session_state['dl_map_cmd_counter']}"
)

if dl_map_data and dl_map_data.get("last_object_clicked") and st.session_state.get("index_grid_cells"):
    clk_pt = dl_map_data["last_object_clicked"]
    if "lat" in clk_pt and "lng" in clk_pt:
        c_lon, c_lat = float(clk_pt["lng"]), float(clk_pt["lat"])
        c_e, c_n = lonlat_to_utm48n(c_lon, c_lat)
        for cell in st.session_state["index_grid_cells"]:
            if cell["e_min"] <= c_e <= cell["e_max"] and cell["n_min"] <= c_n <= cell["n_max"]:
                code_hit = cell["sheet_code"]
                if st.session_state.get("last_clicked_index_code") != code_hit:
                    st.session_state["last_clicked_index_code"] = code_hit
                    st.session_state["selected_index_sheet_codes"] = [code_hit]
                    st.session_state["boundary_polygons_wgs84"] = [cell["ring_wgs84"]]
                    st.session_state["geo_bounds"] = cell["bbox_wgs84"]
                    st.session_state["save_filename"] = f"sat_{code_hit}"
                    st.rerun()
                break


# ==============================================================================
# 13. ຄຳນວນຂະໜາດພາບແທ້ 100% & ປຸ່ມດາວໂຫຼດພາບດາວທຽມ + ຂໍ້ມູນ GIS ຟຣີ
# ==============================================================================
drawn_dl_rings = extract_drawn_rings_from_map_data(dl_map_data)
active_clip_polys = drawn_dl_rings if drawn_dl_rings else (st.session_state["boundary_polygons_wgs84"] if st.session_state["boundary_polygons_wgs84"] else None)

if active_clip_polys:
    target_dl_bbox = compute_bbox_from_polygons(active_clip_polys, buffer_pct=0.01)
    total_poly_ha = sum(calc_wgs84_ring_area_m2(r) for r in active_clip_polys) / 10000.0
    scope_txt = f"ຕາມຂອບເຂດ Polygon / ຫ້ອງ Index ທີ່ເລືອກ ({len(active_clip_polys)} ວົງ | ເນື້ອທີ່ລວມ: {total_poly_ha:,.2f} ເຮັກຕາ)"
else:
    target_dl_bbox = st.session_state["geo_bounds"]
    if dl_map_data and dl_map_data.get("bounds"):
        b = dl_map_data["bounds"]
        sw, ne = b.get("_southWest", {}), b.get("_northEast", {})
        if "lng" in sw and "lat" in sw and "lng" in ne and "lat" in ne:
            target_dl_bbox = (float(sw["lng"]), float(sw["lat"]), float(ne["lng"]), float(ne["lat"]))
    scope_txt = "ຕາມກອບໜ້າຈໍແຜນທີ່ປັດຈຸບັນ (ສາມາດຄລິກເລືອກຫ້ອງ Index ຫຼື ຂີດກອບ ⬛ ເທິງແຜນທີ່ເພື່ອເລືອກຂອບເຂດສະເພາະໄດ້)"

tw, ts, te, tn = target_dl_bbox
grid_specs = calculate_download_grid_specs(tw, ts, te, tn, dl_zoom, tile_px=tile_res_choice)

full_dl_save_path = os.path.join(
    st.session_state["save_folder"].strip(),
    st.session_state["save_filename"].strip() + st.session_state["save_format"]
).replace("\\", "/")

st.markdown(f"""
    <div class="spec-card">
        <span class="metric-pill">🔓 UNLIMITED NATIVE PIXEL</span>
        <b>ຂອບເຂດດາວໂຫຼດ:</b> {scope_txt}<br>
        📐 <b>ຂະໜາດພາບແທ້ 100%:</b> <span style="color:#0284c7; font-weight:800;">{grid_specs['exact_w']:,} x {grid_specs['exact_h']:,} ພິກເຊວ</span> &nbsp;|&nbsp;
        🧩 <b>ຈຳນວນແຜ່ນພາບ:</b> <b>{grid_specs['total_tiles']:,} ແຜ່ນ</b> ({grid_specs['nx']}x{grid_specs['ny']}) &nbsp;|&nbsp;
        🔍 <b>ຄວາມລະອຽດໜ້າດິນ (GSD):</b> <span style="color:#0d9488; font-weight:800;">{grid_specs['gsd_m']*100:.1f} cm/px ({grid_specs['gsd_m']} m/px)</span><br>
        💾 <b>ຂະໜາດໄຟລ໌ໂດຍປະມານ:</b> GeoTIFF ~<b>{grid_specs['est_tif_mb']:,} MB</b> • ECW ~<b>{grid_specs['est_ecw_mb']:,} MB</b> &nbsp;➔&nbsp; <b>ໄຟລ໌ປາຍທາງ:</b> <code>{full_dl_save_path}</code>
    </div>
""", unsafe_allow_html=True)

btn_col1, btn_col2, btn_col3 = st.columns([1.6, 1.2, 1.3])
with btn_col1:
    if st.button(f"💾 1. ເລີ່ມດາວໂຫຼດພາບດາວທຽມຄວາມລະອຽດສູງສຸດ ({st.session_state['save_format'].upper()} - ບໍ່ຈຳກັດຂະໜາດ)", type="primary", use_container_width=True):
        dl_mgr.start_download(
            tw, ts, te, tn, dl_zoom, dl_provider,
            out_file_path=full_dl_save_path,
            clip_polygons_wgs84=active_clip_polys if clip_dl_boundary else None,
            custom_tile_tpl=custom_dl_url,
            tile_px=tile_res_choice,
            coord_sys=dl_crs_choice
        )
        st.rerun()

with btn_col2:
    if st.button("👁️ 2. ເບິ່ງຕົວຢ່າງພາບຕັດຂອບເຂດ (Quick Preview)", use_container_width=True):
        with st.spinner("🛰️ ກຳລັງດຶງພາບຕົວຢ່າງ..."):
            rgb_prev, _, got_z = fetch_bbox_rgb_preview(tw, ts, te, tn, dl_zoom, dl_provider, custom_tile_tpl=custom_dl_url, max_tiles_cap=49)
            if clip_dl_boundary and active_clip_polys:
                bh, bw = rgb_prev.shape[:2]
                c_mask = np.zeros((bh, bw), dtype=np.uint8)
                for ring in active_clip_polys:
                    pts = [[int(round(((lon - tw) / max(1e-9, te - tw)) * bw)), int(round(((tn - lat) / max(1e-9, tn - ts)) * bh))] for lon, lat in ring]
                    if len(pts) >= 3:
                        cv2.fillPoly(c_mask, [np.array(pts, dtype=np.int32)], 255)
                rgb_prev = cv2.bitwise_and(rgb_prev, rgb_prev, mask=c_mask)
            st.session_state["preview_rgb"] = rgb_prev
            st.session_state["preview_caption"] = f"ພາບຕົວຢ່າງຈາກ {dl_provider} (Preview Zoom {got_z} | ຂະໜາດຕົວຢ່າງ: {rgb_prev.shape[1]}x{rgb_prev.shape[0]} px)"

with btn_col3:
    if active_clip_polys:
        kml_bound_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Selected_Boundary</name>']
        for idx_r, r_wgs in enumerate(active_clip_polys, 1):
            c_str = " ".join([f"{lon:.7f},{lat:.7f},0" for lon, lat in r_wgs] + [f"{r_wgs[0][0]:.7f},{r_wgs[0][1]:.7f},0"])
            kml_bound_lines.append(f'<Placemark><name>Boundary #{idx_r}</name><Style><LineStyle><color>ff00ffff</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style><Polygon><outerBoundaryIs><LinearRing><coordinates>{c_str}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>')
        kml_bound_lines.append('</Document></kml>')
        st.download_button(
            "📐 3. ດາວໂຫຼດເສັ້ນຂອບເຂດທີ່ເລືອກ (.KML)",
            data="\n".join(kml_bound_lines).encode("utf-8"),
            file_name=f"{st.session_state['save_filename']}_boundary.kml",
            mime="application/vnd.google-earth.kml+xml",
            use_container_width=True
        )
    else:
        st.button("📐 3. ຂີດກອບເທິງແຜນທີ່ເພື່ອບັນທຶກ .KML", disabled=True, use_container_width=True)


if dl_mgr.status != "idle":
    st.markdown('<div class="dl-monitor-card">', unsafe_allow_html=True)
    st.markdown("##### 🛰️ ສະຖານະການດາວໂຫຼດພາບດາວທຽມຄວາມລະອຽດສູງສຸດ (Unlimited Background Downloader)")
    if dl_mgr.status in ("running", "paused"):
        st.progress(min(100, max(0, int(dl_mgr.pct))), text=dl_mgr.message)
        b_c1, b_c2, b_c3 = st.columns(3)
        with b_c1:
            if dl_mgr.status == "running":
                if st.button("⏸️ ຢຸດຊົ່ວຄາວ (Pause)", use_container_width=True):
                    dl_mgr.pause()
                    st.rerun()
            else:
                if st.button("▶️ ດາວໂຫຼດຕໍ່ (Resume)", type="primary", use_container_width=True):
                    dl_mgr.resume()
                    st.rerun()
        with b_c2:
            if st.button("🛑 ຍົກເລີກ (Cancel)", use_container_width=True):
                dl_mgr.cancel()
                time.sleep(0.3)
                st.rerun()
        with b_c3:
            if st.button("🔄 ອັບເດດເປີເຊັນດຽວນີ້", use_container_width=True):
                st.rerun()
        if dl_mgr.status == "running":
            time.sleep(1.0)
            st.rerun()
    elif dl_mgr.status == "completed":
        st.progress(100, text=dl_mgr.message)
        ok1, ok2 = st.columns(2)
        with ok1:
            if st.button("📂 ເປີດໂຟນເດີເກັບໄຟລ໌ພາບໃນ Windows Explorer", type="primary", use_container_width=True):
                folder_open = os.path.dirname(dl_mgr.out_file_path)
                if os.path.exists(folder_open):
                    try:
                        os.startfile(folder_open)
                    except Exception:
                        pass
        with ok2:
            if st.button("✖️ ປິດແຈ້ງເຕືອນ", use_container_width=True):
                dl_mgr.status = "idle"
                st.rerun()
    else:
        st.warning(dl_mgr.message)
        if st.button("✖️ ລ້າງແຈ້ງເຕືອນ", use_container_width=True):
            dl_mgr.status = "idle"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.get("preview_rgb") is not None:
    with st.expander("🖼️ ພາບຕົວຢ່າງທີ່ຕັດຕາມຂອບເຂດ (Quick Preview)", expanded=True):
        st.image(st.session_state["preview_rgb"], caption=st.session_state["preview_caption"], use_container_width=True)
        if st.button("✖️ ປິດພາບຕົວຢ່າງ"):
            st.session_state["preview_rgb"] = None
            st.rerun()


# ==============================================================================
# 14. ດາວໂຫຼດຂໍ້ມູນ VECTOR GIS & ເສັ້ນລະດັບຄວາມສູງໂຄ້ງມົນ (SMOOTH CONTOURS) + ແປງໄຟລ໌ .ECW
# ==============================================================================
st.divider()
g_col1, g_col2 = st.columns(2)

with g_col1:
    with st.container(border=True):
        st.markdown("#### 〰️ ດາວໂຫຼດເສັ້ນລະດັບຄວາມສູງໂຄ້ງມົນ (Smooth Contours) & Vector GIS ຟຣີ (.ZIP)")
        st.caption("ສ້າງເສັ້ນລະດັບຄວາມສູງທີ່ **ໂຄ້ງມົນລຽບງາມ (Chaikin Spline Curve)** ບໍ່ເປັນລ່ຽມຫຍັກ ແລະ **ບໍ່ມີເສັ້ນຕິດຂອບຮູບສີ່เหล່ຽມ** ພ້ອມແຍກເສັ້ນຫຼັກ (`INDEX`) ແລະ ເສັ້ນຍ່ອຍ (`INTERMED`) + ດຶງເສັ້ນທາງ, ຫ້ວຍນ້ຳ, ອາຄານ ຈາກ OpenStreetMap!")

        fg1, fg2 = st.columns(2)
        with fg1:
            inc_cnt = st.checkbox("⛰️ ສ້າງເສັ້ນລະດັບຄວາມສູງໂຄ້ງມົນ (Smooth Contours)", value=True)
            cnt_step = st.selectbox("ໄລຍະຫ່າງເສັ້ນລະດັບ (Contour Interval):", [2, 5, 10, 20, 25, 50], index=2, format_func=lambda m: f"ທຸກໆ {m} ແມັດ (ເສັ້ນຫຼັກທຸກໆ {m*5}m)")
        with fg2:
            cnt_smooth = st.slider("〰️ ລະດັບຄວາມໂຄ້ງມົນລຽບຂອງເສັ້ນ (Smoothness):", 1.5, 5.0, 2.8, 0.2)
            cnt_min_len = st.slider("🧹 ຕັດວົງຂີ້ເຫຍື້ອນ້ອຍໆອອກ (ຄວາມຍາວຂັ້ນຕ່ຳ m):", 50, 500, 160, 20)

        if st.button("📥 ດຶງເສັ້ນ Contour ໂຄ້ງມົນ & Vector GIS ຟຣີ ຕາມຂອບເຂດນີ້ທັນທີ!", type="primary", use_container_width=True):
            with st.spinner("🌍 ກຳລັງສ້າງເສັ້ນລະດັບຄວາມສູງໂຄ້ງມົນ (Smooth Spline Contours) ແລະ ດຶງຂໍ້ມູນ GIS..."):
                zip_bytes, counts_dict = fetch_free_osm_vector_gis_zip(
                    tw, ts, te, tn,
                    coord_sys=dl_crs_choice,
                    include_contours=inc_cnt,
                    contour_interval_m=cnt_step,
                    contour_smooth_sigma=cnt_smooth,
                    min_contour_len_m=float(cnt_min_len)
                )
                st.session_state["free_gis_zip_bytes"] = zip_bytes
                st.session_state["free_gis_zip_name"] = f"Smooth_Contours_{cnt_step}m_and_GIS_{st.session_state['save_filename']}_{dl_crs_choice}.zip"
                st.success(
                    f"✅ ສ້າງສຳເລັດ! ເສັ້ນ Contour ໂຄ້ງມົນ: **{counts_dict['contours']}** ເສັ້ນ | "
                    f"ເສັ້ນທາງ: **{counts_dict['roads']}** | ຫ້ວຍ/ແມ່ນ້ຳ: **{counts_dict['rivers']}** | "
                    f"ອາຄານ: **{counts_dict['buildings']}**"
                )

        if st.session_state.get("free_gis_zip_bytes"):
            st.download_button(
                f"📦 ບັນທຶກໄຟລ໌ {st.session_state['free_gis_zip_name']} ລົງຄອມ",
                data=st.session_state["free_gis_zip_bytes"],
                file_name=st.session_state["free_gis_zip_name"],
                mime="application/zip",
                use_container_width=True
            )

with g_col2:
    with st.container(border=True):
        st.markdown("#### 🔄 ເຄື່ອງມືແປງໄຟລ໌ພາບທີ່ມີຢູ່ແລ້ວ (.TIF / .JPG / .PNG) ➔ ເປັນໄຟລ໌ `.ECW`")
        st.caption("ສຳລັບແປງໄຟລ໌ພາບດາວທຽມ ຫຼື ພາບໂດຣນທີ່ມີຢູ່ໃນຄອມພິວເຕີ ໃຫ້ກາຍເປັນໄຟລ໌ `.ECW` ພ້ອມໄຟລ໌ພິກັດ `.eww`, `.prj` ແລະ `.aux.xml` ສຳລັບເປີດໃນ ArcMap / QGIS ຢ່າງໄວວາ.")

        cv1, cv2_col = st.columns([1.2, 2.2])
        with cv1:
            if st.button("📂 ເລືອກໄຟລ໌ພາບຕົ້ນສະບັບ", use_container_width=True):
                p_src = pick_file_native_windows("ເລືອກໄຟລ໌ພາບທີ່ຕ້ອງການແປງເປັນ .ECW", [("Images (*.tif;*.tiff;*.jpg;*.png)", "*.tif *.tiff *.jpg *.jpeg *.png")])
                if p_src:
                    st.session_state["ecw_conv_src"] = p_src.replace("\\", "/")
                    st.rerun()
        with cv2_col:
            src_conv_path = st.text_input("ໄຟລ໌ຕົ້ນສະບັບ:", value=st.session_state.get("ecw_conv_src", full_dl_save_path), label_visibility="collapsed")

        if st.button("⚡ ແປງເປັນໄຟລ໌ .ECW ພ້ອມພິກັດ GIS ທັນທີ", type="primary", use_container_width=True):
            if src_conv_path and os.path.isfile(src_conv_path):
                out_ecw = os.path.splitext(src_conv_path)[0] + ".ecw"
                with st.spinner(f"🔄 ກຳລັງແປງໄຟລ໌ເປັນ `{out_ecw}`..."):
                    w_c, h_c = 1000, 1000
                    bw_c, bs_c, be_c, bn_c = tw, ts, te, tn
                    if HAS_RASTERIO:
                        try:
                            with rasterio.open(src_conv_path) as src_ds:
                                w_c, h_c = src_ds.width, src_ds.height
                        except Exception:
                            pass
                    convert_raster_to_ecw_or_gis_wavelet(src_conv_path, out_ecw, bw_c, bs_c, be_c, bn_c, w_c, h_c, coord_sys=dl_crs_choice)
                    st.success(f"✅ ແປງໄຟລ໌ເປັນ `{out_ecw}` (ພ້ອມໄຟລ໌ພິກັດ `.eww` ແລະ `.prj`) ສຳເລັດຮຽບຮ້ອຍ!")
            else:
                st.warning("⚠️ ບໍ່ພົບໄຟລ໌ຕົ້ນສະບັບທີ່ລະບຸ! ກະລຸນາກົດເລືອກໄຟລ໌ກ່ອນ.")