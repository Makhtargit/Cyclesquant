"""Comportement des titres (protocole_comportement_titres.md, 19/11/2026).

À lancer sur ton ordinateur, depuis le dossier de l'application :
    python fichiers/comportement_titres.py
Résultat : fichiers/comportement_titres_resultats.csv et comportement_titres_horaire.csv.
Envoie-moi ces deux fichiers (ou le zip créé à côté) : je fais la lecture.
Option : python fichiers/comportement_titres.py --test  (données fictives, pour vérifier que le script tourne).
"""
import sys, zipfile, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

ICI = Path(__file__).resolve().parent
COEURS = ["MRVL", "MU", "APP", "ORCL", "TSLA", "AMD", "CDE", "GFI"]
SUIVI = ["LEU", "NVDA", "AVGO", "NBIS", "WPM", "GOOGL", "META", "PAAS", "AU", "AGI", "NOW", "DDOG", "CRM", "LRCX",
         "MPWR", "INTC", "AEM", "XOM", "COP", "CVX", "WMT", "COST"]
REPERES = ["^NDX", "^SOX", "IGV", "GDX"]
TOUS = COEURS + SUIVI + REPERES
FEN = {"10 ans": ("2016-01-01", "2100-01-01"), "2016-2021": ("2016-01-01", "2021-12-31"), "2022-2026": ("2022-01-01", "2100-01-01")}

# ---------------------------------------------------------------- données
def faux_journalier(t, n=2750):
    rng = np.random.default_rng(abs(hash(t)) % 2**32); ix = pd.bdate_range(end="2026-11-18", periods=n)
    r = rng.normal(0.0008, 0.025, n); c = 100 * np.exp(np.cumsum(r)); o = c * np.exp(rng.normal(0, 0.01, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.01, n))); l = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.01, n)))
    return pd.DataFrame(dict(Open=o, High=h, Low=l, Close=c, Volume=rng.integers(1e5, 1e7, n)), index=ix)

def faux_horaire(t):
    d = faux_journalier(t, 500); rows = []
    for day, x in d.iterrows():
        for k in range(7):
            ts = pd.Timestamp(day) + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(hours=k)
            rows.append((ts, x.Open * (1 + 0.002 * np.sin(k)), x.Open * 1.003, x.Open * 0.997, x.Open * (1 + 0.002 * np.cos(k))))
    return pd.DataFrame(rows, columns=["ts", "Open", "High", "Low", "Close"]).set_index("ts")

def charge(test):
    if test: return {t: faux_journalier(t) for t in TOUS}, {t: faux_horaire(t) for t in TOUS}
    import yfinance as yf
    J, H = {}, {}
    for t in TOUS:
        try:
            d = yf.download(t, period="11y", interval="1d", auto_adjust=True, progress=False)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            J[t] = d.dropna(subset=["Open", "Close"])
            h = yf.download(t, period="730d", interval="60m", auto_adjust=True, prepost=False, progress=False)
            if isinstance(h.columns, pd.MultiIndex): h.columns = h.columns.get_level_values(0)
            if len(h): h.index = h.index.tz_convert("America/New_York").tz_localize(None)
            H[t] = h.dropna(subset=["Open", "Close"])
            print(f"{t:6s} journalier {len(J[t])} séances · horaire {len(H[t])} barres")
        except Exception as e:
            print(f"{t:6s} ÉCHEC : {e}")
    return J, H

# ---------------------------------------------------------------- mesures
def ann(x):
    x = x.dropna(); return (1 + x).prod() ** (252 / max(len(x), 1)) - 1 if len(x) else np.nan

def zigzag_hausses(c, seuil):
    """Jambes de hausse sur les clôtures : (creux, sommet)."""
    jambes, mode, ext_i = [], None, 0
    v = c.values
    for i in range(1, len(v)):
        if mode is None:
            if v[i] >= v[ext_i] * (1 + seuil): mode, lo_i, ext_i = "haut", ext_i, i
            elif v[i] <= v[ext_i] * (1 - seuil): mode, ext_i = "bas", i
            elif (v[i] < v[ext_i]): ext_i = i
        elif mode == "haut":
            if v[i] > v[ext_i]: ext_i = i
            elif v[i] <= v[ext_i] * (1 - seuil): jambes.append((lo_i, ext_i)); mode, ext_i = "bas", i
        else:
            if v[i] < v[ext_i]: ext_i = i
            elif v[i] >= v[ext_i] * (1 + seuil): mode, lo_i, ext_i = "haut", ext_i, i
    return jambes

def rsi(c, n=14):
    d = c.diff(); u = d.clip(lower=0).ewm(alpha=1 / n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n).mean()
    return 100 - 100 / (1 + u / dn)

def mesures(d, a, b):
    d = d.copy(); C, O, H, L, V = d.Close, d.Open, d.High, d.Low, d.Volume
    d["nuit"] = O / C.shift() - 1; d["seance"] = C / O - 1; d["jour"] = C / C.shift() - 1
    d["atr"] = ((H - L) / C.shift()).rolling(20).median()
    d["bas10"] = L.shift().rolling(10).min(); d["balayage"] = (L < d.bas10) & (C > d.bas10)
    d["f5"] = C.shift(-5) / C - 1; d["f10"] = C.shift(-10) / C - 1
    d["pos"] = ((C - L) / (H - L)).where(H > L); d["vol_rel"] = V / V.rolling(20).median()
    d["ecart_m20"] = C / C.rolling(20).mean() - 1; d["rsi"] = rsi(C); d["m50"] = C > C.rolling(50).mean()
    x = d.loc[a:b].iloc[1:]
    if len(x) < 200: return None
    out = {}
    # 1. nuit / séance
    out["nuit_an"] = ann(x.nuit); out["seance_an"] = ann(x.seance); out["total_an"] = ann(x.jour)
    lt = np.log1p(x.jour).sum(); out["part_gain_nuit"] = np.log1p(x.nuit).sum() / lt if abs(lt) > 1e-9 else np.nan
    out["nuit_positive"] = (x.nuit > 0).mean(); out["seance_positive"] = (x.seance > 0).mean()
    # 2. gaps
    g = x.nuit; out["gap_1pc"] = (g.abs() > 0.01).mean(); out["gap_2pc"] = (g.abs() > 0.02).mean()
    gu, gd = x[g > 0.01], x[g < -0.01]
    pc = d.Close.shift()
    out["gap_haut_comble"] = (gu.Low <= pc.reindex(gu.index)).mean() if len(gu) else np.nan
    out["gap_bas_comble"] = (gd.High >= pc.reindex(gd.index)).mean() if len(gd) else np.nan
    g2 = x[g > 0.02]; out["apres_gap_haut2_seance"] = g2.seance.mean() if len(g2) else np.nan
    out["apres_gap_haut2_f5"] = g2.f5.mean() if len(g2) else np.nan
    # 3. balayage
    s = x[x.balayage]; out["balayage_freq"] = x.balayage.mean()
    out["balayage_f5"] = s.f5.mean(); out["balayage_f10"] = s.f10.mean(); out["tous_f5"] = x.f5.mean(); out["tous_f10"] = x.f10.mean()
    out["balayage_f10_positif"] = (s.f10 > 0).mean(); out["tous_f10_positif"] = (x.f10 > 0).mean()
    # 4. moment d'entrée après une séance rouge en tendance
    idx = x.index[(x.Close < x.Open) & x.m50]; pos = [d.index.get_loc(i) for i in idx if d.index.get_loc(i) + 11 < len(d)]
    if pos:
        sortie = d.Close.values[[p + 10 for p in pos]]
        out["entree_clotureJ"] = np.mean(sortie / d.Close.values[pos] - 1)
        out["entree_ouvertureJ1"] = np.mean(sortie / d.Open.values[[p + 1 for p in pos]] - 1)
        out["entree_clotureJ1"] = np.mean(sortie / d.Close.values[[p + 1 for p in pos]] - 1)
        out["n_seances_rouges"] = len(pos)
    # 5 et 6. jambes de hausse
    seuil = max(0.08, 3 * float(d.atr.loc[a:b].median()))
    jambes = [(i, j) for i, j in zigzag_hausses(d.Close, seuil) if a <= str(d.index[i].date()) <= b and j - i >= 2]
    out["seuil_jambe"] = seuil; out["n_jambes"] = len(jambes)
    if jambes:
        J = d.iloc[[i for i, _ in jambes]]; Jm1 = d.iloc[[i - 1 for i, _ in jambes if i > 0]]
        for nom, z in (("J", J), ("veille", Jm1)):
            out[f"{nom}_rouge"] = (z.Close < z.Open).mean(); out[f"{nom}_pos_cloture"] = z.pos.mean()
            out[f"{nom}_vol_rel"] = z.vol_rel.median(); out[f"{nom}_gap"] = z.nuit.mean()
            out[f"{nom}_balayage"] = z.balayage.mean(); out[f"{nom}_ecart_m20"] = z.ecart_m20.median(); out[f"{nom}_rsi"] = z.rsi.median()
        out["tous_rouge"] = (x.Close < x.Open).mean(); out["tous_pos_cloture"] = x.pos.mean(); out["tous_vol_rel"] = x.vol_rel.median()
        out["tous_balayage"] = x.balayage.mean(); out["tous_ecart_m20"] = x.ecart_m20.median(); out["tous_rsi"] = x.rsi.median()
        out["depart_precede_balayage"] = np.mean([bool(d.balayage.iloc[i] or d.balayage.iloc[max(i - 1, 0)]) for i, _ in jambes])
        forme = []
        for i, j in jambes:
            r = d.jour.iloc[i + 1:j + 1]; gain = d.Close.iloc[j] / d.Close.iloc[i] - 1; lr = np.log1p(r)
            c = d.Close.iloc[i:j + 1]; dd = c / c.cummax() - 1; atr = d.atr.iloc[i] if d.atr.iloc[i] == d.atr.iloc[i] else 0.03
            replis = int(((dd < -1.5 * atr) & (dd.shift(-1).fillna(0) >= dd)).sum())
            forme.append(dict(gain=gain, duree=j - i, part_meilleure=lr.max() / np.log1p(gain) if gain > 0 else np.nan, replis=replis,
                              seances_hausse=(r > 0).mean(), efficacite=np.log1p(gain) / lr.abs().sum(), part_nuit=np.log1p(d.nuit.iloc[i + 1:j + 1]).sum() / np.log1p(gain)))
        f = pd.DataFrame(forme)
        for k in f.columns: out[f"jambe_{k}"] = f[k].median()
        out["jambes_explosives"] = (f.part_meilleure >= 0.4).mean()
    return out

def horaire(h):
    if h is None or len(h) < 100: return None
    h = h.copy(); h["jour"] = h.index.normalize(); h["heure"] = h.index.strftime("%H:%M")
    h["r"] = h.Close / h.Open - 1
    out = {f"r_{k}": v for k, v in h.groupby("heure").r.mean().items()}
    ib = h.groupby("jour").apply(lambda z: z.Low.values.argmin()); ih = h.groupby("jour").apply(lambda z: z.High.values.argmax())
    n = h.groupby("jour").size().median()
    out["bas_1re_heure"] = (ib == 0).mean(); out["bas_derniere_heure"] = (ib == n - 1).mean()
    out["haut_1re_heure"] = (ih == 0).mean(); out["haut_derniere_heure"] = (ih == n - 1).mean()
    out["jours"] = h.jour.nunique()
    return out

def main():
    test = "--test" in sys.argv
    J, H = charge(test)
    lignes, lh = [], []
    for t in TOUS:
        if t not in J: continue
        for f, (a, b) in FEN.items():
            m = mesures(J[t], a, b)
            if m: lignes.append(dict(titre=t, groupe="cœur" if t in COEURS else ("repère" if t in REPERES else "suivi"), fenetre=f, **m))
        m = horaire(H.get(t))
        if m: lh.append(dict(titre=t, **m))
    R = pd.DataFrame(lignes); RH = pd.DataFrame(lh)
    f1, f2 = ICI / "comportement_titres_resultats.csv", ICI / "comportement_titres_horaire.csv"
    R.round(5).to_csv(f1, index=False); RH.round(6).to_csv(f2, index=False)
    with zipfile.ZipFile(ICI / "comportement_titres.zip", "w") as z: z.write(f1, f1.name); z.write(f2, f2.name)
    print(f"\nFini : {len(R)} lignes, {len(RH)} titres en horaire. Envoie-moi fichiers/comportement_titres.zip")
    if not R.empty:
        v = R[R.fenetre == "10 ans"].set_index("titre")[["nuit_an", "seance_an", "part_gain_nuit", "gap_2pc", "jambes_explosives"]]
        print((v * 100).round(1).to_string())

if __name__ == "__main__":
    main()
