"""
╔══════════════════════════════════════════════════════════════╗
║           ORACLE MAHITA V34.1 — VERSION COMPLÈTE            ║
║           Cerveau I · OCR Optimisé · Interface Complète     ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import easyocr
import re
import json
import os
from difflib import get_close_matches
from PIL import Image, ImageEnhance
import numpy as np
import io
import math
from typing import List, Dict

# ── Import Cerveau I ─────────────────────────────────────
from moteur_cerveau1 import cerveau1 as oracle_brain

# ── Configuration ────────────────────────────────────────
st.set_page_config(page_title="Oracle Mahita V34.1", layout="wide", page_icon="🔮")

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
.main-header {
    text-align: center; padding: 28px; border: 5px solid #7FFFD4; border-radius: 20px;
    background: #0E1117; box-shadow: 0 0 35px #7FFFD4; margin-bottom: 20px;
}
.header-title {
    color: #FFF; font-size: 3.6em; font-weight: 900; text-transform: uppercase;
    letter-spacing: 6px; -webkit-text-stroke: 1.8px #7FFFD4; text-shadow: 0 0 20px #7FFFD4;
}
.prono-safe { border-left: 5px solid #00FF00; padding: 14px; background: rgba(0,255,0,0.08); border-radius: 8px; margin: 10px 0; }
.prono-risque { border-left: 5px solid #FFA500; padding: 14px; background: rgba(255,165,0,0.08); border-radius: 8px; margin: 10px 0; }
.prono-fun { border-left: 5px solid #FF4B4B; padding: 14px; background: rgba(255,75,75,0.08); border-radius: 8px; margin: 10px 0; }
.module-box { background: rgba(127,255,212,0.06); border: 1px solid #7FFFD4; border-radius: 10px; padding: 14px; margin: 10px 0; }
.alerte-oracle { color: #FFD700; font-style: italic; }
.alerte-danger { color: #FF4B4B; font-style: italic; }
.next-day-box { text-align: center; color: #7FFFD4; font-weight: bold; font-size: 1.3em; padding: 12px;
                background: rgba(127,255,212,0.12); border-radius: 10px; margin: 15px 0; }
</style>
""", unsafe_allow_html=True)

# ===================== UTILITAIRES =====================
def custom_notify(text: str, color: str = "#00FF00"):
    st.markdown(f"""
    <div style="padding:18px;border:3px solid {color};border-radius:12px;background:#0E1117;color:#FFF;
    text-align:center;font-weight:900;box-shadow:0 0 25px {color};margin:15px 0;font-size:1.25em;">
    {text}</div>""", unsafe_allow_html=True)

def get_standings(season_data: dict, teams_list: list) -> pd.DataFrame:
    stats = {t: {"MJ":0,"V":0,"N":0,"D":0,"BP":0,"BC":0,"Diff":0,"Pts":0} for t in teams_list}
    for data in season_data.values():
        for m in data.get("res", []):
            try:
                sh, sa = map(int, m['s'].replace('-',':').split(':'))
                h, a = m['h'], m['a']
                stats[h]["MJ"] += 1; stats[a]["MJ"] += 1
                stats[h]["BP"] += sh; stats[h]["BC"] += sa
                stats[a]["BP"] += sa; stats[a]["BC"] += sh
                if sh > sa:
                    stats[h]["V"] += 1; stats[h]["Pts"] += 3; stats[a]["D"] += 1
                elif sh < sa:
                    stats[a]["V"] += 1; stats[a]["Pts"] += 3; stats[h]["D"] += 1
                else:
                    stats[h]["N"] += 1; stats[h]["Pts"] += 1
                    stats[a]["N"] += 1; stats[a]["Pts"] += 1
            except: continue
    df = pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'Équipe'})
    df['Diff'] = df['BP'] - df['BC']
    df = df.sort_values(by=["Pts","Diff","BP"], ascending=False).reset_index(drop=True)
    df.insert(0, 'Rang', range(1, len(df)+1))
    return df

def get_forme_equipe(history: dict, saison: str, equipe: str, nb_matchs: int = 6) -> List[str]:
    resultats = []
    if saison not in history: return []
    journees = sorted(history[saison].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in reversed(journees):
        if len(resultats) >= nb_matchs: break
        for match in history[saison][jk].get("res", []):
            try:
                sh, sa = map(int, match["s"].replace("-", ":").split(":"))
                if match["h"] == equipe:
                    resultats.insert(0, "V" if sh > sa else ("N" if sh == sa else "D"))
                elif match["a"] == equipe:
                    resultats.insert(0, "V" if sa > sh else ("N" if sh == sa else "D"))
            except: continue
    return resultats[-nb_matchs:]

def get_serie_victoires(forme: List[str]) -> int:
    serie = 0
    for r in reversed(forme):
        if r == "V": serie += 1
        else: break
    return serie

def get_dernier_adversaire(history: dict, saison: str, equipe: str):
    if saison not in history: return None
    journees = sorted(history[saison].keys(), key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in reversed(journees):
        for match in history[saison][jk].get("res", []):
            if match.get("h") == equipe: return match.get("a")
            if match.get("a") == equipe: return match.get("h")
    return None

# ===================== PERSISTENCE =====================
DB_FILE = "oracle_history.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

if 'history' not in st.session_state:
    st.session_state['history'] = load_db()
    if not st.session_state['history']:
        st.session_state['history']["Saison 2026"] = {}

# ===================== OCR ENGINE =====================
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'fr'], gpu=False)

reader = load_ocr()

class OracleEngine:
    def __init__(self):
        self.teams_list = [
            "Leeds", "Brighton", "A. Villa", "Manchester Blue", "C. Palace",
            "Bournemouth", "Spurs", "Burnley", "West Ham", "Liverpool",
            "Fulham", "Newcastle", "Manchester Red", "Everton", "London Blues",
            "Wolverhampton", "Sunderland", "N. Forest", "London Reds", "Brentford"
        ]

    def clean_team(self, text: str):
        if not text: return None
        m = get_close_matches(text.strip(), self.teams_list, n=1, cutoff=0.35)
        return m[0] if m else None

engine = OracleEngine()

# ===================== OCR RÉSULTATS =====================
def preprocess_image_for_ocr(image_bytes):
    results = []
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    results.append(image_bytes)

    img2 = ImageEnhance.Contrast(img).enhance(2.8)
    img2 = ImageEnhance.Sharpness(img2).enhance(2.5)
    buf = io.BytesIO(); img2.save(buf, format='JPEG', quality=95)
    results.append(buf.getvalue())

    gray = np.array(img.convert("L"))
    thresh = int(gray.mean() * 0.92)
    bin_img = np.where(gray > thresh, 255, 0).astype(np.uint8)
    buf3 = io.BytesIO(); Image.fromarray(bin_img).save(buf3, format='JPEG', quality=95)
    results.append(buf3.getvalue())

    w, h = img.size
    img4 = img.resize((int(w * 1.65), int(h * 1.65)), Image.LANCZOS)
    img4 = ImageEnhance.Contrast(img4).enhance(2.4)
    buf4 = io.BytesIO(); img4.save(buf4, format='JPEG', quality=95)
    results.append(buf4.getvalue())

    return results

def ocr_resultats(image_bytes, debug=False):
    versions = preprocess_image_for_ocr(image_bytes)
    all_raw = []
    for i, ver in enumerate(versions):
        try:
            res = reader.readtext(ver, detail=1, paragraph=False, contrast_ths=0.25, adjust_contrast=0.7)
            if i == 3:
                res = [([[p[0]/1.65, p[1]/1.65] for p in bbox], text, prob) for bbox, text, prob in res]
            all_raw.extend(res)
        except: continue

    blocs = []
    seen = set()
    for bbox, text, prob in all_raw:
        text = text.strip()
        if prob < 0.20 or len(text) < 2: continue
        try:
            cx = (bbox[0][0] + bbox[2][0]) / 2
            cy = (bbox[0][1] + bbox[2][1]) / 2
        except: continue
        key = f"{text}_{int(cx/25)}_{int(cy/25)}"
        if key in seen: continue
        seen.add(key)
        blocs.append({'text': text, 'cx': cx, 'cy': cy})

    blocs.sort(key=lambda x: x['cy'])
    lines = []
    for b in blocs:
        placed = False
        for ln in lines:
            if abs(b['cy'] - ln.get('cy_mean', 0)) < 35:
                ln['blocs'].append(b)
                ln['cy_mean'] = sum(x['cy'] for x in ln['blocs']) / len(ln['blocs'])
                placed = True
                break
        if not placed:
            lines.append({'cy_mean': b['cy'], 'blocs': [b]})

    matches = []
    current = None
    W = Image.open(io.BytesIO(image_bytes)).size[0]
    mid_x = W * 0.48

    for line in lines:
        full = ' '.join(b['text'] for b in line['blocs'])
        bx = sorted(line['blocs'], key=lambda x: x['cx'])

        score = None
        for b in bx:
            t = re.sub(r'[^0-9:\-]', '', b['text'])
            m = re.match(r'^(\d{1,2})[:\-](\d{1,2})$', t)
            if m:
                score = {'val': f"{m.group(1)}:{m.group(2)}", 'cx': b['cx']}
                break

        mt_m = re.search(r'MT[:\s]*(\d)[:\-\.](\d)', full, re.IGNORECASE)
        mt = f"{mt_m.group(1)}:{mt_m.group(2)}" if mt_m else None

        teams_line = [b for b in bx if engine.clean_team(b['text'])]

        if score:
            dom = [t for t in teams_line if t['cx'] < score['cx'] - 40]
            ext = [t for t in teams_line if t['cx'] > score['cx'] + 40]
            current = {
                'h': engine.clean_team(dom[0]['text']) if dom else '?',
                'a': engine.clean_team(ext[0]['text']) if ext else '?',
                's': score['val'],
                'mt': mt or '',
                'hm': '', 'am': ''
            }
            matches.append(current)

        elif mt and current:
            current['mt'] = mt

        for b in bx:
            mins = re.findall(r"(\d{1,3})'", b['text'])
            if mins and current:
                if b['cx'] < mid_x:
                    current['hm'] = (current.get('hm', '') + ' ' + ' '.join(mins)).strip()
                else:
                    current['am'] = (current.get('am', '') + ' ' + ' '.join(mins)).strip()

    return [m for m in matches if m['h'] != '?' and m['a'] != '?']

# ===================== HEADER & SAISON =====================
st.markdown("""
<div class="main-header">
    <h1 class="header-title">🔮 Oracle Mahita</h1>
    <div class="header-subtitle">V34.1 — Cerveau I Actif — OCR Optimisé</div>
</div>
""", unsafe_allow_html=True)

s_active = st.selectbox("Saison", list(st.session_state['history'].keys()), label_visibility="collapsed")
st.session_state['s_active'] = s_active

days = [int(re.search(r'\d+', k).group()) for k in st.session_state['history'][s_active].keys() 
        if re.search(r'\d+', k) and st.session_state['history'][s_active][k].get("res")]
next_j = max(days) + 1 if days else 1
st.markdown(f'<div class="next-day-box">PROCHAINE JOURNÉE : J-{next_j}</div>', unsafe_allow_html=True)

tabs = st.tabs(["🏆 CLASSEMENT", "📅 CALENDRIER", "🎯 PRONOS", "⚽ RÉSULTATS", "📚 HISTORIQUE", "⚙️ GESTION", "📊 PERFORMANCE"])

# ===================== TAB 0 : CLASSEMENT =====================
with tabs[0]:
    st.markdown("### 🏆 Classement de la Saison")
    standings = get_standings(st.session_state['history'][s_active], engine.teams_list)

    def style_classement(row):
        rang = row['Rang']
        if rang <= 3: return ['background-color: rgba(0,255,0,0.12)'] * len(row)
        elif rang >= 17: return ['background-color: rgba(255,75,75,0.12)'] * len(row)
        return [''] * len(row)

    st.dataframe(standings.style.apply(style_classement, axis=1), use_container_width=True, hide_index=True)
    st.caption("🟢 Top 3 (Titre) · 🔴 Zone de relégation")

# ===================== TAB 1 : CALENDRIER =====================
with tabs[1]:
    st.markdown("### 📅 Import du Calendrier")
    j_cal = st.number_input("Journée", 1, 50, next_j, key="j_cal_input")
    f_cal = st.file_uploader("📸 Image du Calendrier", type=['jpg','png','jpeg'], key="cal_upload")

    if f_cal:
        with st.spinner("Lecture OCR du calendrier..."):
            # Pour l'instant, on garde la saisie manuelle. Tu peux étendre l'OCR plus tard.
            custom_notify("OCR Calendrier en cours de développement. Utilisez la saisie manuelle pour l'instant.", "#FFA500")

    if 'tmp_cal' not in st.session_state:
        if st.button("✏️ Initialiser saisie manuelle (10 matchs)"):
            st.session_state['tmp_cal'] = [
                {'h': engine.teams_list[i*2], 'a': engine.teams_list[i*2+1], 'o': [1.80, 3.50, 4.00]}
                for i in range(10)
            ]

    if 'tmp_cal' in st.session_state:
        with st.form("form_cal"):
            st.markdown("#### Vérifiez les matchs de la journée")
            final_c = []
            for i, m in enumerate(st.session_state['tmp_cal']):
                c1, c2, o1, ox, o2 = st.columns([2, 2, 1, 1, 1])
                th = c1.selectbox(f"Domicile {i+1}", engine.teams_list, index=engine.teams_list.index(m['h']) if m['h'] in engine.teams_list else 0, key=f"h_{i}")
                ta = c2.selectbox(f"Extérieur {i+1}", engine.teams_list, index=engine.teams_list.index(m['a']) if m['a'] in engine.teams_list else 0, key=f"a_{i}")
                c1v = o1.number_input("Cote 1", value=float(m['o'][0]), min_value=1.0, step=0.05, key=f"o1_{i}")
                cxv = ox.number_input("Cote X", value=float(m['o'][1]), min_value=1.0, step=0.05, key=f"ox_{i}")
                c2v = o2.number_input("Cote 2", value=float(m['o'][2]), min_value=1.0, step=0.05, key=f"o2_{i}")
                final_c.append({'h': th, 'a': ta, 'o': [c1v, cxv, c2v]})
            if st.form_submit_button("🔥 Valider & Enregistrer Calendrier"):
                jk = f"Journée {j_cal}"
                if jk not in st.session_state['history'][s_active]:
                    st.session_state['history'][s_active][jk] = {"cal": [], "res": [], "pro": []}
                st.session_state['history'][s_active][jk]["cal"] = final_c
                st.session_state['current_ready'] = final_c
                st.session_state['current_j_num'] = j_cal
                save_db(st.session_state['history'])
                if 'tmp_cal' in st.session_state: del st.session_state['tmp_cal']
                custom_notify("✅ Calendrier enregistré ! Allez dans l'onglet PRONOS", "#7FFFD4")
                st.rerun()

# ===================== TAB 2 : PRONOS =====================
with tabs[2]:
    st.markdown("### 🎯 Pronostics — Cerveau I")

    if 'current_ready' not in st.session_state or not st.session_state.get('current_ready'):
        st.info("Veuillez d'abord enregistrer un calendrier dans l'onglet **CALENDRIER**.")
    else:
        current_ready = st.session_state['current_ready']
        j_num = st.session_state.get('current_j_num', 1)
        standings = get_standings(st.session_state['history'][s_active], engine.teams_list)

        safe_d, risque_d, fun_d = [], [], []
        all_analyses = []

        for m in current_ready:
            r_dom = int(standings[standings['Équipe'] == m['h']]['Rang'].values[0]) if not standings[standings['Équipe'] == m['h']].empty else 10
            r_ext = int(standings[standings['Équipe'] == m['a']]['Rang'].values[0]) if not standings[standings['Équipe'] == m['a']].empty else 10

            forme_dom = get_forme_equipe(st.session_state['history'], s_active, m['h'])
            forme_ext = get_forme_equipe(st.session_state['history'], s_active, m['a'])
            serie_dom = get_serie_victoires(forme_dom)
            serie_ext = get_serie_victoires(forme_ext)
            dernier_adv = get_dernier_adversaire(st.session_state['history'], s_active, m['h'])

            analyse = oracle_brain.analyser_match(
                equipe_dom=m['h'], equipe_ext=m['a'], cotes=m['o'],
                journee=j_num, rang_dom=r_dom, rang_ext=r_ext,
                serie_dom=serie_dom, serie_ext=serie_ext,
                forme_dom=forme_dom, forme_ext=forme_ext,
                match_precedent_dom=dernier_adv
            )

            all_analyses.append((m, analyse))

            item = {
                "txt": analyse['choix_expert'],
                "cote": max(m['o']),
                "match": f"{m['h']} vs {m['a']}",
                "indice": analyse['indice_confiance']
            }

            if analyse.get('confiance') == "BANKER":
                safe_d.append(item)
            elif analyse.get('confiance') == "RISQUE CALCULÉ":
                risque_d.append(item)
            else:
                fun_d.append(item)

        # Affichage des matchs (simplifié)
        st.markdown(f"**Journée {j_num}** — Analyse de {len(current_ready)} matchs")
        for m, analyse in all_analyses:
            with st.container():
                st.markdown(f"**{m['h']} vs {m['a']}** — {analyse['choix_expert']} ({analyse['indice_confiance']}% )")
                st.caption(f"Cotes : {m['o']} | Confiance : {analyse.get('confiance', 'N/A')}")
            st.divider()

        # Sauvegarde pronos
        jk = f"Journée {j_num}"
        if jk in st.session_state['history'][s_active]:
            st.session_state['history'][s_active][jk]["pro"] = [
                {"m": a['choix_expert'], "c": m['o'], "indice": a['indice_confiance'], "classe": a.get('confiance')}
                for m, a in all_analyses
            ]
            save_db(st.session_state['history'])

        # Tickets
        c1, c2, c3 = st.columns(3)
        def show_ticket(col, title, data, emoji, css):
            with col:
                st.markdown(f"### {emoji} {title}")
                total = 1.0
                for x in data[:3]:
                    st.markdown(f"<div class='{css}'><b>{x['match']}</b><br>{x['txt']}<br>Indice: {x['indice']}%</div>", unsafe_allow_html=True)
                    total *= x['cote']
                st.info(f"Cote combinée ≈ {total:.2f}")

        show_ticket(c1, "TICKET SAFE", safe_d, "🟢", "prono-safe")
        show_ticket(c2, "TICKET RISQUE", risque_d, "🟡", "prono-risque")
        show_ticket(c3, "TICKET FUN", fun_d, "🔴", "prono-fun")

# ===================== TAB 3 : RÉSULTATS =====================
with tabs[3]:
    st.markdown("### ⚽ Saisie des Résultats")

    j_res = st.number_input("Journée", 1, 50, 1, key="j_res_input")
    f_res = st.file_uploader("📸 Capture Résultats Bet261", type=['jpg','png','jpeg'], key="res_upload")

    extracted = []
    jk = f"Journée {j_res}"
    cal_ref = st.session_state['history'][s_active].get(jk, {}).get("cal", [])

    if f_res:
        debug = st.checkbox("🔍 Mode Debug OCR", value=False)
        with st.spinner("OCR multi-passes en cours..."):
            extracted = ocr_resultats(f_res.getvalue(), debug=debug)

        if extracted:
            custom_notify(f"✅ {len(extracted)} matchs détectés", "#7FFFD4")
        else:
            st.warning("OCR faible. Complétez manuellement.")

    if cal_ref and len(extracted) < len(cal_ref):
        known = {(m.get('h'), m.get('a')) for m in extracted}
        for cm in cal_ref:
            if (cm['h'], cm['a']) not in known:
                extracted.append({"h": cm['h'], "a": cm['a'], "s": "", "mt": "", "hm": "", "am": ""})

    with st.form("form_resultats"):
        st.markdown("#### Correction des résultats")
        final_res = []
        for i, m in enumerate(extracted):
            st.markdown(f"**Match {i+1} : {m.get('h','?')} vs {m.get('a','?')}**")
            c1, c2 = st.columns([2, 1.5])
            score = c1.text_input("Score Final", m.get('s', '0:0'), key=f"score_{i}")
            mt_score = c2.text_input("Mi-temps", m.get('mt', ''), key=f"mt_{i}")
            b1, b2 = st.columns(2)
            hm = b1.text_input(f"Buteurs {m.get('h','')}", m.get('hm', ''), key=f"hm_{i}")
            am = b2.text_input(f"Buteurs {m.get('a','')}", m.get('am', ''), key=f"am_{i}")
            final_res.append({"h": m.get('h'), "a": m.get('a'), "s": score, "mt": mt_score, "hm": hm, "am": am})
            st.divider()

        if st.form_submit_button("✅ Enregistrer Résultats"):
            if jk not in st.session_state['history'][s_active]:
                st.session_state['history'][s_active][jk] = {"cal": cal_ref, "res": [], "pro": []}
            st.session_state['history'][s_active][jk]["res"] = final_res
            save_db(st.session_state['history'])
            custom_notify("✅ Résultats enregistrés !", "#00FF00")
            st.rerun()

# ===================== TAB 4 : HISTORIQUE =====================
with tabs[4]:
    st.markdown("### 📚 Historique des Journées")
    sorted_j = sorted(st.session_state['history'][s_active].keys(), 
                      key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    for jk in sorted_j:
        with st.expander(f"📅 {jk}"):
            d = st.session_state['history'][s_active][jk]
            htabs = st.tabs(["Calendrier", "Pronos", "Résultats"])
            with htabs[0]:
                st.dataframe(pd.DataFrame(d.get("cal", [])))
            with htabs[1]:
                st.dataframe(pd.DataFrame(d.get("pro", [])))
            with htabs[2]:
                st.dataframe(pd.DataFrame(d.get("res", [])))

# ===================== TAB 5 : GESTION =====================
with tabs[5]:
    st.markdown("### ⚙️ Gestion")
    ns = st.text_input("Nouvelle saison (ex: Saison 2027)")
    if st.button("Créer Saison"):
        if ns and ns not in st.session_state['history']:
            st.session_state['history'][ns] = {}
            save_db(st.session_state['history'])
            st.rerun()

    st.divider()
    if st.button("📥 Exporter Backup"):
        st.download_button("Télécharger Backup", 
                           data=json.dumps(st.session_state['history'], indent=4, ensure_ascii=False),
                           file_name="oracle_backup.json", mime="application/json")

# ===================== TAB 6 : PERFORMANCE =====================
with tabs[6]:
    st.markdown("### 📊 Performance Oracle")
    if st.session_state['history'][s_active]:
        stats = oracle_brain.calculer_performance_globale(st.session_state['history'][s_active])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matchs analysés", stats.get("total_matchs", 0))
        c2.metric("Taux 1N2", f"{stats.get('taux_1n2', 0):.1f}%")
        c3.metric("Scores Exacts", stats.get("scores_exacts", 0))
        c4.metric("Points/Match", f"{stats.get('moyenne_points', 0):.2f}")

        rating = stats.get("rating_general", 0)
        color = "green" if rating >= 80 else "orange" if rating >= 50 else "red"
        st.progress(int(rating))
        st.markdown(f"<h2 style='color:{color};'>{rating:.1f} / 100</h2>", unsafe_allow_html=True)

# ===================== Sauvegarde Globale =====================
if st.button("💾 Sauvegarder tout maintenant"):
    save_db(st.session_state['history'])
    custom_notify("Historique sauvegardé avec succès !", "#00FF00")
