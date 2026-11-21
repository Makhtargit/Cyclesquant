"""Portefeuille modèle du système, suivi depuis son déploiement (19/11/2026).
Chaque séance : la position et les poids que donnent les règles (portefeuille), le break appliqué
(blocage K2 : pas de part tech nouvelle ; capital modèle à −30 % : tout en cash). La valeur avance avec les clôtures
des titres tenus la veille. Journal : fichiers/journal_modele.csv (écrit par fichiers/journal_modele.py, chaque soir)."""
import os, re, json
import numpy as np, pandas as pd
from . import FICHIERS
from .regles import MARCHES
from .calcul import tout_calculer, etat_break, or_vix
from .titres import titres as calc_titres, or_titres, portefeuille, fige_or_vix

DEPLOIEMENT = pd.Timestamp(os.environ.get("BOUSSOLES_DEPLOIEMENT", "2026-11-19"))   # variable d’environnement : pour les tests seulement
JOURNAL = os.path.join(FICHIERS, "journal_modele.csv")
PARTS = ["SOX", "Logiciel", "NDX", "Or", "Or-VIX"]
TECH = ("SOX", "Logiciel", "NDX")   # K2 ne bloque que la tech ; or et or-VIX libres (k2_or, décision du 21/11/2026)
FRAIS = 0.002            # par unité de poids échangée (mêmes frais que les tests)

def lignes_part(p):
    """[(ticker, part du capital)] pour une part du portefeuille."""
    if not p.get("dedans"): return []
    t = [x for x in p.get("tient", []) if x != "cash"]
    if not t: return []
    if any("(" in x for x in t):                        # or : « CDE (35%) », « PHYS (30%) »
        out = []
        for x in t:
            m = re.match(r"\s*([A-Z0-9.\-]+)\s*\((\d+)\s*%\)", x)
            if m: out.append((m.group(1).replace(".", "-"), p["poids"] * int(m.group(2)) / 100))
        s = sum(w for _, w in out); return [(k, p["poids"] * w / s) for k, w in out] if s else []
    return [(x.replace(".", "-"), p["poids"] / len(t)) for x in t]

def pf_du_jour(D, asof, memoire=4):
    asof_, C, E, O, *_ = tout_calculer(D, pd.Timestamp(asof), memoire)
    TI = calc_titres(E, C, D.get("titres"), asof_)
    mk = "Mines d'or (GDX)"
    OT = or_titres(O, D.get("titres"), asof_, D.get(mk, pd.Series(dtype=float)).loc[:asof_], MARCHES[mk]["mini"]) if O else None
    gdx = D.get(mk, pd.Series(dtype=float)).loc[:asof_]
    ov = fige_or_vix(or_vix(D, asof_, O), O, D.get("titres"), gdx, MARCHES[mk]["mini"]) if O else None
    PF = portefeuille(E, C, TI, OT, O, D.get("titres"), asof_, ov=ov)
    return asof_, PF, E, O, OT

def ligne_journal(D, asof, prec=None):
    """Une ligne du journal : positions du jour après le break, à partir de la ligne précédente."""
    asof_, PF, E, O, OT = pf_du_jour(D, asof)
    B = etat_break(D, asof_) or {}
    tenu_hier = json.loads(prec["positions"]) if prec is not None else {}
    pos = {}
    for n in PARTS:
        p = (PF or {}).get("parts", {}).get(n)
        if not p: continue
        L = lignes_part(p)
        if B.get("actif") and n in TECH and L and not tenu_hier.get(n): L = []   # blocage K2 : aucune part tech nouvelle
        if L: pos[n] = L
    return asof_, pos, B

def valoriser(journal, close, fed=None, exclues=()):
    """Valeur du portefeuille modèle (base 100 au déploiement) à partir du journal et des clôtures.
    exclues : parts que le trader ne trade pas (leur poids reste en cash, les autres gardent leurs poids)."""
    if journal is None or journal.empty: return pd.Series(dtype=float)
    j = journal.sort_values("date").reset_index(drop=True); v = [100.0]; pic = 100.0; coupe = False
    for i in range(1, len(j)):
        d0, d1 = pd.Timestamp(j.date[i - 1]), pd.Timestamp(j.date[i])
        pos0 = {k: L for k, L in json.loads(j.positions[i - 1]).items() if k not in exclues}; pos1 = {k: L for k, L in json.loads(j.positions[i]).items() if k not in exclues}
        r = 0.0; inv = 0.0
        if not coupe:
            for n, L in pos0.items():
                for t, w in L:
                    if t in close and d0 in close.index and d1 in close.index and close.at[d0, t] == close.at[d0, t] and close.at[d1, t] == close.at[d1, t]:
                        r += w * (close.at[d1, t] / close.at[d0, t] - 1); inv += w
        cash = max(0.0, 1 - inv); r += cash * (0.04 / 252)                 # cash ≈ taux Fed (4 %/an)
        w0 = {t: w for L in pos0.values() for t, w in L}; w1 = {t: w for L in pos1.values() for t, w in L}
        r -= FRAIS * sum(abs(w1.get(t, 0) - w0.get(t, 0)) for t in set(w0) | set(w1))
        v.append(v[-1] * (1 + r)); pic = max(pic, v[-1])
        if v[-1] / pic - 1 <= -0.30: coupe = True                          # break : coupe à −30 % du modèle
    return pd.Series(v, index=pd.to_datetime(j.date))

def lire_journal():
    try: return pd.read_csv(JOURNAL)
    except Exception: return pd.DataFrame(columns=["date", "positions", "k2", "exclues"])

def completer(D, journal=None, jusqua=None, max_seances=40):
    """Ajoute au journal les séances manquantes depuis le déploiement (au plus max_seances d'un coup)."""
    j = lire_journal() if journal is None else journal.copy()
    seances = D["vix"].index[(D["vix"].index >= DEPLOIEMENT)]
    if jusqua is not None: seances = seances[seances <= pd.Timestamp(jusqua)]
    faites = set(pd.to_datetime(j.date)) if len(j) else set()
    a_faire = [d for d in seances if d not in faites][:max_seances]
    for d in a_faire:
        prec = j.sort_values("date").iloc[-1] if len(j) else None
        asof_, pos, B = ligne_journal(D, d, prec)
        j = pd.concat([j, pd.DataFrame([dict(date=str(pd.Timestamp(asof_).date()), positions=json.dumps(pos), k2=bool(B.get("actif")))])], ignore_index=True)
    return j.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True), len(a_faire)
