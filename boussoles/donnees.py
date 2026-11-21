"""Téléchargement des données publiques, avec copie locale de secours (dossier cache/)."""
from . import FICHIERS
import io, os, time
import numpy as np, pandas as pd, requests

CACHE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
os.makedirs(CACHE, exist_ok=True)

def _save(name, s):
    try: s.to_csv(os.path.join(CACHE, name + ".csv"))
    except Exception: pass

def _load(name):
    p = os.path.join(CACHE, name + ".csv")
    if not os.path.exists(p): return None
    s = pd.read_csv(p, index_col=0, parse_dates=True).iloc[:, 0]; return s.dropna()

def _clean(s):
    s = pd.to_numeric(s, errors="coerce").dropna(); s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()

def yahoo(ticker, start="1985-01-01"):
    """Clôtures quotidiennes (non ajustées des dividendes, comme dans les dossiers)."""
    name = "yahoo_" + ticker.replace("^", "_")
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, auto_adjust=False, progress=False, threads=False)
        s = df["Close"]; s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
        s = _clean(s)
        if len(s) > 100: _save(name, s); return s, "Yahoo Finance"
    except Exception: pass
    s = _load(name); return (s, "copie locale") if s is not None else (pd.Series(dtype=float), "indisponible")

def fred(series_id):
    name = "fred_" + series_id
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series_id}, timeout=30); r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text)); s = df.set_index(df.columns[0]).iloc[:, 0].replace(".", np.nan)
        s = _clean(s)
        if len(s) > 50: _save(name, s); return s, "FRED"
    except Exception: pass
    s = _load(name); return (s, "copie locale") if s is not None else (pd.Series(dtype=float), "indisponible")

def cftc_or():
    """Spéculateurs or : position nette non commerciale / positions ouvertes (CFTC, legacy, futures seuls).
    Daté du lundi qui suit la publication (rapport du mardi + 6 jours), comme dans les dossiers."""
    name = "cftc_or"
    try:
        rows, off = [], 0
        while True:
            r = requests.get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", timeout=60,
                             params={"cftc_contract_market_code": "088691", "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all",
                                     "$order": "report_date_as_yyyy_mm_dd", "$limit": 5000, "$offset": off})
            r.raise_for_status(); j = r.json(); rows += j
            if len(j) < 5000: break
            off += 5000
        df = pd.DataFrame(rows)
        d = pd.to_datetime(df.report_date_as_yyyy_mm_dd) + pd.Timedelta(days=6)
        net = (df.noncomm_positions_long_all.astype(float) - df.noncomm_positions_short_all.astype(float)) / df.open_interest_all.astype(float)
        s = _clean(pd.Series(net.values, index=d))
        if len(s) > 100: _save(name, s); return s, "CFTC"
    except Exception: pass
    s = _load(name); return (s, "copie locale") if s is not None else (pd.Series(dtype=float), "indisponible")

def lier(avant, apres):
    """Prolonge une série récente par une plus ancienne, raccordée au premier jour commun."""
    if apres.empty: return avant
    if avant.empty: return apres
    k = apres.iloc[0] / avant.reindex(apres.index).ffill().iloc[0]
    return pd.concat([avant.loc[:apres.index[0] - pd.Timedelta(days=1)] * k, apres]).sort_index()

def tout_charger(MARCHES):
    """Toutes les séries du tableau de bord. Renvoie (données, sources)."""
    D, src = {}, {}
    for nom, m in MARCHES.items():
        s, o = yahoo(m["ticker"])
        if m.get("avant"):
            a, o2 = yahoo(m["avant"]); s = lier(a, s) if not a.empty else s
        D[nom], src[nom] = s, o
    for k, t in [("vix", "^VIX"), ("gvz", "^GVZ"), ("dxy", "DX-Y.NYB"), ("or", "GC=F"), ("brent", "BZ=F")]:
        D[k], src[k] = yahoo(t)
    for k, f in [("dfii10", "DFII10"), ("dgs10", "DGS10"), ("usd_large", "DTWEXBGS"), ("cpi", "CPIAUCSL")]:
        D[k], src[k] = fred(f)
    ancien, _ = fred("DTWEXM")   # dollar large avant 2006 (série arrêtée), raccordé
    if not ancien.empty: D["usd_large"] = lier(ancien, D["usd_large"])
    D["fedfunds"], src["fedfunds"] = fred("FEDFUNDS")
    D["spec_or"], src["spec_or"] = cftc_or()
    D["ndx_ew"], src["ndx_ew"] = ndx_parts_egales()
    D["titres"], src["titres"] = titres_cours()
    D["marge"], src["marge"] = marge_finra()
    return D, src

def ndx_parts_egales():
    """Moyenne à parts égales des membres actuels du Nasdaq-100 (liste en fin de mois, fichier ndx_membres.csv), en indice base 100."""
    name = "ndx_ew"
    try:
        N = pd.read_csv(os.path.join(FICHIERS, "ndx_membres.csv")); mem = sorted(N[N.date == N.date.max()].ticker)
        import yfinance as yf
        df = yf.download(mem, period="2y", auto_adjust=False, progress=False, threads=True)["Close"]
        r = df.pct_change(fill_method=None).mean(axis=1).dropna(); s = _clean((1 + r).cumprod() * 100)
        if len(s) > 100: _save(name, s); return s, "Yahoo Finance (membres du NDX)"
    except Exception: pass
    s = _load(name); return (s, "copie locale") if s is not None else (pd.Series(dtype=float), "indisponible")

def titres_cours():
    """Cours et volumes sur 10 ans des titres candidats (3 ans d historique nécessaires avant une liste : rejouer jusqu à 2019) : compositions SOXX / IGV (compositions_actuelles.csv) et membres du NDX."""
    pc_, pv_ = os.path.join(CACHE, "titres_close.csv"), os.path.join(CACHE, "titres_volume.csv")
    try:
        c = pd.read_csv(os.path.join(FICHIERS, "compositions_actuelles.csv"))
        N = pd.read_csv(os.path.join(FICHIERS, "ndx_membres.csv"))
        tk = sorted({str(t).replace(".", "-") for t in list(c.ticker.dropna()) + list(N[N.date == N.date.max()].ticker)} | {"XLP", "PHYS"})
        import yfinance as yf
        df = yf.download(tk, period="10y", auto_adjust=False, progress=False, threads=True)
        cl, vo = df["Close"], df["Volume"]
        cl.index = pd.to_datetime(cl.index).tz_localize(None).normalize(); vo.index = cl.index
        if cl.notna().sum().gt(250).sum() > 50:
            cl.to_csv(pc_); vo.to_csv(pv_); return dict(close=cl, volume=vo), "Yahoo Finance"
    except Exception: pass
    if os.path.exists(pc_):
        return dict(close=pd.read_csv(pc_, index_col=0, parse_dates=True), volume=pd.read_csv(pv_, index_col=0, parse_dates=True)), "copie locale"
    return None, "indisponible"

def marge_finra():
    """Dette sur marge FINRA (débit des comptes sur marge, mensuel, depuis 1997). Copie locale de secours dans boussoles/."""
    url = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
    dst = os.path.join(CACHE, "margin-statistics.xlsx"); local = os.path.join(FICHIERS, "margin-statistics.xlsx"); srcx = "copie locale"
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 200 and len(r.content) > 5000: open(dst, "wb").write(r.content); srcx = "FINRA"
    except Exception: pass
    for f in (dst, local):
        try:
            F = pd.read_excel(f); F = F.iloc[:, :2]; F.columns = ["mois", "dette"]; F["mois"] = pd.to_datetime(F.mois)
            return F.sort_values("mois").set_index("mois").dette.astype(float), srcx if f == dst else "copie locale (livrée avec l'application)"
        except Exception: continue
    return pd.Series(dtype=float), "indisponible"
