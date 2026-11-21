"""Boussoles SCANOPTIMUS9 — tableau de bord qui se met à jour seul.   Lancer :  streamlit run app.py"""
import datetime as dt
from pathlib import Path
import numpy as np, pandas as pd, streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from boussoles.regles import MARCHES, SEUIL, SP
from boussoles.donnees import tout_charger
from boussoles.calcul import tout_calculer, historique, nb, pc, cone, rang, etat_break, or_vix, k2_mensuel, equiv_or
from boussoles import FICHIERS
from boussoles.modele import DEPLOIEMENT, lire_journal, completer, valoriser, ligne_journal, JOURNAL
import json as _json
import json
from boussoles.titres import titres as calc_titres, THEMES, peremptions, or_titres, recalibrages, portefeuille, fige_or_vix, phase_temps_reel
from boussoles.ui import CSS, COUL, FOND, badge, chip, bar, jauge, sparkline, carte

st.set_page_config(page_title="Boussoles SCANOPTIMUS9", page_icon="🧭", layout="wide", initial_sidebar_state="auto")   # « auto » : barre latérale repliée sur téléphone
def md(h): st.markdown(h.replace("\n", ""), unsafe_allow_html=True)
md(CSS)
def jour(d, court=False): return "—" if d is None or pd.isna(d) else pd.Timestamp(d).strftime("%d/%m" if court else "%d/%m/%Y")
COURT = {"SOX": "Semi-conducteurs", "Logiciel": "Logiciel", "NDX": "Nasdaq 100", "S&P 500": "S&P 500", "Mines d'or (GDX)": "Mines d'or", "Pétrolières (XLE)": "Pétrolières", "Or": "Or & mines"}
GDXN = "Mines d'or (GDX)"
SYMB = {"ok": "●", "warn": "▲", "bad": "■", "info": "◆", "mute": "○"}

LAYOUT = dict(hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0e1626", font=dict(color="#94a3b8", family="Inter"), dragmode=False,
              legend=dict(orientation="h", y=-0.06, yanchor="top", x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
              hoverlabel=dict(bgcolor="#121a2b", bordercolor="#334155", font_color="#e2e8f0"))     # légende sous le graphique, pas de zoom au doigt (téléphone)

# ---------------------------------------------------------------- données
@st.cache_data(ttl=6 * 3600, show_spinner="Téléchargement des cours, des taux, du dollar et des positions des spéculateurs…")
def charger():
    D, src = tout_charger(MARCHES); return D, src, dt.datetime.now()

@st.cache_data(show_spinner="Calcul des boussoles…", max_entries=12)
def calculer(_D, asof, memoire, cle):
    R = tout_calculer(_D, asof, memoire); H = historique(R[2], R[1]); return R + (H,)

with st.sidebar:
    st.markdown("### 🧭 Boussoles")
    st.caption("Version 6.13 · 21/11/2026 · équivalent or des niveaux GDX")
    if st.button("Mettre à jour les données", width="stretch"): charger.clear(); calculer.clear()
D, SRC, quand = charger()
if D["vix"].empty or D[SP].empty:
    st.error("Aucune donnée disponible (ni réseau, ni copie locale)."); st.stop()
seances = D["vix"].index[D["vix"].index <= min(D["vix"].index[-1], D[SP].index[-1])]
dernier = seances[-1]
with st.sidebar:
    asof = st.date_input("Séance analysée", value=dernier.date(), min_value=dt.date(1995, 1, 3), max_value=dernier.date())
    comparer = st.toggle("Comparer avec une autre séance", value=False)
    ref_def = seances[seances <= pd.Timestamp(asof)][-6] if (seances <= pd.Timestamp(asof)).sum() > 6 else seances[0]
    asof2 = st.date_input("Séance de comparaison", value=ref_def.date(), min_value=dt.date(1995, 1, 3), max_value=dernier.date(), disabled=not comparer)
    mem_lab = st.radio("Mémoire des statistiques", ["4 dernières années", "Tout l'historique (1990)"], index=0,
                       help="Âges, profondeurs, situations comparables et carte des prix. Les lois du VIX restent ajustées sur 1990-2026 (il faut assez de corrections).")
    memoire = 4 if mem_lab.startswith("4") else None
    st.divider(); st.markdown("**Mon capital** (break à −30 %)")
    _cf = Path(FICHIERS) / "capital.json"
    try: _sec = dict(st.secrets.get("capital", {}))          # en ligne : valeurs gardées dans les réglages secrets
    except Exception: _sec = {}
    try: _cap = json.loads(_cf.read_text())
    except Exception: _cap = {}
    _cap = {"plus_haut": float(_cap.get("plus_haut", _sec.get("plus_haut", 0)) or 0), "actuel": float(_cap.get("actuel", _sec.get("actuel", 0)) or 0)}
    cap_hi = st.number_input("Plus haut atteint ($)", min_value=0.0, value=_cap["plus_haut"], step=500.0)
    cap_now = st.number_input("Valeur aujourd'hui ($)", min_value=0.0, value=_cap["actuel"], step=500.0)
    if cap_now > cap_hi: cap_hi = cap_now
    if (cap_hi, cap_now) != (_cap["plus_haut"], _cap["actuel"]) and cap_now > 0:
        try: _cf.write_text(json.dumps({"plus_haut": cap_hi, "actuel": cap_now, "date": dt.date.today().isoformat()}))
        except Exception: pass
    st.caption("En ligne, la valeur par défaut vient des réglages secrets (section [capital]) ; une saisie ne dure que la visite."
               if _sec else "Reste sur ton ordinateur (fichiers/capital.json).")
    st.divider(); st.markdown("**Péremption**")
    PER = peremptions()
    for lab, ech, j in PER:
        ic = "🔴" if j < 0 else ("🟡" if j <= 30 else "🟢")
        st.caption(f"{ic} {lab} · {'expiré depuis ' + str(-j) + ' j' if j < 0 else 'jusqu’au ' + ech.strftime('%d/%m/%Y')}")
    st.caption("Mise à jour : `python fichiers/mettre_a_jour.py` (notice : fichiers/NOTICE.md)")
    st.caption(f"Données du {quand:%d/%m/%Y %H:%M}")
    for k, v in SRC.items(): st.caption(f"{'🟢' if v not in ('indisponible', 'copie locale') else ('🟡' if v == 'copie locale' else '🔴')} {k} · {v}")
cle = str(quand)
asof, C, E, O, ST, LO, V, H = calculer(D, pd.Timestamp(asof), memoire, cle)
R2 = calculer(D, pd.Timestamp(asof2), memoire, cle) if comparer else None
if R2: _, C2, E2, O2, ST2, LO2, V2, _ = R2[:8]; d2 = jour(R2[0], True)

@st.cache_data(show_spinner="Sélection des titres…", max_entries=12)
def titres_du_jour(_E, _C, _T, asof_, cle_):
    try: return calc_titres(_E, _C, _T, asof_)
    except Exception as ex: return {"erreur": str(ex)}
TI = titres_du_jour(E, C, D.get("titres"), asof, cle)

def position_regle(n, E_, TI_=None):
    """Badge d'un marché = état de la règle (familles A et B), jamais une alerte (revue_app, 18/11/2026)."""
    e = E_[n]
    if not e["reglage"]["timable"]: return "NON TIMABLE", "info", "Pétrole : aucune règle ne bat la détention (petrole_2022). Stratégie A en repère."
    if n == "Mines d'or (GDX)":
        if O and O.get("investie"): return "OR INVESTI", "ok", "Stratégie or investie : cœur de 2 mines + PHYS. Ordres dans la Conclusion du jour et l'onglet Or & mines."
        nd_, na_ = (sum(O["decor"].values()), sum(O["amorce"].values())) if O else (0, 0)
        return f"OR EN ATTENTE {nd_}/3 · {na_}/3", "mute", "Stratégie or (décor puis amorce) : achat à la clôture du jour où les six conditions sont vertes. Le cycle et le S5 de GDX ne servent que de lecture."
    t = (TI_ or {}).get(n) or {}
    if t.get("dispo"):
        niv = {"CŒUR": "ok"}.get(t["etat"], "mute"); return t["etat"], niv, t["texte"]
    if not e["A"]["investie"]: return "CYCLE FERMÉ", "bad", "Cycle terminé : on attend un signal S7."
    if e["S5"]["valide"]: return "S5 EN COURS", "ok", f"Cycle ouvert et trade S5 en cours (couteau sous {nb(e['S5']['invalidation'])})."
    return "CYCLE OUVERT", "info", "Cycle ouvert, pas de trade S5 en cours."
V = {n: position_regle(n, E, TI) for n in E}
if R2: V2 = {n: position_regle(n, E2) for n in E2}
ok_src = sum(v not in ("indisponible", "copie locale") for v in SRC.values())
mem_txt = "4 dernières années" if memoire else "1990-2026"

md(f'<div class="topbar"><div><div class="brand">SCANOPTIMUS9 · BOUSSOLES</div><div class="title">Séance du {jour(asof)}'
   f'{(" <span style=" + chr(39) + "font-size:18px;color:#64748b;font-weight:600" + chr(39) + ">· comparée au " + jour(R2[0]) + "</span>") if R2 else ""}</div>'
   f'<div class="sub">On ne prédit pas, on gère : la position applique les règles testées, les lois éclairent. Statistiques : {mem_txt}.</div></div>'
   f'<div>{chip(f"{ok_src}/{len(SRC)} sources en direct", "ok" if ok_src == len(SRC) else "warn")}</div></div>')

REC = recalibrages(E)
with st.sidebar:
    for lab, d_ in REC: st.caption(f"🔴 {lab}")
    if not REC: st.caption("🟢 Recalibrage par sortie de cycle · aucun requis")
_exp = [lab for lab, _, j in PER if j < 0] + [lab for lab, _ in REC]
if _exp: st.warning("À réviser : " + " · ".join(_exp) + ". Voir le journal de décisions.")

def delta(txt): return f'<div class="small" style="margin-top:6px;color:#a5b4fc">⇄ {txt}</div>' if R2 else ""
def dnum(a, b, d=1, unite=""):
    x = a - b; return f'{"+" if x >= 0 else ""}{nb(x, d)}{unite}'


# ---------------------------------------------------------------- matières premières et macro (v5.8)
PERIODES = {"6 mois": 126, "1 an": 252, "3 ans": 756, "10 ans": 2520}
def graphique_mp(nom, mp, secteur, nom_secteur, nj):
    """Matière première associée : cours, moyennes 50 et 200, plus haut et plus bas d'un an ; en bas, le secteur rapporté à la matière première."""
    x = mp.loc[:asof].dropna(); x = x.iloc[-(nj + 200):]; m50, m200 = x.rolling(50).mean(), x.rolling(200).mean(); x, m50, m200 = x.iloc[-nj:], m50.iloc[-nj:], m200.iloc[-nj:]
    sec = secteur.loc[:asof].reindex(x.index).ffill(); ratio = (sec / x) / (sec / x).dropna().iloc[0] * 100
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.05,
                        subplot_titles=(f"{nom} · cours, moyennes 50 et 200", f"{nom_secteur} rapporté à {nom.lower()} (base 100)"))
    fig.add_trace(go.Scatter(x=x.index, y=x.values, name=nom, line=dict(color="#fbbf24", width=2), hovertemplate="%{y:,.2f}<extra>" + nom + "</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=m50.index, y=m50.values, name="Moyenne 50", line=dict(color="#60a5fa", width=1.4)), 1, 1)
    fig.add_trace(go.Scatter(x=m200.index, y=m200.values, name="Moyenne 200", line=dict(color="#f97316", width=1.4)), 1, 1)
    h1, l1 = mp.loc[:asof].iloc[-252:].max(), mp.loc[:asof].iloc[-252:].min()
    for y, lab, col in [(h1, "plus haut 1 an", COUL["ok"]), (l1, "plus bas 1 an", COUL["bad"])]:
        fig.add_shape(type="line", x0=x.index[0], x1=x.index[-1], y0=y, y1=y, line=dict(color=col, width=1, dash="dot"), row=1, col=1)
        fig.add_annotation(x=x.index[0], y=y, text=f"{lab} · {nb(y, 1)}", showarrow=False, xanchor="left", yanchor="bottom", font=dict(color=col, size=11), row=1, col=1)
    fig.add_trace(go.Scatter(x=ratio.index, y=ratio.values, name=f"{nom_secteur} / {nom.lower()}", line=dict(color="#a78bfa", width=1.6)), 2, 1)
    fig.add_shape(type="line", x0=ratio.index[0], x1=ratio.index[-1], y0=100, y1=100, line=dict(color="#475569", width=1, dash="dot"), row=2, col=1)
    fig.update_layout(height=560, margin=dict(l=8, r=20, t=30, b=70), **LAYOUT); fig.update_layout(legend=dict(orientation="h", y=-0.06, yanchor="top", x=0)); fig.update_xaxes(showgrid=False, linecolor="#1e293b"); fig.update_yaxes(gridcolor="#1a2438", zeroline=False)
    for a in fig.layout.annotations[:2]: a.font = dict(size=12.5, color="#94a3b8")
    return fig

def bloc_mp(nom, cle, secteur_nom, titre=None):
    mp = D.get(cle, pd.Series(dtype=float)).dropna()
    if mp.empty or secteur_nom not in D: st.info(f"Cours de {nom.lower()} indisponible."); return
    x = mp.loc[:asof]; p_ = x.iloc[-1]; c20 = p_ / x.iloc[-21] - 1; h = x.iloc[-252:].max(); m200 = x.iloc[-200:].mean()
    md(f'<div class="sec">{titre or "Matière première · " + nom}</div>')
    cs = st.columns(4)
    for col, (lab, val, niv) in zip(cs, [(f"{nom} · dernier cours", nb(p_, 1), "info"), ("20 séances", pc(c20), "ok" if c20 >= 0 else "bad"),
                                          ("Sous le plus haut d’un an", pc(p_ / h - 1), "warn" if p_ / h - 1 < -0.1 else "ok"), ("Moyenne 200", ("au-dessus" if p_ > m200 else "en dessous") + f" · {pc(p_ / m200 - 1)}", "ok" if p_ > m200 else "bad")]):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="mid num" style="margin-top:6px;color:{COUL[niv]}">{val}</div>', "card tight"))
    nj = PERIODES[st.radio("Période", list(PERIODES), index=1, horizontal=True, key=f"mp_{cle}_{secteur_nom}")]
    st.plotly_chart(graphique_mp(nom, mp, D[secteur_nom], COURT.get(secteur_nom, secteur_nom), nj), width="stretch", config={"displayModeBar": False})

def inst_13f():
    """Alerte institutions (13f.md) : dernière déclaration 13F disponible, 23 gérants actifs."""
    try:
        f = pd.read_csv(Path(__file__).parent / "fichiers" / "institutions_13f.csv", parse_dates=["periode", "dispo"])
        r = f[f.dispo <= asof].iloc[-1]; on = bool(r.T4) or r.actif <= -0.02
        return ("Institutions · 13F", f"{'+' if r.actif >= 0 else ''}{r.actif * 100:.1f} pt", "warn" if on else "ok",
                f"part tech active, T{(r.periode.month - 1) // 3 + 1} {r.periode.year} · {r.reduisent:.0%} allègent" + (" · vendent dans la hausse" if r.T4 else ""))
    except Exception: return ("Institutions · 13F", "—", "mute", "fichier indisponible")

def alertes_decor(PF):
    """Famille C (tension de fin de cycle) et famille D (climat de creux), état du jour — familles_indicateurs."""
    f12 = C["fed_12m"] if C["fed_12m"] == C["fed_12m"] else 0.0; arme = C["taux10_6m"] >= SEUIL["taux10_6m"] or f12 >= 1.0
    i13 = inst_13f(); co = C.get("concentration", np.nan)
    fam_c = [("Interrupteur armé", arme and not (PF and PF["interrupteur"])), ("Taux réel", C["taux_reel_12m"] >= SEUIL["taux_reel_12m"]),
             ("Crédit sur marge", bool(C.get("marge_actif"))), ("Institutions 13F", i13[2] == "warn"), ("Concentration NDX", bool(C.get("concentration_60"))),
             ("Dispersion tech", bool(PF and PF["dispersion"]))]
    fam_d = [("Correction généralisée", bool(PF and PF["n_corr"] == 3 and not PF["interrupteur"])), ("Peur · VIX", C["vix"] >= C["vix_q80"])]
    return fam_c, fam_d

ETATC = {"porteur": ("cycle porteur", "ok"), "couteau_s5": ("couteau · S5", "warn"), "couteau": ("correction", "mute")}

def revue_du_vendredi(PF):
    """Revue du vendredi (alertes_frequence, k2_frequence, 20/11/2026) : K2 hebdomadaire et alertes lus à la clôture du vendredi.
    Les alertes de creux (famille D) ont une valeur mesurée ; celles de tension (famille C) sont du contexte, sans pouvoir d'annonce."""
    sp = D[SP].loc[:asof].dropna()
    if len(sp) < 260: return
    fr = sp.groupby(pd.Grouper(freq="W-FRI")).tail(1).index; v_ = fr[-1]
    if (v_ + pd.offsets.BDay(1)).to_period("W-FRI") == v_.to_period("W-FRI") and len(fr) > 1: v_ = fr[-2]     # semaine en cours pas encore close
    B = etat_break(D, v_); Bm = k2_mensuel(D, asof)
    vx = D["vix"].loc[:v_].dropna(); q80 = vx.iloc[-250:].quantile(0.8)
    ph = {n: phase_temps_reel(E[n]["s"].loc[:v_], E[n]["seuil_mini"]).iloc[-1] for n in ["SOX", "Logiciel", "NDX"] if n in E}
    t10 = D["dgs10"].loc[:v_].dropna(); rr = D["dfii10"].loc[:v_].dropna(); ff = D.get("fedfunds", pd.Series(dtype=float)).loc[:v_].dropna()
    arme = (t10.iloc[-1] - t10.iloc[-127] >= SEUIL["taux10_6m"]) or (len(ff) > 13 and ff.iloc[-1] - ff.iloc[-13] >= 1.0)
    nd = E["NDX"]["s"].loc[:v_] if "NDX" in E else None; sous50 = nd is not None and nd.iloc[-1] < nd.iloc[-50:].mean()
    disp = []
    for n in ["SOX", "Logiciel", "NDX"]:
        if n not in E: continue
        s_ = E[n]["s"].loc[:v_]; h21 = s_.iloc[-21:].max(); disp.append((s_.iloc[-1] <= h21 * (1 - E[n]["seuil_mini"]), s_.iloc[-1] >= h21))
    i13 = inst_13f()
    fam_d = [("Correction généralisée", sum(1 - x for x in ph.values()) == 3 and not (arme and sous50), "rebond du NDX +4 à +5 pts sur 3 mois en moyenne"),
             ("Peur · VIX", vx.iloc[-1] >= q80, f"VIX {nb(vx.iloc[-1], 1)} contre 80e centile {nb(q80, 1)} · rebond +2 à +4 pts sur 3 mois")]
    fam_c = [("Interrupteur armé", arme and not sous50), ("Taux réel", rr.iloc[-1] - rr.iloc[-253] >= SEUIL["taux_reel_12m"]),
             ("Crédit sur marge", bool(C.get("marge_actif"))), ("Institutions 13F", i13[2] == "warn"), ("Concentration NDX", bool(C.get("concentration_60"))),
             ("Dispersion tech", any(a for a, _ in disp) and any(b for _, b in disp))]
    k2t = "ALLUMÉ" if B and B["actif"] else "ÉTEINT"; k2n = "bad" if B and B["actif"] else "ok"
    lig = (f'<div class="lab">Revue du vendredi {jour(v_)}</div>'
           f'<div style="margin-top:6px"><b>K2 (règle)</b> : <b style="color:{COUL[k2n]}">{k2t}</b> — S&P {nb(B["sp"], 0) if B else "—"} contre sa moyenne 40 semaines {nb(B["m40"], 0) if B else "—"}'
           + (f' · {B["semaines_au_dessus"]}/{B["semaines_requises"]} vendredis au-dessus (8 si le décor de taux est allumé, 2 s’il est éteint)' if B and B["actif"] else "") + f' · décor de taux {"allumé" if B and B["decor"] else "éteint"}.'
           f' <span class="small">K2 mensuel (ancien, pour comparaison) : {"allumé" if Bm and Bm["actif"] else "éteint"}.</span></div>'
           '<div style="margin-top:8px"><b>Creux (à regarder)</b> : ' + " · ".join(f'{n} <b style="color:{COUL["ok"] if on else "#cbd5e1"}">{"ALLUMÉ" if on else "non"}</b>' + (f' <span class="small">({d})</span>' if on else "") for n, on, d in fam_d) + "</div>"
           '<div class="small" style="margin-top:8px"><b>Tension (contexte, sans pouvoir d’annonce)</b> : ' + " · ".join(f'{n} {"●" if on else "○"}' for n, on in fam_c)
           + ". Marge et 13F au rythme de leur publication.</div>")
    md(carte(lig, "card tight", "border-left:3px solid #60a5fa"))

def bandeau_break():
    """Le break l'emporte sur toutes les règles (break.md, décision du trader du 19/11/2026)."""
    B = etat_break(D, asof)
    dd = (cap_now / cap_hi - 1) if cap_hi > 0 and cap_now > 0 else None
    coupe = dd is not None and dd <= -0.30; arret = dd is not None and dd <= -0.35
    if coupe:
        st.error(("RÈGLE D'ARRÊT · " if arret else "BREAK · ") + f"capital à {pc(dd)} de son plus haut : tout couper. "
                 + ("Au-delà de −35 %, on arrête le système et on le réexamine." if arret else "Retour au plus tôt 3 mois après, quand le S&P a clôturé deux fins de mois au-dessus de sa moyenne 10 mois."))
    if B and B["actif"]:
        st.warning(f"BLOCAGE K2 depuis le {B['depuis']:%d/%m/%Y} : aucune nouvelle entrée tech (SOX, Logiciel, NDX). L'or et l'or-VIX restent libres. Les positions ouvertes suivent leurs règles. "
                   f"Levée après {B['semaines_requises']} clôtures hebdomadaires de suite au-dessus de la moyenne 40 semaines du S&P ({B['semaines_au_dessus']}/{B['semaines_requises']}) — 8 tant que le décor de taux est allumé, 2 dès qu'il s'éteint.")
    if not B: return
    dec = [("10 ans", B["taux10_6m"], SEUIL["taux10_6m"], "/ 6 mois"), ("Fed", B["fed_12m"], 1.0, "/ 12 mois"), ("Taux réel", B["taux_reel_12m"], SEUIL["taux_reel_12m"], "/ 12 mois")]
    dtx = " · ".join(f'{n_} {"+" if (v_ or 0) >= 0 else ""}{nb(v_)} pt {u_}{" ●" if v_ == v_ and v_ >= s_ else ""}' for n_, v_, s_, u_ in dec)
    kpi = [("Break · coupe à −30 %", "—" if dd is None else pc(dd), "mute" if dd is None else ("bad" if coupe else "warn" if dd <= -0.20 else "ok"),
            "renseigne ton capital (barre latérale)" if dd is None else f"capital / plus haut · arrêt du système à −35 %"),
           ("Blocage K2", "ACTIF" if B["actif"] else "NON", "bad" if B["actif"] else "ok",
            "aucune entrée tech nouvelle · or libre" if B["actif"] else ("se déclenche si le S&P clôture la semaine (vendredi) sous sa moyenne 40 semaines" if B["decor"] else "décor de taux éteint")),
           ("S&P / moyenne 40 semaines", pc(B["ecart"]), "warn" if B["ecart"] < 0.03 else "ok", f'{nb(B["sp"], 0)} contre {nb(B["m40"], 0)} · seuil de clôture du vendredi'),
           ("Décor de taux", "ALLUMÉ" if B["decor"] else "ÉTEINT", "warn" if B["decor"] else "ok", dtx)]
    for col, (lab, v_, niv, det) in zip(st.columns(4), kpi):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="num" style="font-size:24px;font-weight:800;color:{COUL[niv]};margin-top:6px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))
    st.write("")

@st.cache_data(show_spinner="Portefeuille modèle…", max_entries=4)
def journal_modele(_D, jusqua, cle_):
    j, n = completer(_D, lire_journal(), jusqua=jusqua, max_seances=40)
    if n:
        try: j.to_csv(JOURNAL, index=False)          # sur ton ordinateur, le journal s'allonge ; en ligne, c'est GitHub Actions qui l'écrit
        except Exception: pass
    return j

@st.cache_data(show_spinner="Ordres du jour…", max_entries=8)
def positions_du(_D, asof_, prec_, cle_):
    a_, pos, B = ligne_journal(_D, asof_, None if prec_ is None else {"positions": prec_}); return str(pd.Timestamp(a_).date()), pos, bool(B.get("actif"))

def regime_petrole():
    """Repère d'accélération (petrole_acceleration, 18/11/2026) : Brent V20 et écart à la moyenne 200 tous deux ≥ leur centile 70 sur 3 ans
    = régime de cycle probable (précision ×1,7 sur 1990-2008 et 2009-2026, 83-100 % des cycles reconnus avant mi-parcours). Lecture, pas un signal."""
    b = D.get("brent", pd.Series(dtype=float)).loc[:asof].dropna(); x = D["Pétrolières (XLE)"].loc[:asof].dropna()
    if len(b) < 1000: return None
    def f(s):
        r = np.log(s).diff(); v20 = np.log(s / s.shift(20)) / (r.rolling(20).std() * np.sqrt(20)); m200 = np.log(s / s.rolling(200).mean()) / (r.rolling(250).std() * np.sqrt(252))
        return v20, m200
    bv, bm = f(b); xv, _ = f(x); rk = lambda z: z.rolling(756, min_periods=500).rank(pct=True).iloc[-1]
    return dict(bv=bv.iloc[-1], bm=bm.iloc[-1], cbv=rk(bv), cbm=rk(bm), xv=xv.iloc[-1], cxv=rk(xv), on=bool(rk(bv) >= 0.7 and rk(bm) >= 0.7))

NOMP = {"SOX": "Semi-conducteurs", "Logiciel": "Logiciel", "NDX": "Nasdaq 100", "Or": "Or · mines + PHYS", "Or-VIX": "Or · rebond après panique"}

def ordres_du_jour(PF):
    """Ordres à l'impératif : ce que la règle impose à la clôture de la séance analysée."""
    idx = seances[seances < pd.Timestamp(asof)]
    if not len(idx) or not PF: return
    _, pos0, _ = positions_du(D, idx[-1], None, cle)
    _, pos1, k2 = positions_du(D, pd.Timestamp(asof), _json.dumps(pos0), cle)
    dd = (cap_now / cap_hi - 1) if cap_hi > 0 and cap_now > 0 else None
    cap = cap_now if cap_now > 0 else None
    tc_ = (D.get("titres") or {}).get("close", pd.DataFrame())
    def prix(t):
        try: x = tc_[t].loc[:pd.Timestamp(asof)].dropna(); return float(x.iloc[-1]) if len(x) else None
        except Exception: return None
    def fmt(L):
        """Actions entières seulement : on arrondit à l'action inférieure, le reste reste en cash."""
        out = []
        for t, w in L:
            pr = prix(t)
            if cap and pr:
                q = int(w * cap // pr)
                out.append(f"<b>{t}</b> {q} action{'s' if q > 1 else ''} ({q * pr:,.0f} $)".replace(",", " ") if q > 0
                           else f"<b>{t}</b> 0 action (1 action = {pr:,.0f} $, au-dessus des {w * cap:,.0f} $ prévus)".replace(",", " "))
            else: out.append(f"<b>{t}</b> {nb(w * 100, 1)} %")
        return " · ".join(out)
    cartes = []
    for n in ["SOX", "Logiciel", "NDX", "Or", "Or-VIX"]:
        p_ = PF["parts"].get(n)
        if p_ is None: continue
        a, b = pos0.get(n, []), pos1.get(n, [])
        ta, tb = {t for t, _ in a}, {t for t, _ in b}; wa, wb = sum(w for _, w in a), sum(w for _, w in b)
        if dd is not None and dd <= -0.30: o, niv, det = "TOUT VENDRE", "bad", "Break : capital à −30 % de son plus haut."
        elif b and not a: o, niv, det = "ACHETER À LA CLÔTURE", "ok", fmt(b)
        elif a and not b: o, niv, det = "VENDRE À LA CLÔTURE", "bad", fmt(a)
        elif a and b and ta != tb: o, niv, det = "REMPLACER À LA CLÔTURE", "warn", "vendre " + ", ".join(sorted(ta - tb)) + " · acheter " + fmt([x for x in b if x[0] not in ta])
        elif a and b and abs(wb - wa) >= 0.005: o, niv, det = f"AJUSTER À {nb(wb * 100, 0)} %", "info", fmt(b)
        elif a and b: o, niv, det = "TENIR", "ok", fmt(b)
        elif k2 and n in ("SOX", "Logiciel", "NDX") and p_.get("dedans"): o, niv, det = "INTERDIT D'ACHETER (K2)", "bad", "Le signal est là, mais le blocage K2 interdit toute entrée tech nouvelle."
        else:
            o, niv = "RESTER EN CASH", "mute"
            if n == "Or-VIX":
                ov = p_["ov"]
                det = (f"VIX {nb(ov['vix'], 1)} · plus haut 20 s. {nb(ov['pic'], 1)}. Acheter à la clôture du jour où le VIX, après avoir atteint 30, repasse sous 85 % de son pic"
                       f" ({nb(ov['seuil_reflux'], 1) if ov['pic'] >= 30 else '≈ 25,5 pour un pic à 30'}) : {' · '.join(p_.get('tient_si', [])).replace('%)', ' %)')}, {nb(p_['poids'] * 100, 0)} % du capital."
                       + (" La part or est investie : pas d'achat." if ov.get("or_investi") else "") + " Sortie 6 mois après ou si GDX perd 25 %.")
            elif n == "Or":
                nd, na = sum(O["decor"].values()), sum(O["amorce"].values())
                det = f"Décor {nd}/3, amorce {na}/3. Acheter à la clôture du jour où les six conditions sont vertes : {' · '.join(p_.get('tient_si', [])).replace('%)', ' %)') or 'cœur de 2 mines + PHYS'}, {nb(p_['poids'] * 100, 0)} % du capital."
            else:
                e = E[n]; det = ("Acheter à la clôture du prochain S5." if e["A"]["investie"] else "Acheter à la clôture du prochain S7 (nouveau cycle) ou S5.") + f" Poids prévu {nb(p_['poids'] * 100, 0)} %."
        if n == "Or-VIX" and p_["ov"].get("actif") and b:
            ov = p_["ov"]; det += f'<div style="margin-top:6px">Acheté le {jour(ov["entree"])} (GDX {nb(ov["prix"])}, {pc(ov["perf"])}). Vendre à la clôture de la 126e séance (vers le {jour(ov["fin"])}, reste {ov["reste"]}), ou dès que GDX clôture sous {nb(ov["stop"])} (−25 %).</div>'
        if n not in ("Or", "Or-VIX"):                  # lecture « cycle fragile » (pres_sortie, cycle_fragile : information, pas une règle)
            try:
                e = E[n]; A = e["A"]
                if A["investie"]:
                    th_ = e["seuil_cycle"]; hiA = A["niveau_sortie"] / (1 - th_); s_ = e["s"]
                    dh = s_[s_ >= hiA * 0.9999].index
                    if len(dh):
                        bas = s_.loc[dh[-1]:]; dmin = bas.min() / A["niveau_sortie"] - 1
                        if dmin < 0.10: det += f'<div style="margin-top:6px;color:{COUL["warn"]}">Cycle fragile : passé à {pc(dmin)} de sa sortie le {jour(bas.idxmin())}. Le poids est déjà réduit (fin de cycle proche × 0,5).</div>'
            except Exception: pass
        cartes.append((NOMP[n], o, niv, det))
    md('<div class="lab" style="margin:14px 0 6px">Ordres du jour · à exécuter à la clôture (ordre au cours de clôture), sans exception</div>')
    for col, (nom, o, niv, det) in zip(st.columns(len(cartes)), cartes):
        with col: md(carte(f'<div class="lab">{nom}</div><div style="font-size:17px;font-weight:800;letter-spacing:.03em;color:{COUL[niv] if niv != "mute" else "#cbd5e1"};margin:8px 0 6px">{o}</div><div class="small">{det}</div>', "card tight", f"border-top:3px solid {COUL[niv]}"))
    try:
        R_ = regime_petrole(); dispo = max(0.0, min(0.25, PF["part_cash"]))
        mt = f" ({dispo * cap_now:,.0f} $)".replace(",", " ") if cap_now > 0 else ""
        acc_on = bool(R_ and R_["on"]); acc_c = COUL["ok"] if acc_on else "#cbd5e1"
        acc_d = f" (vitesse 20 s. centile {R_['cbv']:.0%}, écart à la moyenne 200 centile {R_['cbm']:.0%})" if R_ else ""
        md(carte(f'<div class="lab">Poche pétrole · ton arbitrage, hors système</div><div class="small" style="margin-top:6px">Accélération du Brent : <b style="color:{acc_c}">{"ALLUMÉE" if acc_on else "éteinte"}</b>{acc_d}. '
                 f'Seulement si un catalyseur d’offre durable est là (guerre, blocus, coupure qui dure) <b>et</b> que l’accélération est allumée : jusqu’à <b>{nb(dispo * 100, 0)} %</b>{mt} du capital, pris sur le cash, en XOM · CVX · COP. '
                 f'Stops : COP −8 %, XOM −5,4 %, CVX −5,8 %. Sortie : vitesse du Brent repassée sous zéro, ou XLE −15 % depuis son plus haut. Compte dans le capital du break. Note chaque trade dans ton journal.</div>', "card tight", "border-left:3px solid #f59e0b"))
    except Exception as ex: st.caption(f"Poche pétrole indisponible : {ex}")
    md('<div class="small" style="margin:-4px 0 10px">Si ton portefeuille réel diffère du modèle, aligne-le sur lui à la clôture (sauf blocage K2 : aucune part tech nouvelle). Actions entières seulement : chaque quantité est arrondie à l’action inférieure et le reste reste en cash. Les quantités supposent le capital saisi dans la barre latérale ; sans capital, l’ordre donne les poids.</div>')

def bloc_modele():
    """Portefeuille modèle du système depuis le déploiement."""
    md(f'<div class="sec">Portefeuille modèle · le système appliqué à la lettre depuis le {jour(DEPLOIEMENT)}</div>')
    j = journal_modele(D, pd.Timestamp(asof), cle)
    tc = (D.get("titres") or {}).get("close", pd.DataFrame())
    v = valoriser(j, tc) if len(j) else pd.Series(dtype=float)
    if pd.Timestamp(asof) < DEPLOIEMENT or len(j) == 0:
        md(carte(f'<div class="txt">Suivi à partir du {jour(DEPLOIEMENT)} : la première ligne s’écrit à la clôture de cette séance, la première performance à la suivante.</div>', "card tight")); return
    v = v.loc[:pd.Timestamp(asof)]
    last = {k: L for k, L in json.loads(j[pd.to_datetime(j.date) <= pd.Timestamp(asof)].iloc[-1].positions).items()}
    perf = v.iloc[-1] / 100 - 1; pire = (v / v.cummax() - 1).min()
    def bench(serie):
        x = serie.loc[DEPLOIEMENT:pd.Timestamp(asof)].dropna(); return x.iloc[-1] / x.iloc[0] - 1 if len(x) > 1 else 0.0
    sp, ndx = bench(D[SP]), bench(D["NDX"]) if "NDX" in D else 0.0
    inv = sum(w for L in last.values() for _, w in L); cap = cap_now if cap_now > 0 else None
    kpi = [("Depuis le déploiement", pc(perf), "ok" if perf >= 0 else "bad", f"{len(v) - 1} séance{'s' if len(v) > 2 else ''} · base 100 → {nb(v.iloc[-1], 2)}"),
           ("Contre le S&P 500", pc(perf - sp), "ok" if perf >= sp else "bad", f"S&P {pc(sp)} · Nasdaq 100 {pc(ndx)}"),
           ("Pire baisse du modèle", pc(pire), "warn" if pire < -0.10 else "ok", "break à −30 %"),
           ("Investi / cash", f"{nb(inv * 100, 0)} % / {nb((1 - inv) * 100, 0)} %", "info", "positions de la dernière clôture")]
    for col, (lab, v_, niv, det) in zip(st.columns(len(kpi)), kpi):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="num" style="font-size:28px;font-weight:800;color:{COUL[niv] if niv not in ("info", "mute") else "#f8fafc"};margin-top:6px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))
    if last:
        rows = ""
        for n, L in last.items():
            for t, w in L:
                x = tc[t].loc[DEPLOIEMENT:pd.Timestamp(asof)].dropna() if t in tc else pd.Series(dtype=float)
                rows += (f'<tr><td style="padding:8px 10px;border-bottom:1px solid #1a2436;color:#94a3b8">{NOMP.get(n, n)}</td><td style="padding:8px 10px;border-bottom:1px solid #1a2436;font-weight:700;color:#f8fafc">{t}</td>'
                         f'<td class="num" style="padding:8px 10px;border-bottom:1px solid #1a2436;text-align:right">{nb(w * 100, 1)} %</td>'
                         + (f'<td class="num" style="padding:8px 10px;border-bottom:1px solid #1a2436;text-align:right">{int(w * cap // x.iloc[-1]) if len(x) else 0} · {(int(w * cap // x.iloc[-1]) * x.iloc[-1] if len(x) else 0):,.0f} $</td>'.replace(",", " ") if cap else "")
                         + f'<td class="num" style="padding:8px 10px;border-bottom:1px solid #1a2436;text-align:right">{nb(x.iloc[-1]) if len(x) else "—"}</td></tr>')
        hd = "".join(f'<th style="text-align:{a};padding:8px 10px;color:#64748b;font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;border-bottom:1px solid #263244">{h}</th>'
                     for h, a in [("Part", "left"), ("Titre", "left"), ("Poids", "right")] + ([("Actions · montant", "right")] if cap else []) + [("Cours", "right")])
        md(carte(f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>{hd}</tr>{rows}</table></div>', "card", "padding:6px 8px"))
    if len(v) > 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=v.index, y=v.values, name="Portefeuille modèle", line=dict(color="#22c55e", width=2.4)))
        for nom_, ser, col_ in [("S&P 500", D[SP], "#94a3b8"), ("Nasdaq 100", D.get("NDX"), "#60a5fa")]:
            if ser is None: continue
            x = ser.loc[DEPLOIEMENT:pd.Timestamp(asof)].dropna()
            if len(x) > 1: fig.add_trace(go.Scatter(x=x.index, y=100 * x / x.iloc[0], name=nom_, line=dict(color=col_, width=1.4, dash="dot")))
        fig.update_layout(height=300, margin=dict(l=8, r=8, t=10, b=8), **LAYOUT); fig.update_yaxes(gridcolor="#1a2438"); fig.update_xaxes(showgrid=False)
        st.plotly_chart(fig, width="stretch", config=dict(displayModeBar=False, scrollZoom=False))
    st.write("")

def conclusion_du_jour(PF):
    md('<div class="sec">Conclusion du jour · la règle décide, le décor éclaire</div>')
    md('<div class="lab" style="margin:4px 0 6px">Break · il l’emporte sur toutes les règles</div>')
    bandeau_break()
    if not PF: st.info("Conclusion indisponible : titres ou poids non calculés."); return
    try: revue_du_vendredi(PF)
    except Exception as ex: st.caption(f"Revue du vendredi indisponible : {ex}")
    try: ordres_du_jour(PF)
    except Exception as ex: st.caption(f"Ordres du jour indisponibles : {ex}")
    fam_c, fam_d = alertes_decor(PF); allc = [n for n, v in fam_c if v]; alld = [n for n, v in fam_d if v]
    NOMP = {"SOX": "Semi-conducteurs", "Logiciel": "Logiciel", "NDX": "Nasdaq 100", "Or": "Or · mines + PHYS", "Or-VIX": "Or · rebond après panique"}
    def statut(txt, niv, det=""):
        return (f'<span style="white-space:nowrap;font-weight:700;font-size:12.5px;letter-spacing:.06em;color:{COUL[niv]}">{SYMB[niv]} {txt}</span>'
                + (f'<div style="font-size:11.5px;color:#64748b;margin-top:2px">{det}</div>' if det else ""))
    # ---- bandeau de chiffres clés
    inv_p = 1 - PF["part_cash"]; n_inv = sum(p_["dedans"] for p_ in PF["parts"].values())
    kpi = [("Capital investi", f"{inv_p:.0%}", "ok" if inv_p > 0 else "mute", f"{n_inv} part{'s' if n_inv > 1 else ''} sur {len(PF['parts'])}"),
           ("Cash", f"{PF['part_cash']:.0%}", "info", f"poids revus le {jour(PF['date_poids'])}"),
           ("Tension de fin de cycle", f"{len(allc)}/{len(fam_c)}", "warn" if allc else "ok", " · ".join(allc) or "aucune alerte"),
           ("Climat de creux", "OUI" if alld else "NON", "ok" if alld else "mute", " · ".join(alld) or "ni correction générale ni peur")]
    for col, (lab, v_, niv, det) in zip(st.columns(4), kpi):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="num" style="font-size:28px;font-weight:800;color:{COUL[niv] if niv != "info" else "#f8fafc"};margin-top:6px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))
    st.write("")
    # ---- tableau des positions
    H = [("Part", "left", "16%"), ("A · Cycle", "left", "12%"), ("B · Mini-cycle", "left", "15%"), ("Position", "left", "21%"), ("Poids", "right", "12%"), ("Prochain déclencheur", "left", "24%")]
    th = "".join(f'<th style="width:{w};text-align:{a};padding:10px 12px;color:#64748b;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;border:none;border-bottom:1px solid #263244;background:transparent">{h}</th>' for h, a, w in H)
    td = lambda x, a="left": f'<td style="text-align:{a};padding:12px;border:none;border-bottom:1px solid #1a2436;vertical-align:top;color:#e2e8f0;font-size:13px">{x}</td>'
    ETX = {"porteur": "cycle porteur", "couteau_s5": "couteau (S5)", "couteau": "correction"}
    rows = ""
    for n, p_ in PF["parts"].items():
        if n == "Or-VIX":
            ov = p_["ov"]
            cyc = statut("EN COURS", "ok", f'J+{ov["seances"]}') if ov.get("actif") else statut("EN ATTENTE", "mute")
            mini = statut(f'VIX {nb(ov["vix"], 1)}', "warn" if ov["pic"] >= 30 else "mute", f'plus haut 20 s. {nb(ov["pic"], 1)}')
            ens = (f'Sortie à la 126e séance (vers le {jour(ov["fin"])}) ou si GDX clôture sous {nb(ov["stop"])}' if ov.get("actif") else "VIX ≥ 30 puis reflux sous 85 % de son pic → mines")
        elif n == "Or":
            cyc = statut("INVESTIE", "ok") if O["investie"] else statut("EN ATTENTE", "mute")
            mini = statut(f'décor {sum(O["decor"].values())}/3', "ok" if sum(O["decor"].values()) == 3 else "mute", f'amorce {sum(O["amorce"].values())}/3 · budget mines {O["budget"]["part"]:.0%}')
            nv = O.get("niveaux") or {}
            ens = (f'Sortie si l’or recule de 13 % ({nb(nv.get("or_moins13"), 1)}) ou au stop de départ' if O["investie"] and nv.get("or_moins13") else "Entrée quand le décor est à 3/3, puis l’amorce à 3/3")
        else:
            e = E[n]; A = e["A"]; m = e["mini"]; t = TI.get(n) or {}
            cyc = statut("OUVERT", "ok", f'J+{e["cycle"]["seances"]}') if A["investie"] else statut("FERMÉ", "bad", "cycle terminé")
            if PF["interrupteur"] and A["investie"]: cyc += statut("INTERRUPTEUR", "bad")
            mini = statut(("CORRECTION " + pc(-m["ampleur"])) if m["phase"] == "correction" else ("HAUSSE " + pc(m["ampleur"])), "warn" if m["phase"] == "correction" else "ok",
                          "signal S5 actif" if e["S5"]["valide"] else "pas de S5 en cours")
            sortie = f' Le cycle se ferme sous {nb(A["niveau_sortie"])} ({pc(A["niveau_sortie"] / e["prix"] - 1)}).' if A["investie"] else ""
            if e["S5"]["valide"]: ens = f'Couteau sous {nb(e["S5"]["invalidation"])} ({pc(e["S5"]["invalidation"] / e["prix"] - 1)}) → ' + ("fin du trade S5, on garde le cœur." if A["investie"] else "cash.") + sortie
            elif A["investie"]: ens = "Prochain S5 → cœur." + sortie
            else: ens = "Prochain S7 (nouveau cycle) ou S5."
            if t.get("etat", "").startswith("CASH · PIC"): ens = "Retour au-dessus du plus haut d’avant la hausse effacée, ou au prochain S5."
        etat = (PF["parts"][n]["etat"] if n in ("Or", "Or-VIX") else (TI.get(n) or {}).get("etat", p_["etat"]))
        pos = statut(etat, "ok" if p_["dedans"] else "mute", " · ".join(p_["tient"]) if p_["dedans"] else "")
        w = p_["poids"]; ec = ETX.get(p_.get("etat_cycle"), ""); mu = nb(p_.get("mult", 1), 2).rstrip("0").rstrip(",")
        jauge_w = f'<div style="height:4px;background:#1e293b;border-radius:4px;margin:6px 0 4px auto;width:90px"><div style="height:4px;width:{min(w / (0.25 if n == "Or" else 0.15 if n == "Or-VIX" else 0.5), 1) * 100:.0f}%;background:{COUL["ok"] if p_["dedans"] else "#475569"};border-radius:4px"></div></div>'
        poids = (f'<span class="num" style="font-size:16px;font-weight:800;color:{"#f8fafc" if p_["dedans"] else "#64748b"}">{w:.0%}</span>{jauge_w}'
                 f'<div style="font-size:11px;color:#64748b">{"si entrée · " if not p_["dedans"] else ""}{ec} × {mu}{" · fin de cycle" if p_.get("fin_proche") else ""}</div>')
        rows += "<tr>" + td(f'<b style="color:#f8fafc;font-size:13.5px">{NOMP.get(n, n)}</b>') + td(cyc) + td(mini) + td(pos) + td(poids, "right") + td(f'<span style="color:#94a3b8">{ens}</span>') + "</tr>"
    md(carte(f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch"><table style="width:100%;min-width:760px;border-collapse:collapse;table-layout:fixed;border:none;margin:0"><tr>{th}</tr>{rows}</table></div>', "card", "padding:6px 8px"))
    # ---- alertes du décor
    tag = lambda n_, on, niv: f'<span style="display:inline-block;margin:3px 6px 3px 0;padding:3px 9px;border-radius:6px;font-size:11.5px;font-weight:600;border:1px solid {COUL[niv] + "66" if on else "#263244"};color:{COUL[niv] if on else "#475569"};background:{FOND[niv] if on else "transparent"}">{n_}</span>'
    md(f'<div style="margin-top:10px;display:flex;gap:28px;flex-wrap:wrap"><div><span class="lab" style="margin-right:8px">C · Tension de fin de cycle</span>{"".join(tag(n_, v, "warn") for n_, v in fam_c)}</div>'
       f'<div><span class="lab" style="margin-right:8px">D · Climat de creux</span>{"".join(tag(n_, v, "ok") for n_, v in fam_d)}</div></div>')
    with st.expander("Comment lire la conclusion"):
        md('<div class="txt"><b>A</b> dit si l’on peut être investi, <b>B</b> dit quand et quoi détenir : ces deux familles seules décident. '
           f'<b>Poids</b> : W1 de fin de mois ({jour(PF["date_poids"])}) × l’état du cycle de la part (cycle porteur × 1,5 ; couteau pris par un S5 × 0,5 ; correction sans S5 × 1 ; fin de cycle proche × 0,5 en plus), total investi ≤ 100 %, 50 % au plus par part et 25 % pour l’or tant qu’il n’a pas de trades réels, le reste en cash (allocation_cycles, limite_or). <b>Break</b> : capital à −30 % de son plus haut → tout couper ; blocage K2 (S&P sous sa moyenne 40 semaines en clôture du vendredi avec un décor de taux allumé) → aucune entrée tech nouvelle (l’or et l’or-VIX restent libres, k2_or), levé après 8 vendredis de suite au-dessus, ou 2 si le décor de taux s’est éteint (k2_duree · k2_levee_taux) ; −35 % → arrêt du système (break). '
           f'<b>Position</b> : cycle ouvert → cœur de 2 du dernier S5 (coeur_permanent). <b>Exécution</b> : à la clôture du jour du signal, par un ordre au cours de clôture (vers 21 h 40, heure de Paris, à vérifier selon ton courtier et l’heure d’été) ; les sorties sont des niveaux connus la veille (timing_entree). '
           f'<b>Or · rebond après panique</b> : quand le VIX a atteint 30 puis repasse sous 85 % de son pic, cœur de 2 mines, 15 % du capital au plus dans la limite or de 25 %, si la part or est dehors (K2 ne la bloque pas) ; vente 126 séances après ou si GDX perd 25 % (or_vix_risque). '
           f'<b>C</b> et <b>D</b> sont des alertes : elles disent où regarder, jamais quoi faire ; testées ensemble, elles ne se cumulent pas (familles_indicateurs). Si une alerte contredit la règle, la règle gagne.<br>'
           f'Poche hors stratégie, pour les excursions entre deux trades : {" · ".join(PF["defensif"])} (XLP au {PF["date_xlp"]}).</div>')

def series_macro():
    """Séries des indicateurs macro, jour par jour, avec les mêmes définitions que l'outil."""
    nd = D["NDX"].loc[:asof].dropna(); ix = nd.index; X = pd.DataFrame(index=ix); X["ndx"] = nd; X["ma50"] = nd.rolling(50).mean()
    t10 = D["dgs10"].reindex(ix).ffill(); X["taux10_6m"] = t10 - t10.shift(126)
    ff = D.get("fedfunds", pd.Series(dtype=float)).dropna(); X["fed_12m"] = (ff - ff.shift(12)).reindex(ix, method="ffill") if len(ff) else np.nan
    rr = D["dfii10"].reindex(ix).ffill(); X["taux_reel_12m"] = rr - rr.shift(252)
    usd = D["usd_large"].reindex(ix).ffill(); X["dollar_10s"] = usd / usd.shift(10) - 1
    X["vix"] = D["vix"].reindex(ix).ffill(); X["q80"] = X.vix.rolling(250, min_periods=120).quantile(0.8)
    arme = (X.taux10_6m >= SEUIL["taux10_6m"]) | (X.fed_12m >= 1.0); X["interrupteur"] = arme & (X.ndx < X.ma50); X["arme"] = arme
    mg = D.get("marge", pd.Series(dtype=float)).dropna()
    if len(mg) > 20:
        yoy = mg.pct_change(12); rec = yoy.rolling(6).max() - yoy; dispo = mg.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=24)
        X["marge_yoy"] = pd.Series(yoy.values, index=dispo).reindex(ix.union(dispo)).ffill().reindex(ix)
        X["marge_recul"] = pd.Series(rec.values, index=dispo).reindex(ix.union(dispo)).ffill().reindex(ix)
        X["alerte_marge"] = (X.marge_recul >= 0.20) & (X.ndx >= X.ndx.rolling(250, min_periods=200).max() * 0.95)
    ew = D.get("ndx_ew", pd.Series(dtype=float)).dropna()
    if len(ew) > 130:
        e6 = (nd / nd.shift(126) - 1) - (ew.reindex(ix).ffill() / ew.reindex(ix).ffill().shift(126) - 1); X["concentration"] = e6
    return X

def zones(fig, masque, couleur, row):
    m = masque.fillna(False).astype(bool); d = m.astype(int).diff().fillna(m.astype(int).iloc[0])
    debuts, fins = list(m.index[d == 1]), list(m.index[d == -1])
    if len(fins) < len(debuts): fins.append(m.index[-1])
    for a, b in zip(debuts, fins): fig.add_vrect(x0=a, x1=b, fillcolor=couleur, line_width=0, layer="below", row=row, col=1)

def graphique_macro(nj):
    X = series_macro().iloc[-nj:]; has_m = "marge_yoy" in X and X.marge_yoy.notna().any(); has_c = "concentration" in X and X.concentration.notna().any()
    titres = ["Nasdaq 100 · zones orange : interrupteur coût du capital actif · zones violettes : alerte crédit sur marge", "Peur · VIX et son 80e percentile sur 1 an",
              "Coût du capital · variations en points (l’interrupteur s’arme à +1 pt)", "Taux réel 10 ans sur 12 mois (pts) · dollar sur 10 séances (%)"]
    if has_m: titres.append("Crédit sur marge (FINRA) · croissance sur 12 mois et recul depuis son plus haut de 6 mois")
    if has_c: titres.append("Concentration · NDX contre ses membres à parts égales, sur 6 mois")
    n = len(titres); hts = [0.32] + [0.68 / (n - 1)] * (n - 1)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, row_heights=hts, vertical_spacing=0.035, subplot_titles=titres, specs=[[{"secondary_y": i == 3}] for i in range(n)])
    fig.add_trace(go.Scatter(x=X.index, y=X.ndx, name="NDX", line=dict(color="#e2e8f0", width=1.8)), 1, 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.ma50, name="Moyenne 50", line=dict(color="#60a5fa", width=1.2)), 1, 1)
    zones(fig, X.interrupteur, "rgba(249,115,22,.18)", 1)
    if has_m: zones(fig, X.alerte_marge, "rgba(167,139,250,.20)", 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.q80, name="80e percentile du VIX", line=dict(color="#94a3b8", width=1.2, dash="dot")), 2, 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.vix, name="VIX", line=dict(color="#a78bfa", width=1.6)), 2, 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.taux10_6m, name="Taux 10 ans · 6 mois", line=dict(color="#f97316", width=1.6)), 3, 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.fed_12m, name="Taux Fed · 12 mois", line=dict(color="#fbbf24", width=1.6, dash="dash")), 3, 1)
    fig.add_hline(y=1.0, line=dict(color=COUL["bad"], width=1, dash="dot"), row=3, col=1)
    fig.add_trace(go.Scatter(x=X.index, y=X.taux_reel_12m, name="Taux réel · 12 mois", line=dict(color="#38bdf8", width=1.6)), 4, 1)
    fig.add_trace(go.Scatter(x=X.index, y=X.dollar_10s * 100, name="Dollar · 10 séances (%)", line=dict(color="#94a3b8", width=1.2)), 4, 1, secondary_y=True)
    fig.add_hline(y=SEUIL["taux_reel_12m"], line=dict(color=COUL["warn"], width=1, dash="dot"), row=4, col=1)
    r = 5
    if has_m:
        fig.add_trace(go.Scatter(x=X.index, y=X.marge_yoy * 100, name="Crédit · 12 mois (%)", line=dict(color="#f472b6", width=1.6)), r, 1)
        fig.add_trace(go.Scatter(x=X.index, y=X.marge_recul * 100, name="Recul depuis le plus haut 6 mois (pts)", line=dict(color="#c084fc", width=1.2, dash="dash")), r, 1)
        fig.add_hline(y=20, line=dict(color=COUL["warn"], width=1, dash="dot"), row=r, col=1); fig.add_hline(y=40, line=dict(color=COUL["bad"], width=1, dash="dot"), row=r, col=1); r += 1
    if has_c:
        fig.add_trace(go.Scatter(x=X.index, y=X.concentration * 100, name="Concentration (pts)", line=dict(color="#34d399", width=1.6)), r, 1)
        fig.add_hline(y=5, line=dict(color=COUL["warn"], width=1, dash="dot"), row=r, col=1)
    fig.update_layout(height=300 + 170 * n, margin=dict(l=8, r=20, t=40, b=90), **LAYOUT)
    fig.update_layout(legend=dict(orientation="h", y=-0.03, yanchor="top", x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=11.5)))
    fig.update_xaxes(showgrid=False, linecolor="#1e293b"); fig.update_yaxes(gridcolor="#1a2438", zeroline=False)
    for a in fig.layout.annotations[:n]: a.font = dict(size=12.5, color="#94a3b8"); a.x = 0; a.xanchor = "left"
    return fig, X.iloc[-1]

t1, t2, t3, t4 = st.tabs(["Vue d'ensemble", "Marchés", "Macro", "Interroger l'historique"])

# ================================================================ VUE D'ENSEMBLE
def tuile_climat(lab, valeur, etat, niv, concl, visuel, dl=""):
    return carte(f'<div class="row"><span class="lab">{lab}</span>{badge(etat, niv)}</div>'
                 f'<div class="row" style="align-items:flex-end;margin-top:6px"><div class="big num">{valeur}</div><div>{visuel}</div></div>'
                 f'<div class="txt" style="margin-top:6px">{concl}</div>{dl}')
def u_(x): return f"<span style='font-size:16px;color:#94a3b8'>{x}</span>"

def bloc_cycle(e, st_):
    cy = e["cycle"]; A = e["A"]; pr = rang(cy["seances"], st_["cycle_seances"])
    if A["investie"]:
        tete = f'<span style="color:{COUL["ok"]}">●</span> CYCLE OUVERT · J+{cy["seances"]}'
        l1 = f'Depuis le creux du {jour(cy["creux"])} : {pc(cy["gain_actuel"], 0)} (sommet {pc(cy["gain"], 0)}). Plus long que {pc(pr, 0, False)} des cycles depuis 1990.'
        l2 = f'Recul du sommet {pc(cy["recul"])} · {pc(cy["recul_x_seuil"], 0, False)} du chemin vers la sortie ({nb(A["niveau_sortie"])})'
        b = bar(cy["recul_x_seuil"], "warn" if cy["recul_x_seuil"] >= 0.5 else "ok", 1.0)
    else:
        tete = f'<span style="color:{COUL["bad"]}">■</span> CYCLE FERMÉ'; l1 = f"En attente d'un signal S7 (dernier : {jour(e['dernier_S7'])})."; l2 = ""; b = ""
    return f'<div class="lab" style="margin-top:12px">{tete}</div><div class="txt" style="margin-top:4px">{l1}</div>{b}<div class="small" style="margin-top:4px">{l2}</div>'

def bloc_mini(e, lois):
    m = e["mini"]
    if m["phase"] == "correction":
        d = next(l for l in lois if l["titre"].startswith("Loi du VIX · durée")); j = d["jauge"]
        tete = f'<span style="color:{COUL["warn"]}">▼</span> MINI-CORRECTION · SÉANCE {m["seances"]}'
        l1 = f'{pc(-m["ampleur"])} du mini-pic (au pire {pc(-m["ampleur_max"])}, {nb(m["x_seuil_max"])} seuil). Loi du VIX : fin entre {j[3][0]:.0f} et {j[3][1]:.0f} séances.'
        b = bar(j[0] / j[1], d["niveau"], j[2] / j[1], (j[3][0] / j[1], j[3][1] / j[1]))
        c_ = next(l for l in lois if l["titre"] == "Creux ou continuation ?"); l2 = f'{c_["valeur"].capitalize()} · barre = séances, cadre = intervalle de la loi'
    else:
        d = next(l for l in lois if l["titre"] == "Dynamique de la mini-hausse"); j = d["jauge"]
        tete = f'<span style="color:{COUL["ok"]}">▲</span> MINI-HAUSSE · {m["seances"]} SÉANCES'
        l1 = f'{pc(m["ampleur"])} depuis le creux, {pc(-m["retombee"])} depuis son plus haut. Bascule en correction sous {nb(m["niveau_bascule"])}.'
        b = bar(j[0], d["niveau"], 1.0, j[3]); c_ = next(l for l in lois if l["titre"] == "Bascule en correction ?")
        l2 = f'Bascule dans les 10 séances : {c_["valeur"].split(" ")[0]} des cas comparables · barre = retombée vers la bascule'
    return f'<div class="lab" style="margin-top:14px">{tete}</div><div class="txt" style="margin-top:4px">{l1}</div>{b}<div class="small" style="margin-top:4px">{l2}</div>'

with t1:
    try: PF = portefeuille(E, C, TI, or_titres(O, D.get("titres"), asof, D.get("Mines d'or (GDX)", pd.Series(dtype=float)).loc[:asof], MARCHES["Mines d'or (GDX)"]["mini"]) if O else None, O, D.get("titres"), asof, ov=fige_or_vix(or_vix(D, asof, O), O, D.get("titres"), D.get("Mines d'or (GDX)", pd.Series(dtype=float)).loc[:asof], MARCHES["Mines d'or (GDX)"]["mini"]) if O else None)
    except Exception: PF = None
    try: bloc_modele()
    except Exception as ex: st.caption(f"Portefeuille modèle indisponible : {ex}")
    md('<div class="sec">Climat du mini-cycle · VIX et dollar (le décor macro est dans l’onglet Macro)</div>')
    vx, q8 = C["vix"], C["vix_q80"]; dE = C["seances_depuis_e80"]; vm5 = C["vix_max5"]
    if vx >= 30: pe, pn = "PANIQUE", "bad"
    elif dE is not None and dE <= 7: pe, pn = "FENÊTRE DE CREUX", "ok"
    elif vx >= q8 and vx >= 0.95 * vm5: pe, pn = "PEUR QUI MONTE", "warn"
    elif vx >= q8 and vx <= SEUIL["reflux"] * vm5: pe, pn = "PEUR QUI REFLUE", "ok"
    elif vx >= q8: pe, pn = "PEUR ÉLEVÉE", "warn"
    else: pe, pn = "CALME", "ok"
    aD, bD, _ = (ST.get("NDX") or ST[SP])["duree"]
    c1, c4 = st.columns(2)
    with c1: md(tuile_climat("Peur · VIX", nb(vx, 1), pe, pn, f"Seuil de peur {nb(q8, 1)} · à ce VIX, une correction du Nasdaq dure ≈ {aD * (vx / 20) ** bD:.0f} séances.",
                             jauge(vx, 45, pn, q8, 120), delta(f"{d2} : {nb(C2['vix'], 1)} ({dnum(vx, C2['vix'])})") if R2 else ""))
    u = C["dollar_10s"]; n_ = "bad" if C["dollar_ruee_20s"] else "ok"
    with c4: md(tuile_climat("Dollar · 10 séances", pc(u, 2), "RUÉE" if n_ == "bad" else "CALME", n_, "Une ruée (≥ +1,14 %) transforme 57-74 % des creux en couteaux.",
                             jauge(max(u, 0), 0.02, n_, 0.0114, 120), delta(f"{d2} : {pc(C2['dollar_10s'], 2)}") if R2 else ""))

    def comptes(E_, C_):
        nA = sum(e["A"]["investie"] for e in E_.values()); s5 = [n for n, e in E_.items() if e["S5"]["valide"]]
        p4 = [n for n, e in E_.items() if e["P4"]["seances"] is not None and e["P4"]["seances"] <= 10]
        nr = [n for n, e in E_.items() if e["mini"]["phase"] == "correction" and e["mini"]["x_seuil_max"] >= SEUIL["approche"]]
        return nA, s5, p4, nr
    nA, nS5, nP4, nNR = comptes(E, C)
    if R2: nA2, nS52, nP42, nNR2 = comptes(E2, C2)
    dc = lambda a, b: f' <span style="font-size:15px;color:#a5b4fc">({"+" if a - b >= 0 else ""}{a - b})</span>' if R2 else ""
    md('<div class="sec">Marchés · cycle et mini-cycle</div>')
    noms = list(E)
    for i in range(0, len(noms), 3):
        for col, n in zip(st.columns(3), noms[i:i + 3]):
            e = E[n]; vtxt, vniv, raison = V[n]; s = e["s"]; ch1 = s.iloc[-1] / s.iloc[-2] - 1
            lw = next((l for l in LO[n] if l["niveau"] == vniv), LO[n][0])
            chips = (chip("S5 ACTIF", "ok") if e["S5"]["valide"] else "") + (chip(f"P4 J+{e['P4']['seances']}", "warn") if n in nP4 else "") + \
                    (chip("NON-RETOUR PROCHE", "bad") if n in nNR else "")
            cc = next((l for l in LO[n] if l["titre"] in ("Creux ou continuation ?", "Bascule en correction ?")), None)
            if cc and cc["titre"] == "Creux ou continuation ?": chips += chip(cc["valeur"], cc["niveau"])
            dl = ""
            if R2 and n in E2:
                e2 = E2[n]; v2 = V2[n]
                dl = delta(f"{d2} : {v2[0].lower()} → {vtxt.lower()} · cours {pc(e['prix'] / e2['prix'] - 1)} · "
                           + (f"mini-{e2['mini']['phase']} {nb(e2['mini']['x_seuil_max'] if e2['mini']['phase'] == 'correction' else e2['mini']['x_seuil'])} seuil"))
            spk = sparkline(s.iloc[-126:].values, vniv, bandes=e["bande80"][10]); bcyc = "" if n == GDXN else bloc_cycle(e, ST[n])
            with col: md(carte(f'<div class="row"><div><div class="lab">{n}</div><div class="mid">{COURT[n]}</div></div>{badge(vtxt, vniv)}</div>'
                               f'<div class="row" style="margin-top:8px"><span class="big num">{nb(e["prix"])}</span>{chip(pc(ch1), "ok" if ch1 >= 0 else "bad")}</div>'
                               f'<div style="margin:6px 0 0 0">{spk}</div><div class="small">6 mois · cône = carte des prix à 10 séances (80 %, situations comparables)</div>'
                               f'{bcyc}{bloc_mini(e, LO[n])}'
                               f'<div class="txt" style="margin-top:12px;padding-top:10px;border-top:1px solid #1e293b"><b style="color:{COUL[vniv]}">{SYMB[vniv]} {raison}</b></div>'
                               f'<div style="margin-top:8px">{chips}</div>{dl}'))
        st.write("")

    md('<div class="sec">Ce que vaut le système · espérance d’abord, puis simulation datée (20/11/2026)</div>')
    tr = [("Espérance réaliste · 5 ans", "≈ +17 %/an", "pire baisse ≈ −30 %", "Après décotes statistiques, break et limite or compris, si le régime haussier de la tech dure (robustesse_futur, break, limite_or)", "warn"),
          ("Régime type 2000-2009", "≈ −2 %/an", "pire baisse ≈ −50 %", "Version indices 1995-2015 avec le break (sans lui : −82 %). C'est ce chiffre qui fixe la taille des positions (break)", "bad"),
          ("Système · 04/01/2016 → 13/11/2026", "+36,2 %/an", "pire baisse −25 %", "Dans l'échantillon. Break, or à 25 % et cœur permanent compris ; or-VIX : +0,8 à +1,2 pt/an en plus · S&P 500 : +12,8 %/an, −34 % · NDX : +18,1 %, −36 % (coeur_permanent, or_vix_risque)", "ok"),
          ("Système · 03/01/2022 → 13/11/2026", "+42,1 %/an", "pire baisse −19 %", "Dans l'échantillon, marché baissier de 2022 compris (cœur permanent ; la fenêtre à partir du 14/11/2022 est la plus flatteuse) · part or 2013-2026 : +20,5 %/an, −36 %, 4 trades", "info")]
    for col, (a, b_, c_, d_, niv) in zip(st.columns(4), tr):
        with col: md(carte(f'<div class="lab">{a}</div><div class="big num" style="color:{COUL[niv] if niv != "mute" else "#f8fafc"}">{b_}</div><div class="txt" style="font-weight:600">{c_}</div><div class="small" style="margin-top:6px">{d_}</div>'))
    conclusion_du_jour(PF)

# ================================================================ MARCHÉS


def graphique(e, nj):
    s = e["s"].iloc[-nj:]; vix = C["vix_serie"].reindex(s.index).ffill(); q80 = C["q80_serie"].reindex(s.index).ffill()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.74, 0.26], vertical_spacing=0.035)
    fut = pd.bdate_range(s.index[-1], periods=21); Q = cone(e)          # quantiles 10/25/50/75/90 à 0…20 séances
    for (a, b), al, lab in [((0, 4), 0.16, "Carte des prix 80 %"), ((1, 3), 0.30, "Carte des prix 50 %")]:
        fig.add_trace(go.Scatter(x=list(fut) + list(fut[::-1]), y=list(Q[:, b]) + list(Q[::-1, a]), fill="toself", fillcolor=f"rgba(59,130,246,{al})",
                                 line=dict(width=0), name=lab, hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=fut, y=Q[:, 2], mode="lines", line=dict(color="#93c5fd", width=1.5, dash="dot"), name="Médiane attendue",
                             hovertemplate="médiane %{y:,.0f}<extra></extra>"), 1, 1)
    for hh in (5, 10, 20):
        fig.add_trace(go.Scatter(x=[fut[hh], fut[hh]], y=[Q[hh, 0], Q[hh, 4]], mode="lines+markers", line=dict(color="#93c5fd", width=1, dash="dot"), marker=dict(size=5, color="#93c5fd"),
                                 showlegend=False, hovertemplate=f"Dans {hh} séances : 80 % de chances entre {nb(Q[hh, 0])} et {nb(Q[hh, 4])} (médiane {nb(Q[hh, 2])})<extra></extra>"), 1, 1)
    for k in (0, 2, 4):
        fig.add_annotation(x=fut[-1], y=Q[-1, k], text=f"<b>{nb(Q[-1, k], 0)}</b>", showarrow=False, xanchor="left", font=dict(color="#93c5fd", size=10.5), row=1, col=1)
    fig.add_trace(go.Scatter(x=s.index, y=s.values, name="Cours", line=dict(color="#e2e8f0", width=2), hovertemplate="%{y:,.2f}<extra>Cours</extra>"), 1, 1)
    for nom_sig, col, sym, lab in [("S5", COUL["ok"], "triangle-up", "Creux S5"), ("P4", COUL["warn"], "triangle-down", "Pic P4"), ("S7", "#60a5fa", "star", "Creux de cycle S7")]:
        sg = e["series"][nom_sig].reindex(s.index).fillna(False).astype(bool); sg = sg & ~sg.shift(1, fill_value=False)
        if sg.any(): fig.add_trace(go.Scatter(x=s.index[sg], y=s[sg] * (0.985 if nom_sig != "P4" else 1.015), mode="markers", name=lab,
                                              marker=dict(color=col, size=9, symbol=sym, line=dict(color="#0a0f1c", width=1)), hovertemplate=f"{lab}<extra></extra>"), 1, 1)
    m = e["mini"]
    niv = [("Sortie du cycle (A)", e["A"]["niveau_sortie"], COUL["bad"]), ("Couteau S5", e["S5"]["invalidation"] if e["S5"]["valide"] else None, "#fb7185"),
           ("Non-retour", m["niveau_non_retour"], COUL["warn"]), ("Fin de correction", m["niveau_confirmation"], COUL["ok"]),
           ("Bascule en correction", m["niveau_bascule"], COUL["warn"])]
    EQ = equiv_or(D, s.index[-1], {l_: y_ for l_, y_, _ in niv}) if e["nom"] == GDXN else None     # équivalent or des niveaux de GDX
    prev = None
    for lab, y, col in sorted([x for x in niv if x[1] is not None], key=lambda x: x[1]):
        proche = prev is not None and abs(y / prev - 1) < 0.03          # deux niveaux voisins : on décale l'étiquette
        fig.add_shape(type="line", x0=s.index[0], x1=fut[-1], y0=y, y1=y, line=dict(color=col, width=1.4, dash="dash"), row=1, col=1)
        fig.add_annotation(x=s.index[0] if not proche else s.index[len(s) // 3], y=y, text=f"{lab} · {nb(y)}" + (f" · or ≈ {nb(EQ['niveaux'][lab][1], 0)}" if EQ and lab in EQ["niveaux"] else ""), showarrow=False, xanchor="left",
                           yanchor="bottom" if not proche else "top", font=dict(color=col, size=10.5), bgcolor="rgba(10,15,28,.75)", borderpad=2, row=1, col=1)
        prev = y
    fig.add_trace(go.Scatter(x=q80.index, y=q80.values, name="Seuil de peur (80e)", line=dict(color="#64748b", width=1.5, dash="dot"), hovertemplate="%{y:.1f}<extra>seuil</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=vix.index, y=np.maximum(vix.values, q80.values), fill="tonexty", fillcolor="rgba(239,68,68,.25)", line=dict(width=0), showlegend=False, hoverinfo="skip"), 2, 1)
    fig.add_trace(go.Scatter(x=vix.index, y=vix.values, name="VIX", line=dict(color="#a78bfa", width=1.8), hovertemplate="%{y:.1f}<extra>VIX</extra>"), 2, 1)
    E8 = [d for d in C["e80_dates"] if d >= s.index[0]]
    if E8: fig.add_trace(go.Scatter(x=E8, y=vix.reindex(E8).values, mode="markers", name="VIX entre dans la peur", marker=dict(color="#f472b6", size=9, symbol="diamond")), 2, 1)
    fig.update_layout(height=620, margin=dict(l=4, r=52, t=6, b=8), **LAYOUT)
    fig.update_xaxes(showgrid=False, linecolor="#1e293b"); fig.update_yaxes(gridcolor="#1a2438", zeroline=False); fig.update_yaxes(title_text="VIX", row=2, col=1)
    return fig

def carte_loi(l):
    j = l["jauge"]; b = ""
    if j is not None and j[1]:
        bd = (j[3][0] / j[1], j[3][1] / j[1]) if len(j) > 3 and j[3] is not None else None
        b = bar(j[0] / j[1], l["niveau"], (j[2] / j[1]) if j[2] is not None else None, bd)
    c = COUL[l["niveau"]]
    return carte(f'<div class="row"><span class="lab">{l["titre"]}</span><span style="color:{c};font-size:15px">{SYMB[l["niveau"]]}</span></div>'
                 f'<div class="mid num" style="margin-top:4px;color:{c}">{l["valeur"]}</div>{b}'
                 f'<div class="txt" style="margin-top:10px">{l["conclusion"]}</div><div class="small" style="margin-top:8px">{l["source"]}</div>', "card law", f"border-left-color:{c}")

def tuiles_marche(e, repere=False):
    m = e["mini"]
    A = e["A"]; dA = A["niveau_sortie"] / e["prix"] - 1 if A["investie"] else None; an = e["analogue"]
    if m["phase"] == "correction": mv, mn_, md_ = f"CORRECTION {pc(-m['ampleur'])}", "warn", f"séance {m['seances']} · au pire {pc(-m['ampleur_max'])} ({nb(m['x_seuil_max'])} seuil)"
    else: mv, mn_, md_ = f"HAUSSE {pc(m['ampleur'])}", ("warn" if m["retombee"] / e["seuil_mini"] >= 0.5 else "ok"), f"{m['seances']} séances · {pc(-m['retombee'])} depuis son plus haut"
    lo10, hi10 = e["bande80"][10]
    tiles = [("Cycle", "OUVERT" if A["investie"] else "FERMÉ", "ok" if A["investie"] else "bad", f"J+{e['cycle']['seances']} · sortie à {nb(A['niveau_sortie'])} ({pc(dA)})" if A["investie"] else f"dernier S7 {jour(e['dernier_S7'])}"),
             ("Mini-cycle", mv, mn_, md_),
             ("Signal de creux S5", "ACTIF" if e["S5"]["valide"] else "—", "ok" if e["S5"]["valide"] else "mute", f"couteau sous {nb(e['S5']['invalidation'])}" if e["S5"]["valide"] else f"dernier le {jour(e['S5']['dernier'])}"),
             ("Carte des prix · 10 séances", f"{nb(lo10, 0)} – {nb(hi10, 0)}", "info", f"80 % · bas {pc(lo10 / e['prix'] - 1, 0)} / haut {pc(hi10 / e['prix'] - 1, 0)}")]
    if repere: tiles = [(l_, v_, "info" if n_ in ("ok", "bad") else n_, d_) for l_, v_, n_, d_ in tiles[1:]]      # GDX : pas de cycle A, couleurs neutres
    for col, (lab, v_, niv, det) in zip(st.columns(len(tiles)), tiles):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="mid num" style="color:{COUL[niv]};margin-top:4px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))

def bloc_regime_petrole():
    R_ = regime_petrole()
    if not R_: return
    md('<div class="sec">Régime du pétrole · accélération des prix (repère, pas de signal)</div>')
    t = [("Cycle du Brent", "ACCÉLÉRATION" if R_["on"] else "PAS D’ACCÉLÉRATION", "ok" if R_["on"] else "mute",
          f"Vitesse 20 s. : centile {R_['cbv']:.0%} · écart à la moyenne 200 : centile {R_['cbm']:.0%}. Les deux ≥ 70 % : régime de cycle probable."),
         ("Vitesse du Brent · 20 séances", f"{'+' if R_['bv'] >= 0 else ''}{nb(R_['bv'], 2)} σ", "info", "Dans un cycle, elle monte au premier tiers puis se maintient ; hors cycle, elle est négative."),
         ("Mini-hausse de XLE", f"centile {R_['cxv']:.0%}", "ok" if R_["cxv"] >= 0.7 else "mute", f"Vitesse 20 s. de XLE {'+' if R_['xv'] >= 0 else ''}{nb(R_['xv'], 2)} σ : le meilleur repère d’une mini-hausse en cours (AUC 0,70-0,74).")]
    for col, (lab, v_, niv, det) in zip(st.columns(3), t):
        with col: md(carte(f'<div class="lab">{lab}</div><div class="mid num" style="color:{COUL[niv]};margin-top:4px">{v_}</div><div class="small" style="margin-top:4px">{det}</div>', "card tight"))
    st.caption("Le pétrole reste non timable (petrole_2022) : ce repère dit si l’on est probablement dans un cycle, pas quand entrer ni sortir. Le cycle se confirme par son catalyseur (dossier pétrole). Poche pétrole (ton arbitrage, 25 % du capital au plus si le cash est disponible) : voir les ordres du jour, vue d’ensemble.")

def vue_marche(n):
    e = E[n]; vtxt, vniv, raison = V[n]; m = e["mini"]; s = e["s"]; ch1 = s.iloc[-1] / s.iloc[-2] - 1
    lw = next((l for l in LO[n] if l["niveau"] == vniv), LO[n][0])
    c1, c2 = st.columns([1.15, 2])
    dl = delta(f"{d2} : {V2[n][0].lower()} · cours {nb(E2[n]['prix'])} ({pc(e['prix'] / E2[n]['prix'] - 1)})") if R2 and n in E2 else ""
    with c1: md(carte(f'<div class="lab">{n} · seuils cycle {pc(e["seuil_cycle"], 1, False)} · mini {pc(e["seuil_mini"], 1, False)}</div>'
                      f'<div class="title" style="font-size:26px">{COURT[n]}</div><div class="row" style="margin-top:8px"><span class="big num">{nb(e["prix"])}</span>{chip(pc(ch1), "ok" if ch1 >= 0 else "bad")}</div>{dl}'))
    with c2: md(carte(f'<div class="row"><div>{badge(vtxt, vniv, True)}</div><div class="small">position selon la règle (cycle A + mini-cycle) · les lois ci-dessous sont une lecture</div></div>'
                      f'<div class="mid" style="margin-top:10px">{raison}</div>'))
    st.write("")
    tuiles_marche(e)
    per = st.segmented_control("Période", ["3 mois", "6 mois", "1 an", "3 ans", "10 ans"], default="1 an", label_visibility="collapsed", key="per_" + n) or "1 an"
    st.plotly_chart(graphique(e, {"3 mois": 63, "6 mois": 126, "1 an": 252, "3 ans": 756, "10 ans": 2520}[per]), width="stretch", config=dict(displayModeBar=False))
    q20 = cone(e, [20])[0]; an = e["analogue"]
    md(f'<div class="small">Carte des prix : ce qu’ont fait les {an["n"]} situations les plus proches (6 marchés, {mem_txt} ; même {an["critere"]}), ramenées à la volatilité du jour. '
       f'Médiane à 20 séances {pc(q20[2] / e["prix"] - 1)} ; 80 % entre {pc(q20[0] / e["prix"] - 1)} et {pc(q20[4] / e["prix"] - 1)}. Un cône qui penche vers le bas = les cas comparables ont plus souvent prolongé la baisse.</div>')
    md('<div class="sec">Lecture par nos lois</div>')
    lois = LO[n]
    for i in range(0, len(lois), 3):
        for col, l in zip(st.columns(3), lois[i:i + 3]):
            with col: md(carte_loi(l))
        st.write("")
    if n in THEMES: bloc_titres(n)

def bloc_titres(n):
    md(f'<div class="sec">Titres de la thématique · {THEMES[n]}</div>')
    t = TI.get(n)
    if not t or not t.get("dispo"):
        st.info("Sélection des titres indisponible : " + (t["raison"] if t else TI.get("erreur", "cours des titres non chargés"))); return
    c1, c2 = st.columns([1, 2.6])
    with c1: md(carte(f'<div class="lab">Position en titres</div><div style="margin:10px 0">{badge(t["etat"], t["niveau"], True)}</div>'
                      f'<div class="txt">{t["texte"]}</div><div class="small" style="margin-top:10px">Cœur : <b style="color:#e2e8f0">{" · ".join(t["coeur"])}</b></div>'
                      f'<div class="small">Liste figée au S5 du {jour(t["date_liste"])}</div>'))
    tete = "".join(f'<th style="white-space:nowrap;text-align:{a};padding:6px 10px;color:#94a3b8;font-size:11px;letter-spacing:.1em;text-transform:uppercase;font-weight:600">{h}</th>'
                   for h, a in [("Titre", "left"), ("Rôle", "left"), ("Bêta", "right"), ("Cours", "right"), ("Depuis S5", "right"), ("20 s.", "right"), ("vs haut 1 an", "right"), ("MM50", "center")])
    def cel(x, a="right", c="#e2e8f0"): return f'<td class="num" style="white-space:nowrap;text-align:{a};padding:7px 10px;color:{c};border-top:1px solid #1e293b">{x}</td>'
    def cpc(x): return COUL["ok"] if x >= 0 else COUL["bad"]
    rows = ""
    for l in t["lignes"]:
        role = chip("CŒUR", "ok") if l["coeur"] else chip("LISTE", "mute")
        rows += ("<tr>" + f'<td style="padding:7px 10px;border-top:1px solid #1e293b;font-weight:700;color:#f8fafc">{l["titre"]}</td>' + f'<td style="padding:7px 10px;border-top:1px solid #1e293b">{role}</td>'
                 + cel(nb(l["beta"], 2)) + cel(nb(l["cours"])) + cel(pc(l["depuis"]), c=cpc(l["depuis"])) + cel(pc(l["r20"]), c=cpc(l["r20"])) + cel(pc(l["recul"]))
                 + cel("▲ dessus" if l["ma50"] else "▼ dessous", "center", COUL["ok"] if l["ma50"] else COUL["bad"]) + "</tr>")
    with c2: md(carte(f'<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>{tete}</tr>{rows}</table>'
                      f'<div class="small" style="margin-top:10px">Parmi les 15 plus gros {"volumes" if n == "NDX" else "poids"} ({t["source"]}), les 5 qui ont le plus amplifié les mini-corrections de l’indice sur 2 ans (bêta en correction). '
                      f'Cœur = les 2 premiers{" (hors titres déjà au cœur des semis)" if n == "NDX" else ""}. Gain du cœur : il tient à quelques grands rebonds, la médiane par trade vaut l’indice (coeur_controles).</div>'))

def vue_or():
    if O is None: st.warning("Données des mines indisponibles."); return
    nd, na = sum(O["decor"].values()), sum(O["amorce"].values()); b = O["budget"]
    etat = ("INVESTIE", "ok") if O["investie"] else (("DÉCOR PRÊT", "warn") if nd == 3 else ("EN ATTENTE", "mute"))
    c1, c2, c3 = st.columns([1.4, 1, 1])
    manque = f"Ordre : ne rien acheter. Il manque {3 - nd} condition{'s' if 3 - nd > 1 else ''} de décor et {3 - na} d’amorce. Achat à la clôture du jour où les six sont vertes, sans attendre ni anticiper."
    with c1: md(carte(f'<div class="lab">Stratégie or · mines (cœur de 2) + PHYS</div><div style="margin:10px 0">{badge(etat[0], etat[1], True)}</div>'
                      f'<div class="txt">{"Ordre : tenir. Vendre à la clôture du jour où l’une des trois sorties ci-dessous est franchie." if O["investie"] else ("Ordre : ne rien acheter tant que l’amorce n’est pas à 3/3 ; acheter à la clôture du jour où elle l’est." if nd == 3 else manque)}</div>'
                      f'<div class="row" style="margin-top:12px"><span class="small">Or <b class="num" style="color:#e2e8f0">{nb(O["or_prix"], 1)}</b></span><span class="small">GDX <b class="num" style="color:#e2e8f0">{nb(O["gdx"])}</b></span><span class="small">GVZ <b class="num" style="color:#e2e8f0">{nb(O["gvz"], 1)}</b></span></div>'
                      + (delta(f"{d2} : décor {sum(O2['decor'].values())}/3, amorce {sum(O2['amorce'].values())}/3, budget {O2['budget']['part']:.0%}") if R2 and O2 else "")))
    with c2: md(carte(f'<div class="lab">Conditions remplies</div><div class="row" style="margin-top:6px"><div><div class="num" style="font-size:44px;font-weight:800;color:{COUL["ok"] if nd == 3 else "#f8fafc"}">{nd}<span style="font-size:20px;color:#64748b">/3</span></div><div class="small">décor</div></div>'
                      f'<div><div class="num" style="font-size:44px;font-weight:800;color:{COUL["ok"] if na == 3 else "#f8fafc"}">{na}<span style="font-size:20px;color:#64748b">/3</span></div><div class="small">amorce</div></div></div>', "card counter"))
    bt = (f"GDX en correction {pc(b['profondeur'])}, séance {b['seances']} / ≈ {b['duree']:.0f}. 90 % de mines seulement après −17 % et la durée dépassée." if b["phase"] == "correction"
          else f"GDX en hausse, {b['seances']} séances / ≈ {b['duree']:.0f}, écart à l'or {pc(b['ecart'])}. 50 % de mines en surchauffe (écart ≥ +20 % et durée dépassée).")
    with c3: md(carte(f'<div class="lab">Budget de risque · part de mines, le reste en PHYS</div><div class="row"><span class="big num" style="font-size:40px">{b["part"]:.0%}</span>{jauge(b["part"], 1, "info", 0.7, 110)}</div><div class="txt">{bt}</div>'))
    md('<div class="sec">1 · Décision · les six conditions d’entrée</div>')
    def cond(lab, ok_, val, frac, rep, aide):
        c = COUL["ok"] if ok_ else "#475569"
        return carte(f'<div class="row"><span class="lab">{lab}</span><span style="color:{c};font-size:20px">{"✔" if ok_ else "○"}</span></div>'
                     f'<div class="mid num" style="margin-top:4px;color:{COUL["ok"] if ok_ else "#e2e8f0"}">{val}</div>{bar(frac, "ok" if ok_ else "mute", rep)}<div class="small" style="margin-top:8px">{aide}</div>', "card law", f"border-left-color:{c}")
    vr = O["var20"]
    r1 = [("Dollar fort", O["decor"]["dollar"], f"rang {nb(O['dollar_rang'], 0)}/100", O["dollar_rang"] / 100, 0.9, "rang ≥ 90 sur 1 an, dans les 60 dernières séances"),
          ("Taux réel haut", O["decor"]["taux"], f"rang {nb(O['taux_reel_rang'], 0)}/100", O["taux_reel_rang"] / 100, 0.9, "rang ≥ 90 sur 1 an, dans les 60 dernières séances"),
          ("Spéculateurs vendus", O["decor"]["spec"], f"rang {nb(O['spec_rang'], 0)}/100", 1 - O["spec_rang"] / 100, 0.9, "rang ≤ 10 sur 3 ans (CFTC) : barre pleine = spéculateurs au plus bas")]
    r2 = [("Taux réel qui baisse", O["amorce"]["taux"], f"{'+' if vr['taux'] >= 0 else ''}{nb(vr['taux'])} pt", 0.5 + np.clip(-vr["taux"], -0.5, 0.5), 0.5, "variation sur 20 séances < 0 (barre à droite du repère)"),
          ("Volatilité de l'or qui baisse", O["amorce"]["vol"], f"{'+' if vr['vol'] >= 0 else ''}{nb(vr['vol'], 1)} pt", 0.5 + np.clip(-vr["vol"] / 10, -0.5, 0.5), 0.5, "GVZ sur 20 séances < 0"),
          ("Mines meilleures que le S&P", O["amorce"]["gdx_sp"], pc(np.expm1(vr["gdx_sp"])), 0.5 + np.clip(vr["gdx_sp"] * 2.5, -0.5, 0.5), 0.5, "écart GDX − S&P sur 20 séances > 0")]
    for row in (r1, r2):
        for col, x in zip(st.columns(3), row):
            with col: md(cond(*x))
        st.write("")
    g_ = E.get("Mines d'or (GDX)")
    if g_:
        md('<div class="sec">2 · Lecture du marché des mines (GDX) · le S5 et le P4 de GDX ne donnent pas d’ordre (écartés le 17/11 : ils dégradaient la stratégie or)</div>')
        md('<div class="small" style="margin-bottom:8px">Mini-cycle, S5 or (repère, ne pas trader dessus) et carte des prix, calculés sur l’ETF GDX, que tu ne trades pas. Les ordres viennent du point 1 seulement : ne jamais acheter ni vendre l’or sur ces repères.</div>')
        tuiles_marche(g_, repere=True)
        pg = st.segmented_control("Période GDX", ["3 mois", "6 mois", "1 an", "3 ans", "10 ans"], default="1 an", label_visibility="collapsed", key="per_gdx_rep") or "1 an"
        st.plotly_chart(graphique(g_, {"3 mois": 63, "6 mois": 126, "1 an": 252, "3 ans": 756, "10 ans": 2520}[pg]), width="stretch", config=dict(displayModeBar=False))
        m_ = g_["mini"]; EQ = equiv_or(D, g_["date"], {"Fin de correction": m_["niveau_confirmation"], "Non-retour": m_["niveau_non_retour"],
                                                     "Sortie du cycle (A)": g_["A"]["niveau_sortie"], "Bascule en correction": m_["niveau_bascule"]})
        if EQ and EQ["niveaux"]:
            lg = "".join(f'<tr><td>{k}</td><td class="num">{nb(v)}</td><td class="num">{pc(v / EQ["gdx"] - 1)}</td><td class="num">{nb(o, 0)} $</td><td class="num">{pc(o / EQ["or_"] - 1)}</td></tr>'
                         for k, (v, o) in sorted(EQ["niveaux"].items(), key=lambda x: -x[1][0]))
            md(carte(f'<div class="lab">Niveaux de GDX et équivalent or · GDX {nb(EQ["gdx"])} · or {nb(EQ["or_"], 0)} $ · sensibilité β {nb(EQ["beta"])} (250 séances)</div>'
                     f'<table style="width:100%;margin-top:6px"><tr class="small"><td>Niveau</td><td>GDX</td><td>écart</td><td>Or ≈</td><td>écart</td></tr>{lg}</table>'
                     f'<div class="small" style="margin-top:6px">Or ≈ or du jour × (niveau / GDX)^(1/β). Lecture, pas une règle : en krach de liquidité les mines baissent 4 à 10 fois plus que l’or, et le niveau GDX peut tomber sans que l’or atteigne son équivalent.</div>', "card tight"))
            md('<div class="lab" style="margin-top:10px">Cours de l’or avec les niveaux de GDX convertis en or</div>')
            og = D["or"].loc[:g_["date"]].dropna().iloc[-{"3 mois": 63, "6 mois": 126, "1 an": 252, "3 ans": 756, "10 ans": 2520}[pg]:]
            fo = go.Figure(go.Scatter(x=og.index, y=og.values, name="Or", line=dict(color="#fbbf24", width=2), hovertemplate="%{y:,.0f} $<extra>Or</extra>"))
            CL = {"Fin de correction": COUL["ok"], "Non-retour": COUL["warn"], "Sortie du cycle (A)": COUL["bad"], "Bascule en correction": COUL["warn"]}
            prev = None
            for k, (v, o) in sorted(EQ["niveaux"].items(), key=lambda x: x[1][1]):
                proche = prev is not None and abs(o / prev - 1) < 0.02
                fo.add_hline(y=o, line=dict(color=CL.get(k, "#94a3b8"), width=1.4, dash="dash"))
                fo.add_annotation(x=og.index[0] if not proche else og.index[len(og) // 3], y=o, text=f"{k} · or ≈ {nb(o, 0)} $ (GDX {nb(v)})", showarrow=False, xanchor="left",
                                  yanchor="bottom" if not proche else "top", font=dict(color=CL.get(k, "#94a3b8"), size=10.5), bgcolor="rgba(10,15,28,.75)", borderpad=2)
                prev = o
            fo.update_layout(height=360, margin=dict(l=4, r=12, t=6, b=8), showlegend=False, **LAYOUT)
            lo_ = min([og.min()] + [o for _, o in EQ["niveaux"].values()]); hi_ = max([og.max()] + [o for _, o in EQ["niveaux"].values()])
            fo.update_xaxes(showgrid=False, linecolor="#1e293b"); fo.update_yaxes(gridcolor="#1a2438", zeroline=False, range=[lo_ * 0.97, hi_ * 1.03])
            st.plotly_chart(fo, width="stretch", config=dict(displayModeBar=False))
            md('<div class="small">Les niveaux sont ceux de GDX du jour, convertis avec la sensibilité β : ils bougent chaque jour avec GDX et l’or. Même période que le graphique GDX.</div>')
    md('<div class="sec">3 · Signaux d’entrée de la stratégie or et volatilité de l’or</div>')
    per = st.segmented_control("Période or", ["1 an", "3 ans", "10 ans", "Tout"], default="3 ans", label_visibility="collapsed") or "3 ans"
    nj = {"1 an": 252, "3 ans": 756, "10 ans": 2520, "Tout": 10 ** 6}[per]
    g = O["mines"].iloc[-nj:]; pos = O["position"].reindex(g.index); vo = O["vol_or"].reindex(g.index)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.04); inn = pos.values > 0
    if inn.any(): fig.add_trace(go.Scatter(x=g.index, y=np.where(inn, g.values, np.nan), fill="tozeroy", fillcolor="rgba(34,197,94,.10)", line=dict(width=0), name="Stratégie investie", hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=g.index, y=g.values, name="GDX", line=dict(color="#fbbf24", width=2), hovertemplate="%{y:,.2f}<extra>GDX</extra>"), 1, 1)
    sg = [d for d in O["signaux"] if d >= g.index[0]]
    if sg: fig.add_trace(go.Scatter(x=sg, y=g.reindex(sg).values * 0.97, mode="markers", name="Signal d'entrée", marker=dict(color=COUL["ok"], size=14, symbol="triangle-up", line=dict(color="#0a0f1c", width=1.5))), 1, 1)
    fig.add_trace(go.Scatter(x=vo.index, y=vo.values, name="Volatilité de l'or (GVZ)", line=dict(color="#a78bfa", width=1.6)), 2, 1)
    fig.update_layout(height=520, margin=dict(l=8, r=8, t=10, b=8), **LAYOUT)
    fig.update_xaxes(showgrid=False); fig.update_yaxes(gridcolor="#1a2438", zeroline=False); fig.update_yaxes(range=[g.min() * 0.9, g.max() * 1.05], row=1, col=1)
    st.plotly_chart(fig, width="stretch", config=dict(displayModeBar=False))
    md('<div class="sec">Sorties · vendre à la clôture dès que l’une est franchie (une fois investi)</div>')
    nv = O["niveaux"] or {}
    sx = [("Stop de départ", "GDX −10 %", nb(nv.get("stop_depart")) if nv.get("stop_depart") else "—", "tant que GDX n'a pas fait +10 % depuis l'entrée"),
          ("Recul de l'or", "or −13 %", nb(nv.get("or_moins13"), 1) if nv else "—", "depuis son plus haut depuis l'entrée"),
          ("Règle de cycle", "or −15 % + macro", nb(nv.get("or_moins15"), 1) if nv else "—", f"et taux réel ou dollar en hausse sur 63 séances (aujourd'hui : {'oui' if O['macro'] else 'non'})")]
    for col, (a, b_, c_, d_) in zip(st.columns(3), sx):
        with col: md(carte(f'<div class="lab">{a}</div><div class="mid" style="margin-top:4px">{b_}</div><div class="small">niveau : <b class="num" style="color:#e2e8f0">{c_}</b></div><div class="small" style="margin-top:6px">{d_}</div>', "card tight"))
    OT = or_titres(O, D.get("titres"), asof, D.get("Mines d'or (GDX)", pd.Series(dtype=float)).loc[:asof], MARCHES["Mines d'or (GDX)"]["mini"])
    if OT:
        md('<div class="sec">4 · Titres · liste des 5 mines et cœur de 2</div>')
        c1, c2 = st.columns([1, 2.6])
        with c1: md(carte(f'<div class="lab">Position en titres</div><div style="margin:10px 0">{badge(OT["etat"], OT["niveau"], True)}</div><div class="txt">{OT["texte"]}</div>'
                          f'<div class="small" style="margin-top:10px">Composition GDX au {OT["date_compo"]} (déclaration SEC). Part de mines = budget de risque, réparti sur les 2 mines ; le reste en PHYS (or_phys).</div>'))
        th = "".join(f'<th style="white-space:nowrap;text-align:{a};padding:6px 10px;color:#94a3b8;font-size:11px;letter-spacing:.1em;text-transform:uppercase;font-weight:600">{h}</th>'
                     for h, a in [("Titre", "left"), ("Rôle", "left"), ("Bêta", "right"), ("Poids GDX", "right"), ("Cours", "right"), ("20 s.", "right"), ("vs haut 1 an", "right"), ("MM50", "center")])
        def ce(x, a="right", c="#e2e8f0"): return f'<td class="num" style="white-space:nowrap;text-align:{a};padding:7px 10px;color:{c};border-top:1px solid #1e293b">{x}</td>'
        rw = "".join("<tr>" + f'<td style="padding:7px 10px;border-top:1px solid #1e293b;font-weight:700;color:#f8fafc">{l["titre"]}</td>' + f'<td style="padding:7px 10px;border-top:1px solid #1e293b">{chip("CŒUR", "ok") if l["coeur"] else chip("LISTE", "mute")}</td>' + ce(nb(l["beta"], 2)) + ce(nb(l["poids"], 1) + " %") + ce(nb(l["cours"]))
                     + ce(pc(l["r20"]), c=COUL["ok"] if l["r20"] >= 0 else COUL["bad"]) + ce(pc(l["recul"])) + ce("▲ dessus" if l["ma50"] else "▼ dessous", "center", COUL["ok"] if l["ma50"] else COUL["bad"]) + "</tr>" for l in OT["lignes"])
        with c2: md(carte(f'<table style="width:100%;border-collapse:collapse;font-size:13.5px"><tr>{th}</tr>{rw}</table><div class="small" style="margin-top:10px">Choix du trader (17/11/2026) : parmi les 15 plus gros poids, les 5 qui amplifient le plus les mini-corrections de GDX ; cœur = les 2 premiers. Avec le budget mines / PHYS (or_phys, 18/11/2026) : 2022-2026 +40,6 %/an, pire baisse −28 % ; 2013-2026 +20,5 %/an, −36 % (100 % mines : −48 %). Cours en devise locale (.TO Toronto, .AX Sydney, .L Londres).</div>'))
    bloc_mp("Or", "or", "Mines d'or (GDX)", "5 · Matière première · or et rapport mines / or")

with t2:
    choix = [k for k in E if k != "Mines d'or (GDX)"] + ["Or"]
    n = st.segmented_control("Marché", choix, default="NDX" if "NDX" in E else choix[0], format_func=lambda x: COURT[x], label_visibility="collapsed") or "NDX"
    if n == "Or": vue_or()
    else:
        vue_marche(n)
        if n == "Pétrolières (XLE)": bloc_regime_petrole(); bloc_mp("Brent", "brent", n)

# ================================================================ MACRO
with t3:
    md('<div class="txt" style="margin-bottom:10px">Les indicateurs macro de l’outil sur un même axe de temps, avec leurs seuils. Ils ne décident pas seuls : l’interrupteur coût du capital est une règle, le reste (crédit sur marge, concentration, taux réel, dollar) sont des alertes de lecture.</div>')
    nj = PERIODES[st.radio("Période", list(PERIODES), index=2, horizontal=True, key="macro_periode")]
    try:
        figm, last = graphique_macro(nj)
        cards = [("Interrupteur coût du capital", "ACTIF" if last.interrupteur else ("ARMÉ" if last.arme else "ÉTEINT"), "bad" if last.interrupteur else ("warn" if last.arme else "ok"),
                  f"10 ans {'+' if last.taux10_6m >= 0 else ''}{nb(last.taux10_6m)} pt / 6 mois · Fed {'+' if last.fed_12m >= 0 else ''}{nb(last.fed_12m)} pt / 12 mois"),
                 ("Peur · VIX", nb(last.vix, 1), "warn" if last.vix >= last.q80 else "ok", f"80e percentile {nb(last.q80, 1)}"),
                 ("Taux réel · 12 mois", f"{'+' if last.taux_reel_12m >= 0 else ''}{nb(last.taux_reel_12m)} pt", "warn" if last.taux_reel_12m >= SEUIL["taux_reel_12m"] else "ok", "vent contraire au-delà de +0,5 pt"),
                 ("Crédit sur marge", pc(last.get("marge_yoy", np.nan)) if last.get("marge_yoy", np.nan) == last.get("marge_yoy", np.nan) else "—", "warn" if last.get("alerte_marge", False) else "ok",
                  f"recul {last.get('marge_recul', np.nan) * 100:.0f} pts depuis le plus haut 6 mois" if last.get("marge_recul", np.nan) == last.get("marge_recul", np.nan) else ""),
                 inst_13f(),
                 ("Concentration · NDX", pc(last.get("concentration", np.nan)) if last.get("concentration", np.nan) == last.get("concentration", np.nan) else "—", "warn" if C.get("concentration_60") else "ok", "alerte : ≥ +5 pts dans les 60 dernières séances")]
        for col, (lab, val, niv, det) in zip(st.columns(6), cards):
            with col: md(carte(f'<div class="lab">{lab}</div><div class="mid num" style="margin-top:6px;color:{COUL[niv]}">{val}</div><div class="small" style="margin-top:6px">{det}</div>', "card tight"))
        st.plotly_chart(figm, width="stretch", config={"displayModeBar": False})
        md('<div class="small">Comment lire : <b>1</b> le NDX, avec les périodes où l’interrupteur était actif (orange) et où l’alerte crédit était allumée (violet) ; <b>2</b> le VIX au-dessus de son 80e percentile = peur ; <b>3</b> le coût du capital : au-delà de la ligne rouge (+1 pt), l’interrupteur est armé ; <b>4</b> le taux réel (au-delà de +0,5 pt, la tech fait moins bien) et le dollar ; <b>5</b> le crédit sur marge : au-delà de 40 % il s’emballe, un recul de 20 pts depuis son plus haut signale qu’il se retourne ; <b>6</b> la concentration du NDX (au-delà de +5 pts, la hausse tient à quelques géants).</div>')
    except Exception as ex:
        st.info(f"Graphique macro indisponible : {ex}")

# ================================================================ INTERROGER L'HISTORIQUE
with t4:
    md('<div class="txt" style="margin-bottom:10px">Choisis un marché, un signal et une période : tu vois ce qui s’est passé ensuite, chaque fois que le signal est apparu.</div>')
    c1, c2, c3 = st.columns([2, 2, 2])
    mk = c1.multiselect("Marchés", list(E), default=["NDX"] if "NDX" in E else None, format_func=lambda x: COURT[x])
    sg = c2.multiselect("Signaux", sorted(H["signal"].unique()), default=["S5 mini"])
    an_ = c3.slider("Années", 1990, asof.year, (max(1990, asof.year - 4), asof.year))
    c4, c5 = st.columns(2)
    vixmin = c4.slider("VIX minimum le jour du signal", 0, 60, 0)
    retard = c5.toggle("Seulement avec un retard ≥ 3,3 pts sur le S&P (20 séances)")
    q = H[H["marché"].isin(mk or list(E)) & H["signal"].isin(sg or H["signal"].unique()) & H.date.dt.year.between(*an_)].copy()
    if vixmin: q = q[C["vix_serie"].reindex(q.date).values >= vixmin]
    if retard:
        rel = []
        for _, r in q.iterrows():
            s_ = E[r["marché"]]["s"]; spx = E[SP]["s"]; t = s_.index.get_loc(r.date)
            rel.append(np.nan if t < 20 else (s_.iloc[t] / s_.iloc[t - 20] - 1) - (spx.asof(r.date) / spx.asof(s_.index[t - 20]) - 1))
        q = q[np.array(rel) <= SEUIL["retard"]]
    if len(q):
        r20 = q["20 s."].dropna()
        kp = [("Occurrences", str(len(q)), "info"), ("Gain moyen à 20 séances", pc(r20.mean()), "ok" if r20.mean() > 0 else "bad"),
              ("Positifs à 20 séances", pc((r20 > 0).mean(), 0, False), "ok" if (r20 > 0).mean() > 0.5 else "warn"), ("Pire recul moyen (20 s.)", pc(q["pire 20 s."].mean()), "bad")]
        for col, (a, b_, niv) in zip(st.columns(4), kp):
            with col: md(carte(f'<div class="lab">{a}</div><div class="big num" style="color:{COUL[niv]}">{b_}</div>', "card tight counter"))
        g = q.groupby(["marché", "signal"])[["5 s.", "20 s.", "40 s."]].mean().reset_index()
        fig = go.Figure()
        for hz, col in [("5 s.", "#93c5fd"), ("20 s.", "#3b82f6"), ("40 s.", "#1d4ed8")]:
            fig.add_trace(go.Bar(x=[f"{COURT[a]} · {b_}" for a, b_ in zip(g["marché"], g["signal"])], y=g[hz] * 100, name=f"à {hz}", marker_color=col,
                                 text=[pc(x) for x in g[hz]], textposition="outside", hovertemplate="%{y:.1f} %<extra></extra>"))
        fig.update_layout(barmode="group", height=360, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0e1626",
                          font=dict(color="#94a3b8", family="Inter"), legend=dict(orientation="h", y=1.12), yaxis=dict(title="gain moyen (%)", gridcolor="#1a2438", zerolinecolor="#334155"))
        st.plotly_chart(fig, width="stretch", config=dict(displayModeBar=False))
        with st.expander(f"Voir les {len(q)} occurrences"):
            aff = q.copy(); aff["marché"] = aff["marché"].map(COURT); aff["date"] = aff.date.map(jour); aff["prix"] = aff.prix.map(nb)
            for col in ["5 s.", "20 s.", "40 s.", "pire 20 s."]: aff[col] = aff[col].map(pc)
            st.dataframe(aff, hide_index=True, width="stretch", height=380)
            st.download_button("Télécharger (CSV)", q.to_csv(index=False).encode("utf-8"), "signaux.csv", "text/csv")
    else: st.info("Aucun signal pour ces filtres.")
    md('<div class="small" style="margin-top:12px">Un filtre ajouté ici est une piste, pas une loi : il devient une règle après son protocole et sa validation hors échantillon.</div>')
