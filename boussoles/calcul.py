"""Calcul des boussoles : mêmes règles que les dossiers SCANOPTIMUS9 (voir regles.py et les docs du projet)."""
import numpy as np, pandas as pd
from .regles import MARCHES, SEUIL, SP, REGLAGES, duree_attendue_mini

def nb(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
def pc(x, d=1, signe=True):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    return (f"{x * 100:+.{d}f} %" if signe else f"{x * 100:.{d}f} %").replace(".", ",")

DEBUT_A = pd.Timestamp("1990-06-01")

def on(idx, s):
    """Série s alignée sur les séances idx (dernière valeur connue)."""
    s = s.dropna(); return s.reindex(idx.union(s.index)).ffill().reindex(idx)

def front(b):
    """Premier jour de chaque série de True."""
    b = b.fillna(False).astype(bool); return b & ~b.shift(1, fill_value=False)

# ---------------------------------------------------------------- cycles et mini-cycles
def zz(s, th):
    """Zigzag : pivots (indice, 'B' creux / 'H' pic) au seuil th ; renvoie (pivots, mode en cours, extrême en cours)."""
    v = s.values; piv = [(0, "B")]; mode = "up"; ext = 0
    for t in range(1, len(v)):
        if mode == "up":
            if v[t] > v[ext]: ext = t
            if v[t] <= v[ext] * (1 - th): piv.append((ext, "H")); mode = "down"; ext = t
        else:
            if v[t] < v[ext]: ext = t
            if v[t] >= v[ext] * (1 + th): piv.append((ext, "B")); mode = "up"; ext = t
    if len(piv) > 1: piv[0] = (int(np.argmin(v[:piv[1][0] + 1])), "B")
    return piv, mode, ext

def sig7(s, vix, sp, th, mth, est_sp):
    """Signal S7 des cycles (entrée de la stratégie A)."""
    idx = s.index; v = on(idx, vix); spx = on(idx, sp)
    dd = s / s.rolling(250, min_periods=100).max() - 1; crash = (dd <= -th).astype(float).rolling(60, min_periods=1).max() > 0
    vpk = v.rolling(20).max(); S1 = (crash & (vpk >= SEUIL["vix_s7"]) & (v <= SEUIL["reflux"] * vpk)).fillna(False)
    S1r = S1.astype(float).rolling(60, min_periods=1).max() > 0
    lo60 = s.rolling(60).min(); rel = pd.Series(True, index=idx) if est_sp else (s / spx) > (s / spx).shift(20)
    age = s.rolling(60).apply(lambda x: 59 - int(np.argmin(x)), raw=True)
    return (S1r & (s >= lo60 * (1 + mth)) & rel & (age >= 10)).fillna(False)

def strategie_A(s, S7, th, fin=None):
    """Entrée sur S7 (20 séances au moins après la dernière sortie), sortie à −1 seuil de cycle du plus haut depuis l'entrée.
    fin = date de sortie forcée (mécanisme de fin de cycle déclarée, inutilisé depuis le 20/11/2026)."""
    p = s.values; sg = S7.values; pos = np.zeros(len(p)); w = 0; last_exit = -999; hi = None; trades = []; fin = pd.Timestamp(fin) if fin else None
    for t in range(len(p)):
        if s.index[t] < DEBUT_A: continue
        if w == 0:
            if sg[t] and t - last_exit >= 20: w = 1; hi = p[t]; trades.append([s.index[t], p[t], None, None])
        else:
            hi = max(hi, p[t])
            if p[t] <= hi * (1 - th) or (fin is not None and s.index[t] >= fin and trades[-1][0] < fin):
                w = 0; last_exit = t; trades[-1][2:] = [s.index[t], p[t]]
        pos[t] = w
    return pd.Series(pos, index=s.index), trades, hi

def sigS5(s, vix, sp, mth, est_sp, R=None):
    """Signal de creux S5 : E1 (prix) et S5 = E1 + peur. R = réglage du groupe (regles.REGLAGES) ; None = réglage 1990-2009."""
    R = R or dict(k=1.0, q=SEUIL["vix_q"], rf=SEUIL["reflux"], r=0.25, rel=True)
    idx = s.index; v = on(idx, vix); spx = on(idx, sp)
    crash = ((s / s.rolling(21).max() - 1) <= -R["k"] * mth).astype(float).rolling(5, min_periods=1).max() > 0
    vm = v.rolling(5).max(); fear = vm >= v.rolling(250, min_periods=125).quantile(R["q"])
    if R["rf"]: fear &= v <= R["rf"] * vm
    rel = pd.Series(True, index=idx) if (est_sp or not R["rel"]) else (s / spx) > (s / spx).shift(5)
    E1 = (crash & (s >= s.rolling(5).min() * (1 + R["r"] * mth)) & rel).fillna(False)
    return E1, (E1 & fear).fillna(False)

def trades_S5(s, E, mth):
    """Gestion validée : sortie si clôture sous le plus bas des 5 séances avant le signal (couteau), sinon à la fin de la mini-hausse (−1 seuil mini du plus haut)."""
    p = s.values; e = E.values; inn = False; tr = []
    for t in range(len(p)):
        if s.index[t] < DEBUT_A or t < 5: continue
        if not inn:
            if e[t]: inn = True; ep = p[t]; hi = p[t]; lo5 = p[t - 4:t + 1].min(); t0 = t
        else:
            hi = max(hi, p[t]); why = "couteau" if p[t] < lo5 else ("fin de mini-hausse" if p[t] <= hi * (1 - mth) else "")
            if why: inn = False; tr.append(dict(entree=s.index[t0], sortie=s.index[t], resultat=p[t] / ep - 1 - 0.002, motif=why, seances=t - t0))
    if inn: tr.append(dict(entree=s.index[t0], sortie=None, resultat=p[-1] / ep - 1, motif="en cours", seances=len(p) - 1 - t0))
    return tr

def sigP4(s, vix, sp, est_sp, R=None):
    """Signal de pic P4. R = réglage du groupe (regles.REGLAGES) ; None = réglage 1990-2009."""
    R = R or dict(q=SEUIL["p4_vitesse"], reveil=SEUIL["p4_reveil"], rel=True)
    idx = s.index; v = on(idx, vix); spx = on(idx, sp); r20 = s / s.shift(20) - 1
    F2 = r20.rolling(250, min_periods=125).rank(pct=True); F5 = v / v.rolling(20).min()
    F6 = pd.Series(1.0, index=idx) if (est_sp or not R["rel"]) else r20 - (spx / spx.shift(20) - 1)
    q = R["q"]
    P4 = ((F2.rolling(10, min_periods=1).max() >= q) & ((F6 > 0) & (F2 >= q)).astype(float).rolling(10, min_periods=1).max().gt(0) & (F5 >= R["reveil"])).fillna(False)
    return P4, F2

def e80(vix):
    """Premiers franchissements du 80e percentile du VIX (après 10 séances en dessous)."""
    q80 = vix.rolling(250).quantile(SEUIL["vix_q"]); ab = (vix >= q80).values
    return [vix.index[t] for t in range(10, len(vix)) if ab[t] and not ab[t - 10:t].any()], q80

# ---------------------------------------------------------------- taux, dollar
def taux_reel_tech(dfii10, dgs10, cpi):
    """Convention des dossiers tech : DGS10 − inflation sur 1 an avant 2003, DFII10 ensuite."""
    c = cpi.copy(); c.index = c.index + pd.offsets.MonthBegin(1); infl = (c / c.shift(12) - 1) * 100
    prox = dgs10 - on(dgs10.index, infl)
    return pd.concat([prox.loc[:"2003-01-01"], dfii10.loc["2003-01-02":]]).dropna()

def taux_reel_or(dfii10, dgs10, cpi):
    """Convention du dossier or : DFII10, prolongé avant 2003 par DGS10 − inflation (publiée avec 2 mois de retard)."""
    yoy = (cpi / cpi.shift(12) - 1) * 100; yoy.index = yoy.index + pd.offsets.MonthBegin(2)
    return dfii10.combine_first((dgs10 - on(dgs10.index, yoy)).loc[:"2002-12-31"]).dropna()

def climat(D, asof):
    v = D["vix"].loc[:asof]; E, q80 = e80(v)
    rr = taux_reel_tech(D["dfii10"], D["dgs10"], D["cpi"]).loc[:asof]; dgs = D["dgs10"].loc[:asof]
    usd = D["usd_large"].loc[:asof]; u10 = (usd / usd.shift(10) - 1).dropna()
    rr12 = rr.iloc[-1] - rr.loc[:rr.index[-1] - pd.DateOffset(years=1)].iloc[-1]
    t6 = dgs.iloc[-1] - dgs.loc[:dgs.index[-1] - pd.DateOffset(months=6)].iloc[-1]
    ff = D.get("fedfunds", pd.Series(dtype=float)).loc[:asof].dropna()
    ff12 = (ff.iloc[-1] - ff.loc[:ff.index[-1] - pd.DateOffset(months=12)].iloc[-1]) if len(ff) > 13 else np.nan
    ew = D.get("ndx_ew", pd.Series(dtype=float)).loc[:asof].dropna(); conc, conc60 = np.nan, False
    if len(ew) > 130:
        nd = on(ew.index, D["NDX"]); e6 = (nd / nd.shift(126) - 1) - (ew / ew.shift(126) - 1); conc = e6.iloc[-1]; conc60 = bool((e6.iloc[-60:] >= 0.05).any())
    mg = D.get("marge", pd.Series(dtype=float)).dropna(); mg_yoy = mg_recul = np.nan; mg_actif = False; mg_mois = None; mg_dernier = None
    if len(mg) > 20:
        yoy = mg.pct_change(12); rec = yoy.rolling(6).max() - yoy; dispo = mg.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=24)
        ok = dispo <= pd.Timestamp(asof)
        if ok.any():
            j = np.where(ok)[0][-1]; mg_yoy, mg_recul, mg_mois = yoy.iloc[j], rec.iloc[j], mg.index[j]
            nd = D["NDX"].loc[:asof].dropna(); pres = nd.iloc[-1] >= nd.iloc[-250:].max() * 0.95
            mg_actif = bool(mg_recul >= 0.20 and pres)
            # dernier allumage (crédit retourné et NDX près du plus haut), lu mois par mois
            ndm = nd.resample("ME").last(); hm = nd.rolling(250, min_periods=200).max().resample("ME").last()
            for i in range(j, max(j - 60, 0), -1):
                d_ = dispo[i]; x = ndm.asof(d_); h = hm.asof(d_)
                if rec.iloc[i] >= 0.20 and x == x and h == h and x >= 0.95 * h: mg_dernier = d_; break
    return dict(marge_yoy=mg_yoy, marge_recul=mg_recul, marge_actif=mg_actif, marge_mois=mg_mois, marge_dernier=mg_dernier,
                fed=ff.iloc[-1] if len(ff) else np.nan, fed_12m=ff12, concentration=conc, concentration_60=conc60,vix=v.iloc[-1], vix_q80=q80.iloc[-1], vix_rang=v.rolling(250).rank(pct=True).iloc[-1], vix_sur_bas20=v.iloc[-1] / v.rolling(20).min().iloc[-1],
                vix_max5=v.iloc[-5:].max(), vix_pic20=v.iloc[-20:].max(), dernier_e80=E[-1] if E else None, seances_depuis_e80=len(v.loc[E[-1]:]) - 1 if E else None,
                taux_reel=rr.iloc[-1], taux_reel_12m=rr12, date_taux=rr.index[-1], taux10=dgs.iloc[-1], taux10_6m=t6,
                dollar_10s=u10.iloc[-1], dollar_ruee_20s=bool((u10.iloc[-20:] >= SEUIL["ruee_dollar"]).any()), date_dollar=u10.index[-1],
                e80_dates=E, vix_serie=v, q80_serie=q80)

# ---------------------------------------------------------------- état d'un marché
def etat_break(D, asof):
    """Break du trader (break.md, 19/11/2026 ; K2 hebdomadaire depuis le 20/11/2026, k2_frequence · k2_duree).
    Blocage K2 : le S&P clôture une semaine (vendredi) sous sa moyenne 40 semaines ET le décor de taux est allumé
    (10 ans ≥ +1 pt / 6 mois, Fed ≥ +1 pt / 12 mois ou taux réel ≥ +0,5 pt / 12 mois) → aucune nouvelle entrée ;
    levée après 8 clôtures hebdomadaires de suite au-dessus de la moyenne 40 semaines, ou 2 si le décor de taux est éteint ce vendredi
    (levée rapide, k2_levee_taux, décision du trader du 20/11/2026). La coupe à −30 % se lit sur le capital réel."""
    sp = D[SP].loc[:asof].dropna()
    if len(sp) < 260: return None
    ix = sp.index; t10 = D["dgs10"].reindex(ix).ffill(); rr = D["dfii10"].reindex(ix).ffill()
    ff = D.get("fedfunds", pd.Series(dtype=float)).dropna()
    f12 = (ff - ff.shift(12)).reindex(ix, method="ffill") if len(ff) > 13 else pd.Series(np.nan, index=ix)
    v10, vf, vr = t10 - t10.shift(126), f12, rr - rr.shift(252)
    decor = (v10 >= SEUIL["taux10_6m"]) | (vf >= 1.0) | (vr >= SEUIL["taux_reel_12m"])
    fw = sp.groupby(pd.Grouper(freq="W-FRI")).tail(1)
    d_ = fw.index[-1]; complet = (d_ + pd.offsets.BDay(1)).to_period("W-FRI") != d_.to_period("W-FRI")
    fw_c = fw if complet else fw.iloc[:-1]                      # la semaine en cours ne compte qu'une fois clôturée
    m40 = fw_c.rolling(40).mean(); on_ = False; ab = 0; depuis = None
    for d in fw_c.index:
        if np.isnan(m40[d]): continue
        b = fw_c[d] < m40[d]; ab = 0 if b else ab + 1
        if not on_ and b and bool(decor[d]): on_ = True; depuis = d
        elif on_ and ab >= (8 if bool(decor[d]) else 2): on_ = False; depuis = None
    m40_proj = m40.iloc[-1] if complet else pd.concat([fw_c.iloc[-39:], sp.iloc[-1:]]).mean()     # moyenne 40 semaines si la semaine clôturait aujourd'hui
    return dict(actif=on_, depuis=depuis, semaines_au_dessus=ab, semaines_requises=8 if bool(decor.iloc[-1]) else 2, sp=sp.iloc[-1], m40=m40_proj, ecart=sp.iloc[-1] / m40_proj - 1,
                decor=bool(decor.iloc[-1]), taux10_6m=v10.iloc[-1], fed_12m=vf.iloc[-1], taux_reel_12m=vr.iloc[-1],
                derniere_fin=fw_c.index[-1], sous_m40_fin=bool(fw_c.iloc[-1] < m40.iloc[-1]))

def k2_mensuel(D, asof):
    """Ancien K2 (moyenne 10 mois en clôture mensuelle, levée après 2 fins de mois) : affiché pour comparaison jusqu'à la révision de 2028 (k2_frequence)."""
    sp = D[SP].loc[:asof].dropna()
    if len(sp) < 260: return None
    ix = sp.index; t10 = D["dgs10"].reindex(ix).ffill(); rr = D["dfii10"].reindex(ix).ffill()
    ff = D.get("fedfunds", pd.Series(dtype=float)).dropna()
    f12 = (ff - ff.shift(12)).reindex(ix, method="ffill") if len(ff) > 13 else pd.Series(np.nan, index=ix)
    decor = ((t10 - t10.shift(126)) >= SEUIL["taux10_6m"]) | (f12 >= 1.0) | ((rr - rr.shift(252)) >= SEUIL["taux_reel_12m"])
    fm = sp.groupby([ix.year, ix.month]).tail(1); d_ = fm.index[-1]
    fm_c = fm if ((d_ + pd.offsets.BMonthEnd(0)) - d_).days <= 1 else fm.iloc[:-1]
    m10 = fm_c.rolling(10).mean(); on_ = False; ab = 0
    for d in fm_c.index:
        if np.isnan(m10[d]): continue
        b = fm_c[d] < m10[d]; ab = 0 if b else ab + 1
        if not on_ and b and bool(decor[d]): on_ = True
        elif on_ and ab >= 2: on_ = False
    m10p = pd.concat([fm_c.iloc[-9:], sp.iloc[-1:]]).mean()
    return dict(actif=on_, m10=m10p, ecart=sp.iloc[-1] / m10p - 1, derniere_fin=fm_c.index[-1])

def or_vix(D, asof, O=None, fenetre=600):
    """Mines après une panique du VIX (or_vix · or_vix_sortie · or_vix_risque · or_vix_fraction ; décision du trader du 20/11/2026).
    Déclencheur : le VIX a atteint 30 dans les 20 dernières séances puis reflue sous 85 % de ce pic. Achat à la clôture du jour du
    déclencheur, si la part or n'est pas investie et si K2 est éteint. Sortie 126 séances après l'achat, ou si GDX perd 25 % depuis l'achat.
    Taille : 15 % du capital au plus, dans la limite or de 25 %. Mesuré sur GDX ; détenu en cœur de 2 mines."""
    g = D.get("Mines d'or (GDX)", pd.Series(dtype=float)).loc[:asof].dropna(); v = D["vix"].loc[:asof].dropna()
    if len(g) < 300 or len(v) < 300: return None
    idx = g.index; vv = v.reindex(idx).ffill(); vpk = vv.rolling(20).max(); trig = ((vpk >= 30) & (vv <= 0.85 * vpk)).fillna(False).values
    pos_or = (O["position"].reindex(idx).ffill().fillna(0).values if O is not None and "position" in O else np.zeros(len(idx)))
    p = g.values; inn = False; t0 = None; hist = []; bloque = None; k2c = {}
    for t in range(max(0, len(idx) - fenetre), len(idx)):
        if inn:
            if t - t0 >= 126 or p[t] <= p0 * 0.75:
                inn = False; hist.append(dict(entree=idx[t0], sortie=idx[t], resultat=p[t] / p0 - 1, motif="6 mois" if t - t0 >= 126 else "stop −25 %"))
            continue
        if trig[t] and pos_or[t] == 0:
            m_ = (idx[t].year, idx[t].month)
            if m_ not in k2c: B_ = etat_break(D, idx[t]); k2c[m_] = bool(B_ and B_["actif"])
            if k2c[m_]: bloque = idx[t]; continue
            inn = True; t0 = t; p0 = p[t]
    n = len(idx) - 1
    out = dict(actif=inn, signal=bool(trig[-1]), vix=float(vv.iloc[-1]), pic=float(vpk.iloc[-1]), seuil_reflux=float(0.85 * vpk.iloc[-1]),
               historique=hist, bloque_k2=bloque, or_investi=bool(pos_or[-1] > 0))
    if inn:
        reste = 126 - (n - t0)
        out.update(entree=idx[t0], prix=float(p0), stop=float(p0 * 0.75), seances=n - t0, reste=reste,
                   fin=pd.Timestamp(idx[-1]) + pd.offsets.BDay(max(reste, 0)), perf=float(p[-1] / p0 - 1))
    return out

def sigma_serie(s, v, spx, est_sp):
    """Volatilité annuelle attendue chaque jour : VIX × bêta 60 séances (carte des prix)."""
    if est_sp: return v / 100
    return v / 100 * (np.log(s).diff().rolling(60).std() / np.log(spx).diff().rolling(60).std())

def etat_marche(nom, D, asof, cl=None):
    m = MARCHES[nom]; th, mth = m["cycle"], m["mini"]; est_sp = nom == SP
    s = D[nom].loc["1989":asof].dropna(); idx = s.index; val = s.values
    vix, sp = D["vix"], D[SP]; v = on(idx, vix); spx = on(idx, sp)
    S7 = sig7(s, vix, sp, th, mth, est_sp); posA, tradesA, hiA = strategie_A(s, S7, th)
    RG = REGLAGES[m["groupe"]]; m5 = m["mini_recent"] if RG["s5"]["seuil"] == "récent" else mth
    E1, S5 = sigS5(s, vix, sp, m5, est_sp, RG["s5"]); P4, F2 = sigP4(s, vix, sp, est_sp, RG["p4"])
    P, modeP, _ = zz(s, th); p, mode, _ = zz(s, mth)
    lastB = [i for i, t in P if t == "B"][-1]; i_hi = lastB + int(np.argmax(val[lastB:])); hi_c = val[i_hi]
    if mode == "down":
        h = [i for i, t in p if t == "H"][-1]; ref = h; phase = "correction"
        ampl = 1 - val[-1] / val[h]; ampl_max = 1 - val[h:].min() / val[h]; vix_h = v.iloc[h]; dur = duree_attendue_mini(vix_h)
        hi_mini = val[h]; non_retour = hi_mini * (1 - SEUIL["non_retour"] * mth); confirm = val[h:].min() * (1 + mth)
    else:
        b = [i for i, t in p if t == "B"][-1]; ref = b; phase = "hausse"
        ampl = val[-1] / val[b] - 1; ampl_max = val[b:].max() / val[b] - 1; vix_h = dur = non_retour = confirm = None
        i_hr = b + int(np.argmax(val[b:])); hi_r = val[i_hr]
    s5d = list(idx[S5.values]); t5 = idx.get_loc(s5d[-1]) if s5d else None
    inval = float(val[t5 - 4:t5 + 1].min()) if t5 is not None else None
    p4d = list(idx[P4.values]); s7d = list(idx[S7.values])
    r60 = 1.0 if est_sp else np.log(s).diff().iloc[-60:].std() / np.log(spx).diff().iloc[-60:].std()
    sig_ann = v.iloc[-1] / 100 * r60
    bande = {h: (val[-1] * np.exp(-1.2816 * sig_ann * np.sqrt(h / 252)), val[-1] * np.exp(1.2816 * sig_ann * np.sqrt(h / 252))) for h in (5, 10, 20)}
    rel20 = (val[-1] / val[-21] - 1) - (spx.iloc[-1] / spx.iloc[-21] - 1)
    A_inv = bool(posA.iloc[-1])
    return dict(nom=nom, s=s, prix=val[-1], date=idx[-1], seuil_cycle=th, seuil_mini=mth, groupe=m["groupe"], reglage=RG,
        cycle=dict(creux=idx[lastB], plus_haut=idx[i_hi], valeur_haut=hi_c, recul=val[-1] / hi_c - 1, recul_x_seuil=(1 - val[-1] / hi_c) / th,
                   gain=hi_c / val[lastB] - 1, gain_actuel=val[-1] / val[lastB] - 1, seances=len(val) - 1 - lastB, seances_depuis_haut=len(val) - 1 - i_hi,
                   pivots=P,
                   en_hausse=modeP == "up", niveau_fin_cycle=hi_c * (1 - th)),
        A=dict(investie=A_inv, niveau_sortie=hiA * (1 - th) if A_inv else None, trades=tradesA, position=posA,
               decision=None,
               derniere_sortie=pd.Timestamp(tradesA[-1][2]) if tradesA and tradesA[-1][2] is not None else None),
        mini=dict(phase=phase, depuis=idx[ref], seances=len(val) - 1 - ref, ampleur=ampl, ampleur_max=ampl_max, x_seuil=ampl / mth, x_seuil_max=ampl_max / mth,
                  vix_au_pic=vix_h, duree_attendue=dur, niveau_non_retour=non_retour, niveau_confirmation=confirm,
                  plus_haut=(idx[i_hr], hi_r) if phase == "hausse" else (idx[ref], val[ref]),
                  retombee=(1 - val[-1] / hi_r) if phase == "hausse" else None, niveau_bascule=hi_r * (1 - mth) if phase == "hausse" else None,
                  plus_bas=val[ref:].min()),
        r20=val[-1] / val[-21] - 1, r5=val[-1] / val[-6] - 1, sigma=sigma_serie(s, v, spx, est_sp),
        S5=dict(dernier=s5d[-1] if s5d else None, seances=len(val) - 1 - t5 if t5 is not None else None, invalidation=inval,
                valide=bool(inval is not None and val[-1] >= inval and len(val) - 1 - t5 <= 40), trades=trades_S5(s, S5, m5)),
        P4=dict(dernier=p4d[-1] if p4d else None, seances=len(val) - 1 - idx.get_loc(p4d[-1]) if p4d else None, vitesse_rang=F2.iloc[-1]),
        dernier_S7=s7d[-1] if s7d else None, retard_sp20=rel20, ma50=bool(val[-1] > s.rolling(50).mean().iloc[-1]), ma200=bool(val[-1] > s.rolling(200).mean().iloc[-1]),
        vol_annuelle=sig_ann, bande80=bande, series=dict(S7=S7, S5=S5, E1=E1, P4=P4))

# ---------------------------------------------------------------- lecture : ce que disent les règles, ensemble
def lecture(e, c):
    """Phrases de lecture, dans l'ordre de la chaîne : fond → cycle → mini-cycle → signaux → risque."""
    L = []; m = e["mini"]; tech = MARCHES[e["nom"]]["tech"]
    if tech and c["taux_reel_12m"] >= SEUIL["taux_reel_12m"]:
        L.append(("fond", f"Taux réel +{nb(c['taux_reel_12m'])} pt sur 12 mois : fond défavorable à la tech contre le marché (règle « niveau »)."))
    if tech and c["taux10_6m"] >= SEUIL["taux10_6m"] and not e["ma50"]:
        L.append(("alerte", "Taux 10 ans +1 pt en 6 mois et indice sous sa moyenne 50 : alerte de sortie."))
    if e["A"]["investie"]:
        L.append(("cycle", f"Stratégie A investie ; sortie si clôture ≤ {nb(e['A']['niveau_sortie'])} (−1 seuil de cycle du plus haut)."))
    else:
        L.append(("cycle", "Stratégie A hors marché : on attend un signal S7 de cycle."))
    if m["phase"] == "correction":
        txt = f"Mini-correction depuis le {m['depuis']:%d/%m/%Y} : {pc(-m['ampleur'])} ({nb(m['x_seuil'])} seuil mini, max {nb(m['x_seuil_max'])}), {m['seances']} séances"
        if m["duree_attendue"]: txt += f" ; loi du VIX : ≈ {m['duree_attendue']:.0f} séances attendues (VIX au pic {nb(m['vix_au_pic'], 1)})"
        L.append(("mini", txt + "."))
        if m["x_seuil_max"] >= SEUIL["approche"]:
            L.append(("alerte", f"Correction ≥ 2 seuils mini : point de non-retour ({nb(m['niveau_non_retour'])}) proche — fin de cycle dans 54-78 % des cas s'il est franchi."))
    else:
        L.append(("mini", f"Mini-hausse depuis le {m['depuis']:%d/%m/%Y} : {pc(m['ampleur'])} ({nb(m['x_seuil'])} seuil mini), {m['seances']} séances."))
    s5 = e["S5"]
    if s5["valide"]:
        L.append(("signal", f"S5 actif (signal du {s5['dernier']:%d/%m/%Y}, il y a {s5['seances']} séance{'s' if s5['seances'] > 1 else ''}) ; invalidation (couteau) sous {nb(s5['invalidation'])}."))
    if c["dernier_e80"] is not None and c["seances_depuis_e80"] <= 7:
        txt = f"VIX entré dans son 80e percentile il y a {c['seances_depuis_e80']} séances"
        txt += " et gros retard sur le S&P : mini-creux dans les 7 séances 36-46 % des fois." if e["retard_sp20"] <= SEUIL["retard"] and e["nom"] != SP else " : mini-creux dans les 7 séances 14-36 % des fois."
        L.append(("signal", txt))
    if e["P4"]["seances"] is not None and e["P4"]["seances"] <= 10:
        L.append(("signal", f"P4 il y a {e['P4']['seances']} séances : souvent un surplace ensuite (0 à +3 % à 20 s.)."))
    if c["dollar_ruee_20s"] and s5["valide"]:
        L.append(("alerte", "Ruée vers le dollar récente : 57-74 % des S5 dans ce cas sont des couteaux — respecter l'invalidation."))
    return L

# ---------------------------------------------------------------- historique des signaux
def historique(etats, clim):
    rows = []
    for nom, e in etats.items():
        s = e["s"]; idx = s.index; val = s.values; n = len(val)
        def add(sig, d):
            t = idx.get_loc(d)
            r = {f"{h} s.": (val[t + h] / val[t] - 1) if t + h < n else np.nan for h in (5, 20, 40)}
            pire = val[t:min(t + 21, n)].min() / val[t] - 1
            rows.append(dict(marché=nom, signal=sig, date=d, prix=val[t], **r, **{"pire 20 s.": pire}))
        for sig, ser in [("S7 cycle", e["series"]["S7"]), ("S5 mini", e["series"]["S5"]), ("P4 pic", e["series"]["P4"])]:
            for d in idx[front(ser).values]:
                if d >= DEBUT_A: add(sig, d)
        for d in clim["e80_dates"]:
            if d in idx and d >= DEBUT_A: add("VIX entre dans son 80e", d)
    return pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)

# ---------------------------------------------------------------- or
def recent(b, n=60): return b.fillna(False).astype(float).rolling(n, min_periods=1).max() > 0
def rk1(s): return s.rolling(250, min_periods=200).rank(pct=True) * 100

def rang_speculateurs(c, idx):
    """Rang (0-100) de la position nette des spéculateurs parmi les 156 semaines précédentes."""
    c = c.dropna(); v = c.values; rk = pd.Series(np.nan, index=c.index)
    for t in range(160, len(v)): rk.iloc[t] = (v[t - 156:t] < v[t]).mean() * 100
    return on(idx, rk)

def fire(cond, idx, start, ecart=126):
    out = []; last = -10**9; c = cond.fillna(False).values
    for i in range(len(idx)):
        if idx[i] >= start and c[i] and i - last >= ecart: out.append(i); last = i
    return out

def etat_or(D, asof):
    mines = D["Mines d'or (GDX)"].loc[:asof]; idx = mines.index
    gold = D["or"].loc[:asof]; gd = on(idx, gold).combine_first(mines)
    rr = on(idx, taux_reel_or(D["dfii10"], D["dgs10"], D["cpi"])); u = on(idx, D["dxy"])
    srk = rang_speculateurs(D["spec_or"], idx) if not D["spec_or"].empty else pd.Series(np.nan, index=idx)
    gvz = on(idx, D["gvz"]); rvg = np.log(on(idx, gold)).diff().rolling(20).std() * np.sqrt(252) * 100
    rvm = np.log(mines).diff().rolling(20).std() * np.sqrt(252) * 100
    vol_or = gvz.combine_first(rvg.where(idx >= pd.Timestamp("2000-10-01"))).combine_first(rvm)
    rel = np.log(mines / on(idx, D[SP])); ch = lambda x: x - x.shift(20)
    d_usd, d_rr, d_sp = recent(rk1(u) >= 90), recent(rk1(rr) >= 90), recent(srk <= 10)
    am_rr, am_vol, am_rel = ch(rr) < 0, ch(vol_or) < 0, ch(rel) > 0
    signaux = fire(d_usd & d_rr & d_sp & am_rr & am_vol & am_rel, idx, pd.Timestamp("1989-01-01"))
    macro = ((rr - rr.shift(63)) > 0) | ((u / u.shift(63) - 1) > 0)
    # stratégie : à partir de sept. 2000, entrée sur signal, sorties : stop de départ GDX −10 % (avant +10 %), or −13 % du plus haut, règle de cycle
    pos = pd.Series(0.0, index=idx); trades = []; busy = -1; px = mines
    for i in signaux:
        if idx[i] < pd.Timestamp("2000-09-01") or i <= busy: continue
        p0 = px.iloc[i]; ghi = gd.iloc[i]; up = False; o, why = len(idx) - 1, "en cours"
        for t in range(i + 1, len(idx)):
            ghi = max(ghi, gd.iloc[t]); x = px.iloc[t]
            if x >= p0 * 1.10: up = True
            if not up and x <= p0 * 0.90: o, why = t, "stop de départ −10 %"; break
            if gd.iloc[t] <= ghi * 0.87: o, why = t, "or −13 %"; break
            if gd.iloc[t] < 0.85 * ghi and macro.iloc[t]: o, why = t, "règle de cycle"; break
        pos.iloc[i + 1:o + 1] = 1.0; busy = o
        trades.append(dict(entree=idx[i], sortie=idx[o] if why != "en cours" else None, resultat=px.iloc[o] / p0 - 1, motif=why,
                           ghi=ghi, p0=p0, up=up))
    inv = bool(pos.iloc[-1])
    niveaux = None
    if inv:
        tr = trades[-1]; niveaux = dict(or_moins13=tr["ghi"] * 0.87, or_moins15=tr["ghi"] * 0.85, stop_depart=None if tr["up"] else tr["p0"] * 0.90)
    last = lambda x: x.iloc[-1] if len(x) else np.nan
    return dict(date=idx[-1], or_prix=last(gold), gdx=mines.iloc[-1], investie=inv, niveaux=niveaux, trades=trades, position=pos,
                dollar_rang=last(rk1(u)), taux_reel_rang=last(rk1(rr)), spec_rang=last(srk),
                decor=dict(dollar=bool(d_usd.iloc[-1]), taux=bool(d_rr.iloc[-1]), spec=bool(d_sp.iloc[-1])),
                amorce=dict(taux=bool(am_rr.iloc[-1]), vol=bool(am_vol.iloc[-1]), gdx_sp=bool(am_rel.iloc[-1])),
                macro=bool(macro.iloc[-1]), gvz=last(gvz), signaux=[idx[i] for i in signaux],
                var20=dict(taux=last(ch(rr)), vol=last(ch(vol_or)), gdx_sp=last(ch(rel))), vol_or=vol_or, mines=mines, or_serie=on(idx, gold))

def tout_calculer(D, asof=None, memoire=4):
    if asof is None: asof = min(D["vix"].index[-1], D[SP].index[-1])
    asof = pd.Timestamp(asof); c = climat(D, asof)
    E = {}
    for n in MARCHES:
        if len(D[n].loc[:asof]) >= 300:
            try: E[n] = etat_marche(n, D, asof)
            except Exception: pass
    O = etat_or(D, asof) if not D["Mines d'or (GDX)"].empty else None
    if O is not None: O["budget"] = budget_or(D, asof)
    debut = asof - pd.DateOffset(years=memoire) if memoire else DEBUT_A
    ST = {n: stats_marche(e, D["vix"], debut) for n, e in E.items()}
    J = {n: etats_jour(e, D["vix"], ST[n]) for n, e in E.items()}
    for n, e in E.items():
        e["analogue"] = analogues(J, n, debut, asof)
        e["bande80"] = {h: tuple(e["prix"] * np.exp(np.array(e["analogue"]["q"][h])[[0, 4]] * e["sigma"].iloc[-1] * np.sqrt(h / 252))) for h in (5, 10, 20)}
    LO = {n: lois_du_jour(e, c, ST[n]) for n, e in E.items()}
    V = {n: verdict(E[n], LO[n]) for n in E}
    return asof, c, E, O, ST, LO, V

# ================================================================ statistiques propres à chaque marché
def phases_mini(s, vix, mth):
    """Mini-hausses et mini-corrections terminées (zigzag au seuil mini) : ampleur, durée, VIX au départ."""
    piv, _, _ = zz(s, mth); v = s.values; idx = s.index; vv = on(idx, vix).values; R = []
    for (i, a), (j, b) in zip(piv[:-1], piv[1:]):
        if idx[i] < DEBUT_A or j <= i: continue
        R.append(dict(type="hausse" if a == "B" else "correction", debut=idx[i], fin=idx[j], seances=j - i, ampleur=abs(v[j] / v[i] - 1), vix=vv[i]))
    return pd.DataFrame(R)

def loi_puissance(x, y):
    """y = a × (x/20)^b ajusté en logarithmes ; renvoie a, b, facteur d'erreur (écart-type des résidus, en multiplicatif)."""
    m = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
    lx, ly = np.log(x[m] / 20), np.log(y[m]); b, la = np.polyfit(lx, ly, 1); res = ly - (la + b * lx)
    return float(np.exp(la)), float(b), float(np.exp(res.std()))

def stats_marche(e, vix, debut):
    """Lois du VIX ajustées sur tout l'historique (assez de corrections) ; âges et profondeurs sur la mémoire choisie."""
    P = phases_mini(e["s"], vix, e["seuil_mini"]); C = P[P.type == "correction"]
    aD, bD, fD = loi_puissance(C.vix.values, C.seances.values.astype(float))
    aV, bV, fV = loi_puissance(C.vix.values, (C.ampleur / C.seances).values * 100)
    W = P[P.fin >= debut]
    if (W.type == "hausse").sum() < 8 or (W.type == "correction").sum() < 8: W = P
    Cw, Hw = W[W.type == "correction"], W[W.type == "hausse"]
    piv = e["cycle"]["pivots"]; v = e["s"].values; idx = e["s"].index
    cyc = [(v[j] / v[i] - 1, j - i) for (i, a), (j, b) in zip(piv[:-1], piv[1:]) if a == "B" and idx[i] >= DEBUT_A]
    return dict(P=P, n_corr=len(Cw), n_hausse=len(Hw), n_corr_loi=len(C), duree=(aD, bD, fD), vitesse=(aV, bV, fV),
                corr_ampleur=Cw.ampleur.values, corr_seances=Cw.seances.values, hausse_ampleur=Hw.ampleur.values, hausse_seances=Hw.seances.values,
                cycle_gain=np.array([g for g, _ in cyc]), cycle_seances=np.array([d for _, d in cyc]), memoire_reduite=len(W) < len(P))

def rang(x, arr): return float((np.asarray(arr) < x).mean()) if len(arr) else np.nan

# ================================================================ situations comparables (carte des prix conditionnelle, creux ou continuation)
def etats_jour(e, vix, st):
    """État du mini-cycle connu chaque jour (sans regarder l'avenir) et ce qui s'est passé ensuite."""
    s = e["s"]; v = s.values; idx = s.index; n = len(v); mth = e["seuil_mini"]; aD, bD, fD = st["duree"]
    vv = on(idx, vix).values; sig = e["sigma"].values
    mode = np.zeros(n, int); x = np.full(n, np.nan); rx = np.full(n, np.nan); age = np.full(n, np.nan); low = np.full(n, np.nan)
    md, ref, ext = 1, 0, 0
    for t in range(1, n):
        if md == 1:
            if v[t] > v[ext]: ext = t
            if v[t] <= v[ext] * (1 - mth): md, ref, ext = -1, ext, t
        else:
            if v[t] < v[ext]: ext = t
            if v[t] >= v[ext] * (1 + mth): md, ref, ext = 1, ext, t
        mode[t] = md
        if md == 1: x[t] = (v[t] / v[ref] - 1) / mth; rx[t] = (1 - v[t] / v[ext]) / mth
        else: x[t] = (1 - v[ext] / v[ref]) / mth; age[t] = (t - ref) / (aD * (vv[t] / 20) ** bD); low[t] = v[ext]
    J = pd.DataFrame(dict(mode=mode, x=x, rx=rx, age=age), index=idx)
    for h in (2, 5, 10, 15, 20):
        fwd = np.full(n, np.nan); fwd[:n - h] = np.log(v[h:] / v[:n - h]); J[f"z{h}"] = fwd / (sig * np.sqrt(h / 252))
    mn10 = pd.Series(v[::-1]).rolling(10, min_periods=10).min().values[::-1]   # min des séances t … t+9
    nxt = np.full(n, np.nan); nxt[:n - 1] = mn10[1:]                           # min des séances t+1 … t+10
    J["nouveau_bas"] = np.where(np.isnan(nxt), np.nan, (nxt < low).astype(float)); J["surplus"] = nxt / low - 1
    fl = np.full(n, np.nan)
    for t in range(n - 10): fl[t] = float((mode[t + 1:t + 11] == -1).any())
    J["bascule"] = fl
    J["bx"] = np.where(mode == -1, np.digitize(x, [1, 1.5, 2, 2.5]), np.digitize(np.nan_to_num(x), [1, 2]))
    J["ba"] = np.where(mode == -1, np.digitize(np.nan_to_num(age), [0.5, 1, fD]), np.digitize(np.nan_to_num(rx), [0.25, 0.5, 0.75]))
    return J

def analogues(J, nom, debut, asof):
    """Jours comparables des 6 marchés (même phase, même profondeur, même âge relatif) sur la mémoire choisie."""
    cur = J[nom].iloc[-1]; A = pd.concat([j.loc[debut:asof] for j in J.values()]); A = A[A["mode"] == cur["mode"]]
    base = A.dropna(subset=["z20"])
    for keys, lab in [(["bx", "ba"], "phase, profondeur et âge"), (["ba"], "phase et âge"), (["bx"], "phase et profondeur"), ([], "phase seule")]:
        M = base
        for k in keys: M = M[M[k] == cur[k]]
        if len(M) >= 60: break
    q = {0: [0.0] * 5}
    for h in (2, 5, 10, 15, 20):
        z = M[f"z{h}"].dropna(); q[h] = list(np.quantile(z, [0.10, 0.25, 0.50, 0.75, 0.90])) if len(z) >= 30 else [-1.2816, -0.6745, 0, 0.6745, 1.2816]
    r = dict(n=len(M), critere=lab, q=q, mode=int(cur["mode"]))
    if cur["mode"] == -1:
        nb_ = M["nouveau_bas"].dropna(); r.update(p_bas=nb_.mean(), p_bas_base=base["nouveau_bas"].dropna().mean(), surplus=M.loc[M.nouveau_bas == 1, "surplus"].median())
    else:
        r.update(p_bascule=M["bascule"].dropna().mean(), p_bascule_base=base["bascule"].dropna().mean())
    return r

def cone(e, hs=range(21)):
    """Quantiles de prix (10, 25, 50, 75, 90 %) à chaque horizon, d'après les situations comparables."""
    q = e["analogue"]["q"]; H = sorted(q); sig = e["sigma"].iloc[-1]; out = []
    for h in hs:
        zq = [np.interp(h, H, [q[k][i] for k in H]) for i in range(5)]
        out.append([e["prix"] * np.exp(z * sig * np.sqrt(h / 252)) for z in zq])
    return np.array(out)

# ================================================================ les lois appliquées aujourd'hui
def L(titre, valeur, conclusion, niveau, source, jauge=None):
    """niveau : ok (vert) · info (bleu) · warn (orange) · bad (rouge). jauge : (valeur, max, repère[, (bande basse, bande haute)])."""
    return dict(titre=titre, valeur=valeur, conclusion=conclusion, niveau=niveau, source=source, jauge=jauge)

def lois_du_jour(e, c, st):
    m = e["mini"]; s = e["s"]; val = s.values; mth = e["seuil_mini"]; nom = e["nom"]; tech = MARCHES[nom]["tech"]; an = e["analogue"]
    vix = c["vix"]; aD, bD, fD = st["duree"]; aV, bV, fV = st["vitesse"]; out = []
    mem = f"{an['n']} situations comparables ({an['critere']})"
    pl = lambda k: "s" if k >= 1.5 else ""
    if m["phase"] == "correction":
        n = m["seances"]; D0 = aD * (m["vix_au_pic"] / 20) ** bD; D1 = aD * (vix / 20) ** bD; lo, hi = D1 / fD, D1 * fD
        dep = f" Au VIX du départ ({nb(m['vix_au_pic'], 1)}), la loi attendait ≈ {D0:.0f}."
        if n < lo: concl, niv = f"Jeune : au VIX d'aujourd'hui, la loi place la fin entre {lo:.0f} et {hi:.0f} séances, soit dans {lo - n:.0f} à {hi - n:.0f} séances.{dep}", "info"
        elif n <= D1: concl, niv = f"Dans l'intervalle de la loi ({lo:.0f} à {hi:.0f} séances) : fin estimée dans ≈ {D1 - n:.0f} séance{pl(D1 - n)}, au plus tard ≈ {hi - n:.0f}.{dep}", "info"
        elif n <= hi: concl, niv = f"Mûre : dans l'intervalle de la loi ({lo:.0f} à {hi:.0f} séances), au-delà de son centre (≈ {D1:.0f}). La fin peut venir à tout moment.{dep}", "ok"
        else: concl, niv = f"Trop longue : au-delà de l'intervalle de la loi ({lo:.0f} à {hi:.0f} séances). Baisse de régime plutôt que simple correction.", "bad"
        out.append(L("Loi du VIX · durée de la correction", f"séance {n} · loi {lo:.0f}–{hi:.0f}", concl, niv,
                     f"loi_vix_tech · {nb(aD, 1)} × (VIX/20)^{nb(bD)} · {st['n_corr_loi']} corrections depuis 1990", (n, max(hi * 1.2, n * 1.08), D1, (lo, hi))))
        vit = m["ampleur_max"] / max(n, 1) * 100; vit_att = aV * (vix / 20) ** bV; r = vit / vit_att
        txt = f"{nb(vit, 2)} % par séance depuis le plus haut du {pd.Timestamp(m['depuis']):%d/%m}. À un VIX de {nb(vix, 1)}, une correction normale de ce marché descend de {nb(vit_att, 2)} % par séance : {nb(r, 1)} × ce rythme. "
        if n < 3: cv, nv = txt + f"Mesure fragile ({n} séance{'s' if n > 1 else ''}).", "info"
        elif r >= 1.5: cv, nv = txt + "Trop rapide : la peur n'est pas au niveau de la baisse, soit le VIX monte encore, soit la baisse ralentit.", "warn"
        elif r <= 0.67: cv, nv = txt + "Lente : baisse d'usure, sans panique.", "info"
        else: cv, nv = txt + "Rythme normal.", "ok"
        out.append(L("Vitesse de la correction", f"{pc(-m['ampleur_max'])} en {n} séance{'s' if n > 1 else ''}", cv, nv, f"loi_vix_tech · vitesse = {nb(aV, 2)} × (VIX/20)^{nb(bV)}", (r, 3.0, 1.0, (0.67, 1.5))))
        # creux ou continuation
        p, pb, sx = an["p_bas"], an["p_bas_base"], an["surplus"]; vm5 = c["vix_max5"]; montee = vix >= 0.95 * vm5; reflux = vix <= SEUIL["reflux"] * vm5
        txt = f"Dans {mem}, la correction a fait un nouveau plus bas dans les 10 séances {pc(p, 0, False)} des fois (moyenne des corrections : {pc(pb, 0, False)})"
        txt += f", de {pc(sx)} de plus en médiane. " if p > 0 and not np.isnan(sx) else ". "
        if montee and vix >= c["vix_q80"]: txt += f"La peur monte encore : pas de creux avant son reflux (VIX sous {nb(SEUIL['reflux'] * vm5, 1)})."
        elif reflux: txt += "La peur reflue déjà (−15 % de son pic) : la condition du creux est remplie côté VIX."
        if e["S5"]["valide"]: lab, nv = "CREUX EN FORMATION", "ok"; txt = "Signal S5 actif : tant que le couteau tient, le creux est en place. " + txt
        elif p >= 0.6 or (montee and vix >= c["vix_q80"]): lab, nv = "CONTINUATION PROBABLE", "warn"
        elif p <= 0.4 and not montee: lab, nv = "CREUX PROCHE", "ok"
        else: lab, nv = "INDÉCIS", "info"
        out.append(L("Creux ou continuation ?", lab, txt, nv, f"situations comparables des 6 marchés · reperes_mini_cycles", (p, 1.0, pb)))
        x = m["x_seuil_max"]; pr = rang(m["ampleur_max"], st["corr_ampleur"])
        if x >= SEUIL["non_retour"]: cp, np_ = "Point de non-retour franchi : la correction finit le cycle dans 54-78 % des cas.", "bad"
        elif x >= SEUIL["approche"]: cp, np_ = f"Zone d'alerte : non-retour à {nb(m['niveau_non_retour'])} ({pc(m['niveau_non_retour'] / val[-1] - 1)}). Plus profonde que {pc(pr, 0, False)} des mini-corrections récentes.", "warn"
        else: cp, np_ = f"Correction ordinaire : plus profonde que {pc(pr, 0, False)} des mini-corrections récentes (médiane {pc(-np.median(st['corr_ampleur']), 0)}).", "ok"
        out.append(L("Profondeur · point de non-retour", f"{pc(-m['ampleur_max'])} · {nb(x)} seuil{'s' if x >= 2 else ''} sur 2,5", cp, np_, f"mini_cycles_tech · {st['n_corr']} corrections", (x, 3.0, 2.5)))
        out.append(L("Fin officielle de la correction", f"au-dessus de {nb(m['niveau_confirmation'])}",
                     f"Il faut {pc(m['niveau_confirmation'] / val[-1] - 1)} pour confirmer le mini-creux (rebond d'un seuil mini depuis le plus bas, {nb(m['plus_bas'])}).", "info", "définition des mini-cycles",
                     (val[-1] / m["plus_bas"] - 1, mth, mth)))
    else:
        n = m["seances"]; g = m["ampleur"]; ret = m["retombee"]; rx = ret / mth; dh, vh = m["plus_haut"]
        pa = rang(m["ampleur_max"], st["hausse_ampleur"]); pd_ = rang(n, st["hausse_seances"]); med_a, med_n = np.median(st["hausse_ampleur"]), np.median(st["hausse_seances"])
        bas = f"Bascule en correction sous {nb(m['niveau_bascule'])} ({pc(m['niveau_bascule'] / val[-1] - 1)})."
        if rx >= 0.75: ch, nh = f"Hausse presque effacée : {pc(-ret)} depuis son plus haut du {pd.Timestamp(dh):%d/%m} ({nb(vh)}), soit {nb(rx)} seuil mini. {bas}", "bad"
        elif rx >= 0.5: ch, nh = f"Essoufflement : {pc(-ret)} depuis le plus haut du {pd.Timestamp(dh):%d/%m}, la moitié du chemin vers la correction. {bas}", "warn"
        elif pa >= 0.8 or pd_ >= 0.8: ch, nh = f"Hausse âgée : plus grande ou plus longue que 80 % des mini-hausses récentes (médiane {pc(med_a, 0)} en {med_n:.0f} séances). {bas}", "warn"
        elif pa <= 0.3 and pd_ <= 0.3: ch, nh = f"Hausse jeune et intacte : la mini-hausse médiane fait {pc(med_a, 0)} en {med_n:.0f} séances. {bas}", "ok"
        else: ch, nh = f"Hausse en milieu de course (médiane {pc(med_a, 0)} en {med_n:.0f} séances). {bas}", "info"
        out.append(L("Dynamique de la mini-hausse", f"{pc(g)} depuis le creux · {pc(-ret)} depuis le haut", ch, nh,
                     f"mini_cycles_tech · {st['n_hausse']} mini-hausses · barre = retombée vers la bascule", (rx, 1.0, 1.0, (0, 0.5))))
        p, pb = an["p_bascule"], an["p_bascule_base"]
        nv = "warn" if p >= 0.4 else ("info" if p >= 0.25 else "ok")
        out.append(L("Bascule en correction ?", f"{pc(p, 0, False)} dans les 10 séances",
                     f"Dans {mem}, la hausse a basculé en correction dans les 10 séances {pc(p, 0, False)} des fois (moyenne des hausses : {pc(pb, 0, False)}).", nv,
                     "situations comparables des 6 marchés", (p, 1.0, pb)))
        if n <= 5:
            rb = g / mth
            cr, nr = ("Départ vif : 75-80 % de ces creux donnent un vrai rebond (≥ 2 seuils).", "ok") if rb >= SEUIL["depart_vif"] else ("Départ modeste : deux creux sur trois donnent quand même un vrai rebond.", "info")
            out.append(L("Force du départ", f"{nb(rb)} seuil en {n} séances", cr, nr, "creux_rebond_tech", (rb, 1.5, SEUIL["depart_vif"])))
    # élan 20 séances
    vr = e["P4"]["vitesse_rang"]; r20 = e["r20"]
    base_txt = f"Variation du cours sur 20 séances ({pc(r20)}), classée parmi celles des 250 dernières séances : elle bat {pc(vr, 0, False)} d'entre elles. "
    if e["P4"]["seances"] is not None and e["P4"]["seances"] <= 10: cs, ns = base_txt + f"Signal de pic P4 il y a {e['P4']['seances']} séances : ensuite, souvent du surplace (0 à +3 % à 20 séances).", "warn"
    elif vr >= e["reglage"]["p4"]["q"]: cs, ns = base_txt + f"Montée trop rapide : si le VIX se réveille (+{(e['reglage']['p4']['reveil'] - 1) * 100:.0f} % sur son plus bas 20 s.), signal de pic P4.", "warn"
    elif vr <= 0.05: cs, ns = base_txt + "Chute parmi les 5 % les plus brutales de l'année.", "warn"
    else: cs, ns = base_txt + "Élan dans la normale de l'année.", "ok"
    out.append(L("Élan sur 20 séances", f"{pc(r20)} · rang {pc(vr, 0, False)}", cs, ns, "pics_mini_tech · P4", (vr, 1.0, 0.95, (0.05, 0.95))))
    # peur
    vm5 = c["vix_max5"]; q8 = c["vix_q80"]
    if c["seances_depuis_e80"] is not None and c["seances_depuis_e80"] <= 7:
        big = e["retard_sp20"] <= SEUIL["retard"] and nom != SP
        cvx = ("Le VIX vient d'entrer dans la peur et ce marché est en retard sur le S&P : mini-creux dans les 7 séances 36-46 % des fois (contre 6-15 %)." if big
               else "Le VIX vient d'entrer dans la peur : mini-creux dans les 7 séances 14-36 % des fois (contre 8-16 %).")
        out.append(L("Peur · VIX", f"VIX {nb(vix, 1)} · entré il y a {c['seances_depuis_e80']} s.", cvx, "ok" if big else "info", "reperes_mini_cycles", (vix, q8 * 1.8, q8)))
    elif vix >= q8:
        if vix >= 0.95 * vm5: cvx, nvx = f"Peur au-dessus de son seuil ({nb(q8, 1)}) et encore à son plus haut de 5 séances : la baisse continue en général. Le creux se forme quand la peur reflue, sous {nb(SEUIL['reflux'] * vm5, 1)}.", "warn"
        elif vix <= SEUIL["reflux"] * vm5: cvx, nvx = f"La peur reflue (−15 % de son pic de 5 séances, {nb(vm5, 1)}) : le creux est en général proche. Le S5 2022 n'exige plus ce reflux : la peur au-dessus de son 70e centile suffit.", "ok"
        else: cvx, nvx = f"Peur haute qui hésite : sous {nb(SEUIL['reflux'] * vm5, 1)}, son reflux validerait un creux ; au-dessus de {nb(vm5, 1)}, la baisse continue.", "info"
        out.append(L("Peur · VIX", f"VIX {nb(vix, 1)} ≥ seuil {nb(q8, 1)}", cvx, nvx, "s7_mini_tech · reperes_mini_cycles", (vix, q8 * 1.8, q8)))
    else:
        out.append(L("Peur · VIX", f"VIX {nb(vix, 1)} < seuil {nb(q8, 1)}", f"Peur contenue. À ce VIX, une correction de ce marché dure ≈ {aD * (vix / 20) ** bD:.0f} séances et descend de {nb(aV * (vix / 20) ** bV, 2)} % par séance.", "ok", "loi_vix_tech", (vix, q8 * 1.8, q8)))
    # S5
    s5 = e["S5"]
    if s5["valide"]:
        d = s5["invalidation"] / val[-1] - 1
        RG = e["reglage"]
        if not RG["timable"]:
            out.append(L("Signal de creux S5", f"actif · couteau {pc(d)}", "Pétrole déclaré non timable : aucune règle de creux n'y bat le hasard. Signal affiché pour information.", "info", "recalibrage_or_petrole"))
        else:
            cc = "Ruée vers le dollar en même temps : 57-74 % de couteaux. Respecter le niveau." if c["dollar_ruee_20s"] else f"Sortie si clôture sous {nb(s5['invalidation'])}. Réglage 2022 : {RG['s5_preuve']}."
            out.append(L("Signal de creux S5", f"actif · couteau {pc(d)}", cc, "info" if RG.get("repere") else ("warn" if c["dollar_ruee_20s"] else "ok"), f"recalibrage_2022 · peremption · portefeuille_final · révision {RG['revision']}"))
    elif s5["dernier"] is not None and s5["seances"] <= 40 and val[-1] < s5["invalidation"]:
        out.append(L("Signal de creux S5", "invalidé", f"Le cours a cassé le couteau ({nb(s5['invalidation'])}) : on sort et on attend le signal suivant.", "bad", "gestion_couteau_tech"))
    # cycle
    cy = e["cycle"]
    if e["A"]["investie"]:
        dA = e["A"]["niveau_sortie"] / val[-1] - 1; x = cy["recul_x_seuil"]
        out.append(L("Cycle · stratégie A", f"ouvert · sortie {pc(dA)}", f"Cycle ouvert tant que le cours tient {nb(e['A']['niveau_sortie'])}. Recul depuis le sommet du cycle : {pc(cy['recul'])}, soit {pc(x, 0, False)} du chemin vers la sortie.",
                     "ok" if x < 0.5 else "warn", "entree_tech · strategie_actuelle_tech", (x, 1.0, 1.0)))
    else:
        dc = e["A"].get("decision")
        out.append(L("Cycle · stratégie A", "fermé" + (" · décision du trader" if dc else ""), (dc["note"] + ". " if dc else "") + "Cycle terminé : on attend un signal S7 (krach, VIX ≥ 30 qui reflue, amorce).", "bad", (dc["source"] + " · journal de décisions") if dc else "entree_tech"))
    if tech:
        if c["taux_reel_12m"] >= SEUIL["taux_reel_12m"]:
            out.append(L("Fond · taux réel", f"+{nb(c['taux_reel_12m'])} pt sur 12 mois", "Vent contraire : quand le taux réel monte de 0,5 pt, le NDX fait +2 % sur 12 mois contre +11 %.", "warn", "niveau_tech"))
        arme = c["taux10_6m"] >= SEUIL["taux10_6m"] or (c["fed_12m"] == c["fed_12m"] and c["fed_12m"] >= 1.0)
        val_cc = f"10 ans {'+' if c['taux10_6m'] >= 0 else ''}{nb(c['taux10_6m'])} pt / 6 mois · Fed {'+' if (c['fed_12m'] or 0) >= 0 else ''}{nb(c['fed_12m'])} pt / 12 mois"
        if arme and not e["ma50"]:
            out.append(L("Interrupteur coût du capital", "ACTIF · " + val_cc, "Coût du capital en hausse rapide et indice sous sa moyenne 50 : se mettre à l'abri. Retour dès que l'alerte s'éteint (cours au-dessus de la moyenne 50, ou hausses retombées sous 1 pt).", "bad", "alerte_taux_sortie · pic_tech_doc · NDX pire baisse −28 % au lieu de −39 % depuis 2010"))
        elif arme:
            out.append(L("Interrupteur coût du capital", "armé · " + val_cc, "Le coût du capital monte vite ; l'interrupteur se déclenche si l'indice clôture sous sa moyenne 50.", "warn", "alerte_taux_sortie · pic_tech_doc"))
        if c.get("marge_actif"):
            out.append(L("Alerte crédit sur marge", f"le crédit se retourne : {pc(c['marge_yoy'])} sur 12 mois, {c['marge_recul'] * 100:.0f} pts sous son plus haut de 6 mois",
                         "Les achats à crédit des particuliers s'essoufflent alors que le NDX est près de son plus haut : profil de 2021 (allumé de juillet 2021 à janvier 2022) et du 28/10/2026. Lecture, pas une règle : vérifier les sorties du système.",
                         "warn", "dette_marge · alerte, critère de règle atteint de justesse"))
        if c["concentration_60"]:
            out.append(L("Alerte concentration", f"NDX contre ses membres à parts égales : {pc(c['concentration'])} sur 6 mois",
                         "La hausse repose sur quelques méga-capitalisations (écart ≥ 5 pts dans les 60 dernières séances)." + (" Indice sous sa moyenne 50 : c'est le profil du sommet de fin 2021." if not e["ma50"] else " Tant que l'indice tient sa moyenne 50, simple vigilance."),
                         "warn", "pic_tech_doc · alerte non validée sur une 2e période"))
    return out

def verdict(e, lois):
    """Ancienne synthèse « loi la plus sévère » : gardée pour l historique ; le badge affiché suit la règle (app.position_regle, revue_app)."""
    if not e["reglage"]["timable"]: return "NON TIMABLE", "info", "Pétrole : aucune règle mécanique ne bat le hasard"
    if not e["A"]["investie"]: return "DANGER", "bad", "Cycle terminé"
    nv = [l["niveau"] for l in lois]
    if "bad" in nv: return "DANGER", "bad", next(l["titre"] for l in lois if l["niveau"] == "bad")
    if "warn" in nv: return "VIGILANCE", "warn", next(l["titre"] for l in lois if l["niveau"] == "warn")
    if e["S5"]["valide"] or e["mini"]["phase"] == "hausse": return "FAVORABLE", "ok", "Cycle ouvert, rien d'anormal"
    return "PATIENCE", "info", "Correction ordinaire en cours"

def budget_or(D, asof):
    """Budget de risque or, version simple : 90 % de mines en correction ≥ 17 % ayant dépassé sa durée, 50 % en surchauffe, sinon 70 %."""
    gdx = D["Mines d'or (GDX)"].loc[:asof]; idx = gdx.index; g = on(idx, D["or"]).combine_first(gdx).values; v = gdx.values; V = on(idx, D["vix"]).ffill().values
    up = True; pk = v[0]; pt = 0; lo = v[0]; lt = 0; L_ = 0; Dup = 25; Dc = 18
    for t in range(1, len(v)):
        x = v[t]
        if up:
            if x > pk: pk, pt = x, t
            if x <= pk * 0.9: up = False; lo, lt = x, t; Dc = 17.8 * (V[pt] / 20) ** -0.72
        else:
            if x < lo: lo, lt = x, t
            if x >= lo * 1.1: up = True; L_ = lt; pk, pt = x, t; Dup = 22.6 * (V[t] / 20) ** -0.76
    t = len(v) - 1
    if up:
        e = (v[t] / v[L_]) / (g[t] / g[L_]) - 1; age = (t - L_) / Dup
        part = 0.5 if (e >= 0.20 and age > 1) else 0.7
        return dict(part=part, phase="hausse", ecart=e, age=age, seances=t - L_, duree=Dup, profondeur=None)
    d = v[t] / pk - 1; age = (t - pt) / Dc
    part = 0.9 if (d <= -0.17 and age > 1) else 0.7
    return dict(part=part, phase="correction", ecart=None, age=age, seances=t - pt, duree=Dc, profondeur=d)
