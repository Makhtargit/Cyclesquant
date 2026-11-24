"""Titres de chaque thématique (univers_coeur, coeur_controles, minicycles_titres — 17/11/2026).
Règle : parmi les 15 plus gros poids de l'ETF (NDX : les 15 plus gros volumes en dollars sur 60 séances), les 5 au bêta
en correction le plus élevé ; cœur = les 2 premiers. Liste figée à chaque signal S5 du secteur.
Position (système retenu, en titres, v7.0 du 24/11/2026) : cycle ouvert → le cœur d'un titre (le premier de la liste des 5 au bêta
en correction), figé au dernier S5 (cœur permanent) ; cycle fermé ou hausse effacée (G3) → cash. L'interrupteur coût du capital (X5)
est retiré (optimisation du 24/11/2026 : K2 regarde déjà la hausse des taux)."""
import os
import numpy as np, pandas as pd
from .calcul import zz
from .regles import SEUIL

from . import FICHIERS
ICI = FICHIERS
THEMES = {"SOX": "SOXX", "Logiciel": "IGV", "NDX": "NDX"}

def compositions():
    c = pd.read_csv(os.path.join(ICI, "compositions_actuelles.csv"))
    n = pd.read_csv(os.path.join(ICI, "ndx_membres.csv")); n = n[n.date == n.date.max()]
    return c, sorted(set(n.ticker)), str(c.date.max()), str(n.date.max())

def yahoo(t): return str(t).replace(".", "-")

def beta_corr(px, S, mth, d):
    """Médiane, sur les mini-corrections de l'indice des 2 années avant d, de baisse du titre / baisse de l'indice."""
    SS = S.loc[:d].dropna(); piv = zz(SS, mth)[0]; P_ = [(SS.index[i], ty) for i, ty in piv[1:]]; r = []
    for (a, ta), (b, _) in zip(P_[:-1], P_[1:]):
        if ta == "H" and a >= d - pd.DateOffset(years=2):
            pa, pb = px.asof(a), px.asof(b)
            if pd.notna(pa) and pd.notna(pb): r.append((pb / pa - 1) / (SS[b] / SS[a] - 1))
    return float(np.median(r)) if r else np.nan

def selection(theme, S, mth, d, T, comp, ndx):
    """Liste des 5 (triée par bêta) et bêtas, à la date d."""
    cl, vo = T["close"], T["volume"]
    if theme == "NDX":
        dv = (cl * vo).loc[:d].iloc[-60:].mean()
        cand = [(t, dv.get(yahoo(t), np.nan)) for t in ndx]
    else:
        c = comp[comp.etf == THEMES[theme]]; cand = list(zip(c.ticker, c.poids))
    cand = [(t, w) for t, w in cand if yahoo(t) in cl and pd.notna(w) and cl[yahoo(t)].loc[:d].notna().sum() > 260]
    top = [t for t, _ in sorted(cand, key=lambda x: -x[1])[:15]]; poids = dict(cand)
    b = {t: beta_corr(cl[yahoo(t)], S, mth, d) for t in top}
    L5 = sorted([t for t in top if not np.isnan(b[t])], key=lambda t: -b[t])[:5]
    return L5, b, poids

def pic_hausse_effacee(e, asof):
    """Règle G3 (pic_distribution, 18/11/2026) : dans les 3 séances qui suivent un plus haut de 10 séances, la clôture repasse
    sous la plus basse clôture des 10 séances qui le précédaient → la part passe en cash, jusqu'à une clôture au-dessus du plus haut
    de 10 séances qui précédait le signal, ou jusqu'au prochain S5."""
    s_ = e["s"].loc[:asof].dropna(); h10 = s_.rolling(10).max(); nh = s_ >= h10
    jd = nh.astype(int).groupby(nh.cumsum()).cumcount(); lo_ref = s_.shift(1).rolling(10).min().where(nh).ffill()
    sig = (jd.between(1, 3) & (s_ <= lo_ref)).values; p = s_.values; hh = h10.shift(1).values
    s5 = set(pd.Timestamp(t["entree"]) for t in e["S5"]["trades"]); on = False; seuil = None; d_sig = None
    for i, d in enumerate(s_.index):
        if on and (p[i] > seuil or d in s5): on = False
        if not on and sig[i]: on = True; seuil = hh[i - 2] if i >= 2 else p[i]; d_sig = d
    return dict(actif=on, date=d_sig, seuil=seuil) if on else dict(actif=False, date=None, seuil=None)

def titres(E, C, T, asof, n_coeur=1):
    """Par thématique : état de la position, date de la liste, liste des 5, cœur, mesures par titre."""
    if T is None or T["close"].empty: return {}
    comp, ndx, d_comp, d_ndx = compositions(); out = {}; cl = T["close"].loc[:asof]
    arme = C["taux10_6m"] >= SEUIL["taux10_6m"] or (C["fed_12m"] == C["fed_12m"] and C["fed_12m"] >= 1.0)
    for theme in ["SOX", "Logiciel", "NDX"]:          # SOX avant NDX : le cœur NDX évite les titres du cœur SOX
        if theme not in E: continue
        e = E[theme]; S = e["s"]; mth = e["seuil_mini"]
        tr = e["S5"]["trades"]; en_cours = bool(tr) and tr[-1]["motif"] == "en cours"
        d = pd.Timestamp(tr[-1]["entree"]) if tr else pd.Timestamp(asof)
        if d - cl.index[0] < pd.Timedelta(days=3 * 365):
            out[theme] = dict(dispo=False, raison="historique des titres insuffisant pour cette date"); continue
        L5, b, poids = selection(theme, S, mth, d, dict(close=cl, volume=T["volume"].loc[:asof]), comp, ndx)
        coeur = L5[:n_coeur]
        if theme == "NDX" and "SOX" in out and out["SOX"].get("dispo") and out["SOX"].get("etat") == "CŒUR":
            pris = set(out["SOX"]["coeur"]); coeur = [t for t in L5 if t not in pris][:n_coeur] or coeur
        abri = False; pic = pic_hausse_effacee(e, asof)   # X5 retiré (v7.0)
        if abri: etat, niv, txt = "À L'ABRI", "bad", "Interrupteur coût du capital actif : cash."
        elif pic["actif"]: etat, niv, txt = "CASH · PIC", "bad", f"Hausse des 10 séances effacée en moins de 3 séances (le {pic['date']:%d/%m/%Y}) : cash jusqu’à une clôture au-dessus de {pic['seuil']:,.0f} ou un nouveau S5.".replace(",", " ")
        elif en_cours: etat, niv, txt = "CŒUR", "ok", f"Mini-cycle en cours depuis le {d:%d/%m/%Y} : détenir le cœur."
        elif e["A"]["investie"]: etat, niv, txt = "CŒUR", "ok", f"Cycle ouvert, pas de mini-cycle en cours : garder le cœur du dernier S5 ({d:%d/%m/%Y}) (cœur permanent)."
        else: etat, niv, txt = "CASH", "mute", "Cycle fermé : cash. La liste sera refaite au prochain S5."
        lignes = []
        for t in L5:
            s = cl[yahoo(t)].dropna(); p = s.iloc[-1]
            lignes.append(dict(titre=t, coeur=t in coeur, beta=b[t], poids=poids.get(t), cours=p, depuis=p / s.asof(d) - 1,
                               recul=p / s.iloc[-252:].max() - 1, ma50=bool(p > s.iloc[-50:].mean()), r20=p / s.iloc[-21] - 1))
        out[theme] = dict(dispo=True, etat=etat, niveau=niv, texte=txt, date_liste=d, en_cours=en_cours, coeur=coeur, liste=L5, lignes=lignes,
                          source=f"compositions {THEMES[theme]} du {d_comp}" if theme != "NDX" else f"membres du NDX au {d_ndx}, classés par volume en dollars")
    return out

def peremptions(aujourdhui=None):
    """Liste (libellé, échéance, jours restants) : réglages et fichiers de l'univers."""
    from .regles import PEREMPTION_REGLAGES, PEREMPTION_FICHIERS, PEREMPTION_GDX
    j = pd.Timestamp(aujourdhui or pd.Timestamp.today()).normalize(); out = []
    for lab, d in PEREMPTION_REGLAGES: out.append((lab, pd.Timestamp(d), (pd.Timestamp(d) - j).days))
    for f, (lab, vie) in PEREMPTION_FICHIERS.items():
        try:
            df = pd.read_csv(os.path.join(ICI, f))
            dc = "date" if "date" in df else "dispo"
            groupes = df.groupby("etf").date.max().items() if "etf" in df else [(lab, df[dc].max())]
            for etf, d0 in groupes:
                d0 = pd.Timestamp(d0); v = PEREMPTION_GDX if etf in ("GDX", "XLP") else vie; e = d0 + pd.Timedelta(days=v)
                out.append((f"{'Poids ' + etf if 'etf' in df else lab} (au {d0:%d/%m/%Y})", e, (e - j).days))
        except Exception: out.append((lab + " (fichier illisible)", j, -1))
    return sorted(out, key=lambda x: x[1])

def or_titres(O, T, asof, gdx=None, mth=0.109):
    """Or sans ETF, décision du trader du 17/11/2026 (or_sans_etf) : parmi les 15 plus gros poids de GDX, les 5 au bêta en
    correction le plus élevé (mini-corrections de GDX sur 2 ans) ; cœur = les 2 premiers, détenu quand la stratégie or est investie."""
    if T is None or T["close"].empty or O is None: return None
    comp = compositions()[0]; g = comp[comp.etf == "GDX"].sort_values("poids", ascending=False); cl = T["close"].loc[:asof]
    top = [t for t in g.ticker if yahoo(t) in cl and cl[yahoo(t)].dropna().size > 260][:15]
    if not top: return None
    b = {t: beta_corr(cl[yahoo(t)], gdx, mth, pd.Timestamp(asof)) for t in top} if gdx is not None and len(gdx) else {t: np.nan for t in top}
    L5 = sorted([t for t in top if not np.isnan(b[t])], key=lambda t: -b[t])[:5] or top[:5]; coeur = L5[:2]
    lignes = []
    for t in L5:
        s_ = cl[yahoo(t)].dropna(); p = s_.iloc[-1]
        lignes.append(dict(titre=t, coeur=t in coeur, beta=b[t], poids=float(g[g.ticker == t].poids.iloc[0]), cours=p, r20=p / s_.iloc[-21] - 1,
                           recul=p / s_.iloc[-252:].max() - 1, ma50=bool(p > s_.iloc[-50:].mean())))
    inv = bool(O["investie"]); bm = O["budget"]["part"]
    rep = f"{bm:.0%} en mines ({' · '.join(coeur)}), {1 - bm:.0%} en PHYS"
    return dict(etat="MINES + PHYS" if inv else "CASH", niveau="ok" if inv else "mute", liste=L5, coeur=coeur, lignes=lignes, date_compo=str(g.date.iloc[0]), budget=bm,
                tient=[f"{t} ({bm / 2:.0%})" for t in coeur] + [f"PHYS ({1 - bm:.0%})"],
                texte=f"Stratégie or investie : {rep}." if inv else f"Stratégie or en attente : cash. Au signal d'entrée : {rep} (budget et cœur recalculés ce jour-là).")

def fige_or_vix(ov, O, T, gdx, mth):
    """Cœur de 2 mines figé au jour de l'achat or-VIX (pas de rotation en cours de trade)."""
    if ov and ov.get("actif") and O is not None:
        try:
            ot = or_titres(O, T, ov["entree"], gdx.loc[:ov["entree"]], mth)
            if ot: ov["coeur"] = ot["coeur"]
        except Exception: pass
    return ov

def recalibrages(E):
    """Déclencheur : un marché sorti de son cycle après le dernier recalibrage doit être recalibré (journal de décisions)."""
    from .regles import DATE_CALIBRAGE, MARCHES
    d0 = pd.Timestamp(DATE_CALIBRAGE); out = []
    for n, e in E.items():
        if not MARCHES[n].get("tech") and MARCHES[n]["groupe"] != "or": continue
        ds = e["A"].get("derniere_sortie")
        if ds is not None and ds > d0: out.append((f"Recalibrage requis · {n} (sortie de cycle le {ds:%d/%m/%Y})", ds))
    return out


def phase_temps_reel(s, m):
    """Zigzag au seuil mini lu jour par jour : 1 = mini-hausse, 0 = mini-correction (phases_secteurs)."""
    p = s.dropna().values; h = lo = p[0]; e = 1; out = np.ones(len(p))
    for t in range(len(p)):
        if e == 1:
            h = max(h, p[t])
            if p[t] <= h * (1 - m): e = 0; lo = p[t]
        else:
            lo = min(lo, p[t])
            if p[t] >= lo * (1 + m): e = 1; h = p[t]
        out[t] = e
    return pd.Series(out, index=s.dropna().index)

def portefeuille(E, C, TI, OT, O, T, asof, plancher=0.05, ov=None):
    """Portefeuille du jour : 4 parts. Poids W1 revus en fin de mois (inverse de la volatilité sur 63 séances de ce que chaque part a détenu,
    plancher 5 %, concours_poids), multipliés selon l'état du cycle de la part (allocation_cycles), 50 % au plus par part (25 % pour l'or). Le reste est en cash.
    Le défensif (5 plus gros poids de XLP) est affiché comme poche hors stratégie. Alertes : correction généralisée, dispersion."""
    if T is None or T["close"].empty: return None
    cl = T["close"].loc[:asof]; comp = compositions()[0]; g = comp[comp.etf == "XLP"].sort_values("poids", ascending=False)
    defensif = [t for t in g.ticker if yahoo(t) in cl and cl[yahoo(t)].dropna().size > 260][:5]
    parts = {}
    for n in ["SOX", "Logiciel", "NDX"]:
        if n not in E or n not in TI or not TI[n].get("dispo"): continue
        e = E[n]; pos = e["A"]["position"].copy()
        for tr in e["S5"]["trades"]:
            a_, b_ = pd.Timestamp(tr["entree"]), pd.Timestamp(tr["sortie"]) if tr.get("sortie") is not None else pos.index[-1]
            pos.loc[(pos.index > a_) & (pos.index <= b_)] = 1
        dedans = TI[n]["etat"] == "CŒUR"
        parts[n] = dict(s=e["s"], pos=pos, dedans=dedans, etat=TI[n]["etat"] if dedans else "CASH", tient=TI[n]["coeur"] if dedans else ["cash"])
    mk = "Mines d'or (GDX)"
    if O is not None and OT is not None and mk in E:
        parts["Or"] = dict(s=E[mk]["s"], pos=O["position"], dedans=bool(O["investie"]), etat=OT["etat"], tient=OT["tient"] if O["investie"] else ["cash"], tient_si=OT["tient"])
    # poids : fin du mois précédent la séance analysée (ou la séance même si c'est une fin de mois)
    idx = next(iter(parts.values()))["s"].loc[:asof].index
    a = pd.Timestamp(asof)
    if a.normalize() == (a + pd.offsets.BMonthEnd(0)).normalize(): d_rev = idx[-1]          # la séance est la dernière du mois
    else:
        prec = idx[idx < a.replace(day=1)]; d_rev = prec[-1] if len(prec) else idx[-1]     # sinon : fin du mois précédent
    vols = {}
    for n, p_ in parts.items():
        r = p_["s"].loc[:d_rev].pct_change(); q = p_["pos"].reindex(r.index).ffill().fillna(0).shift(1)
        vols[n] = max((q * r).dropna().iloc[-63:].std() * np.sqrt(252), plancher)
    inv = {n: 1 / v for n, v in vols.items()}; tot = sum(inv.values())
    # allocation_cycles (18/11/2026) : W1 × multiplicateur de l'état du cycle de la part (calculé à la clôture, pour la séance suivante)
    #   cycle porteur (mini-hausse) × 1,5 ; couteau pris par la règle (trade S5 en mini-correction) × 0,5 ; couteau subi (sans S5) × 1 ;
    #   fin de cycle proche (recul ≥ la moitié du seuil de cycle depuis le plus haut du cycle) × 0,5 en plus ; somme investie ramenée à 100 % au plus.
    #   limite de prudence (décision du trader, 18/11/2026) : aucune part au-dessus de 50 % du capital, après le multiplicateur.
    for n, p_ in parts.items():
        p_["poids_w1"] = inv[n] / tot; base = p_["poids_w1"]
        if n == "Or":
            mk_ = "Mines d'or (GDX)"; s_ = E[mk_]["s"].loc[:asof].dropna(); m_ = E[mk_]["seuil_mini"]; th_ = 0.436; trade = False
            pos_ = O["position"].reindex(s_.index).fillna(0); deb = pos_[pos_ == 0].index; d0 = deb[-1] if len(deb) else s_.index[0]
            hi_ = s_.loc[d0:].max() if p_["dedans"] else s_.iloc[-1]
        else:
            e_ = E[n]; s_ = e_["s"].loc[:asof].dropna(); m_ = e_["seuil_mini"]; th_ = e_["seuil_cycle"]; trade = TI[n]["etat"] == "CŒUR"
            hi_ = e_["A"]["niveau_sortie"] / (1 - th_) if e_["A"]["investie"] else s_.iloc[-1]
        hausse = bool(phase_temps_reel(s_, m_).iloc[-1] == 1)
        etat = "porteur" if hausse else ("couteau_s5" if trade or not p_["dedans"] else "couteau")   # une part qui entre le fait sur un creux
        if not p_["dedans"] and n == "Or": etat = "porteur" if hausse else "couteau"
        fin = bool(p_["dedans"] and 1 - s_.iloc[-1] / hi_ >= 0.5 * th_)
        mult = {"porteur": 1.5, "couteau_s5": 0.5, "couteau": 1.0}[etat] * (0.5 if fin else 1.0)
        p_.update(etat_cycle=etat, fin_proche=fin, mult=mult, poids=base * mult)
    som = sum(p_["poids"] for p_ in parts.values() if p_["dedans"])
    if som > 1:
        for p_ in parts.values():
            if p_["dedans"]: p_["poids"] /= som
    #   part or limitée à 25 % tant que la stratégie or n'a pas de trades réels (décision du 19/11/2026, limite_or : coût −2,6 pts/an).
    for n, p_ in parts.items(): p_["poids"] = min(p_["poids"], 0.25 if n == "Or" else 0.50)
    #   or-VIX (20/11/2026) : mines après une panique du VIX, 15 % au plus, dans la limite or de 25 %, pris sur le cash ; hors W1.
    if ov is not None and OT is not None and mk in E:
        w_or = parts["Or"]["poids"] if "Or" in parts and parts["Or"]["dedans"] else 0.0
        cash_ = 1 - sum(p_["poids"] for p_ in parts.values() if p_["dedans"])
        w_ = max(0.0, min(0.15, 0.25 - w_or, cash_)); tient = [f"{t} (50%)" for t in (ov.get("coeur") or OT["coeur"])]
        actif = bool(ov["actif"]) and w_ > 0
        parts["Or-VIX"] = dict(s=E[mk]["s"], pos=None, dedans=actif, etat="MINES · VIX" if actif else "CASH", tient=tient if actif else ["cash"], tient_si=tient,
                               poids=w_ if actif else min(0.15, 0.25 - w_or), etat_cycle="", fin_proche=False, mult=1.0, ov=ov)
    part_cash = 1 - sum(p_["poids"] for p_ in parts.values() if p_["dedans"])
    ph = {n: phase_temps_reel(E[n]["s"].loc[:asof], E[n]["seuil_mini"]).iloc[-1] for n in ["SOX", "Logiciel", "NDX"] if n in E}
    n_corr = int(sum(1 - v for v in ph.values()))
    arme = C["taux10_6m"] >= SEUIL["taux10_6m"] or (C["fed_12m"] == C["fed_12m"] and C["fed_12m"] >= 1.0)
    inter = False   # X5 retiré (v7.0) : plus de mise à l'abri sur le coût du capital
    disp = []
    for n in ["SOX", "Logiciel", "NDX"]:
        if n not in E: continue
        s_ = E[n]["s"].loc[:asof]; h21 = s_.iloc[-21:].max(); disp.append((s_.iloc[-1] <= h21 * (1 - E[n]["seuil_mini"]), s_.iloc[-1] >= h21))
    dispersion = any(a for a, _ in disp) and any(b for _, b in disp)
    return dict(parts=parts, defensif=defensif, part_cash=part_cash, date_poids=d_rev, n_corr=n_corr, phases=ph, interrupteur=inter, dispersion=dispersion,
                date_xlp=str(g.date.iloc[0]) if len(g) else "")
