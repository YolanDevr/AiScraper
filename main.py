import numpy as np
import streamlit as st
from googlesearch import search
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime
import hashlib
import os
import json
from PIL import Image
import base64
import urllib.request
from io import BytesIO
from ai_context_seo import AI_SEO_GUIDE

# 🔑 Gemini API-configuratie
genai.configure(api_key="AIzaSyAc4ZTDxosK4IkSu2MHWkkRQmStDm6mcmI")

# Streamlit instellingen + themakleuren
st.set_page_config(page_title="AI-SEO Toolkit", layout="wide")

st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-family: 'Open Sans', sans-serif;
            color: #1D1D1B;
        }
        h1 {
            font-weight: 800;
            color: #1D1D1B;
        }
        .stButton>button {
            background-color: #00C6B1;
            color: white;
            border: none;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #009E92;
        }
        .stRadio > div {
            gap: 1rem;
        }
        .css-1v3fvcr, .css-1dp5vir {
            background-color: #F3F3F3;
        }
    </style>
""", unsafe_allow_html=True)

# 🌟 The Fat Lady branding
logo_url = "https://thefatlady.be/wp-content/uploads/2021/12/logo.png"
with urllib.request.urlopen(logo_url) as response:
    logo = Image.open(BytesIO(response.read()))

with st.container():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.image(logo, width=100)
    with col2:
        st.markdown("""
        <h1 style='margin-bottom: 0;'>AI & SEO Zichtbaarheid</h1>
        <p style='margin-top: 0; color: #00C6B1;'>powered by The Fat Lady</p>
        """, unsafe_allow_html=True)

if "ai_historiek" not in st.session_state:
    st.session_state.ai_historiek = []

CACHE_DIR = "ai_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def cache_antwoord(prompt, tekst, modeltype, force_refresh=False):
    hash_input = prompt.strip() + tekst.strip() + modeltype
    hash_id = hashlib.sha256(hash_input.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, f"{hash_id}.json")

    if not force_refresh and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["antwoord"]

    try:
        modelnaam = "models/gemini-1.5-flash-latest" if modeltype == "flash" else "models/gemini-1.5-pro-latest"
        model = genai.GenerativeModel(
            modelnaam,
            system_instruction="Je bent een AI-SEO expert. Gebruik onderstaande gids als vaste leidraad voor analyses:\n" + AI_SEO_GUIDE
        )
        response = model.generate_content(prompt + "\n\n" + tekst)
        antwoord = response.text
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"antwoord": antwoord}, f)
        st.session_state.ai_historiek.append({
            "timestamp": datetime.now(), "prompt": prompt, "antwoord": antwoord
        })
        return antwoord
    except Exception as e:
        if "429" in str(e):
            st.error("🚫 AI-quota overschreden. Bekijk [quota info](https://ai.google.dev/gemini-api/docs/rate-limits).")
            return "⚠️ Quota bereikt – probeer later opnieuw."
        else:
            return f"⚠️ AI-fout: {e}"

def scrap_tekst_van_url(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        return f"[Fout bij ophalen]: {e}"

def get_cached_tekst(url, force_refresh=False):
    hash_id = hashlib.sha256(url.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, f"{hash_id}_tekst.json")

    if not force_refresh and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)["tekst"]

    tekst = scrap_tekst_van_url(url)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tekst": tekst}, f)
    return tekst

def analyseer_pagina(keyword, url):
    keyword = keyword.lower()
    resultaat = {
        "URL": url,
        "Keyword in titel": False,
        "Keyword in headings": False,
        "Keyword in body": False,
        "Aantal woorden": 0,
        "Titel": "N.v.t.",
        "Meta Titel": "Niet gevonden",
        "Meta Beschrijving": "Niet gevonden"
    }
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.title and soup.title.string:
            meta_titel = soup.title.string.strip()
            resultaat["Titel"] = meta_titel
            resultaat["Meta Titel"] = meta_titel
            resultaat["Keyword in titel"] = keyword in meta_titel.lower()

        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and description_tag.get("content"):
            resultaat["Meta Beschrijving"] = description_tag["content"].strip()

        headings = [h.get_text(strip=True).lower() for h in soup.find_all(["h1", "h2", "h3"])]
        resultaat["Keyword in headings"] = any(keyword in h for h in headings)

        body_text = soup.get_text(separator=" ", strip=True).lower()
        resultaat["Keyword in body"] = keyword in body_text
        resultaat["Aantal woorden"] = len(body_text.split())

    except Exception as e:
        resultaat["Titel"] = f"Fout: {e}"
    return resultaat

def gecombineerde_ai_analyse(zoekvraag, tekst):
    prompt = f"""
Analyseer onderstaande webtekst rond de zoekvraag: '{zoekvraag}'.

1. Wat is de kans dat deze pagina zichtbaar is in Gemini?
2. Simuleer of ChatGPT dit als een goed antwoord zou beschouwen.
3. Geef concrete optimalisatietips voor betere zichtbaarheid in Gemini.
4. Geef concrete optimalisatietips voor betere zichtbaarheid in ChatGPT.
5. Wat zijn mogelijke redenen waarom deze pagina NIET bovenaan staat in Google?
6. Zijn er structurele zwaktes in SEO (bv. ontbrekende headings, rommelige opbouw)?
7. Beoordeel de tone of voice.
8. Geef 2 concrete herschrijfsuggesties die de boodschap versterken.
9. Geef een eindscore van 0 tot 10 voor de algemene AI-vindbaarheid + tone of voice.
10. Analyseer de meta title en meta description.
11. Geef herschrijfsuggesties voor een betere meta title en meta description.
12. Vermeld of deze site expliciet of impliciet als bron kan opduiken in AI-antwoorden.
13. Geef een sentimentanalyse: positief, negatief of neutraal?
14. Haal de 3 kernboodschappen uit de tekst.
"""
    return cache_antwoord(prompt, tekst, modeltype="pro")

# Interface
keuze = st.sidebar.radio("📍 Kies een module", [
    "🔍 AI-rank Monitor",
    "🏑 SEO Concurrentievergelijker",
    "🧠 AI-SEO Expert Analyse"
])

if keuze == "🧠 AI-SEO Expert Analyse":
    st.subheader("🧠 Één krachtige AI-SEO Analyse")
    urls = st.text_area("🌐 Voer één of meerdere URL's in", "https://www.wittewoede.be/")
    keyword = st.text_input("🔑 Zoekwoord", "kunstenaarsstatuut")
    zoekvraag = st.text_input("❓ Typ een typische AI-zoekvraag", "Wat is het kunstenaarsstatuut?")
    if st.button("🔍 Start analyse"):
        urls = [u.strip() for u in urls.splitlines() if u.strip()]
        analyses = []
        for url in urls:
            st.markdown(f"---\n## 🌐 Analyse van {url}")
            tekst = get_cached_tekst(url)
            analyse = analyseer_pagina(keyword, url)
            analyses.append(analyse)
            st.markdown("### 📋 Basis SEO-analyse")
            for k, v in analyse.items():
                st.write(f"- **{k}**: {v}")

            st.markdown("### 🧠 AI-analyse per onderdeel")
            antwoord = gecombineerde_ai_analyse(zoekvraag, tekst)
            st.markdown(antwoord)

        if len(analyses) > 1:
            st.markdown("## 📈 SEO-vergelijking (radar chart)")
            def bereken_scores(pagina):
                return {
                    "Titel": 1 if pagina["Keyword in titel"] else 0,
                    "Headings": 1 if pagina["Keyword in headings"] else 0,
                    "Body": 1 if pagina["Keyword in body"] else 0,
                    "Woorden": min(pagina["Aantal woorden"] / 500, 1)
                }

            labels = ["Titel", "Headings", "Body", "Woorden"]
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist() + [0]
            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
            for pagina in analyses:
                scores = list(bereken_scores(pagina).values()) + [bereken_scores(pagina)["Titel"]]
                ax.plot(angles, scores, label=pagina["URL"])
                ax.fill(angles, scores, alpha=0.1)
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_thetagrids(np.degrees(angles[:-1]), labels)
            ax.set_ylim(0, 1)
            plt.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
            st.pyplot(fig)
