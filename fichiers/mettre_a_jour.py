"""
SCANOPTIMUS9 — Mise à jour de tous les fichiers de l'outil, dans ce dossier « fichiers ».
Notice complète : NOTICE.md (même dossier).

À lancer sur ton ordinateur, depuis le dossier de l'application :
    pip install requests pandas yfinance openpyxl
    python fichiers/mettre_a_jour.py            → tout ce qui est périmé ou presque (moins de 15 jours)
    python fichiers/mettre_a_jour.py tout       → tout, même ce qui est encore frais
    python fichiers/mettre_a_jour.py ndx        → une seule étape : ndx, ishares, sec, marge ou 13f

AVANT DE LANCER les étapes « sec » et « 13f » : remplace la ligne CONTACT par ton nom et ton e-mail (la SEC l'exige ;
ils ne sont envoyés qu'à elle). Les autres étapes n'en ont pas besoin.

Chaque étape garde l'ancien fichier (suffixe .ancien) et écrit ce qu'elle a fait dans journal_mises_a_jour.txt.
Une étape qui échoue ne touche pas au fichier en place.
"""
import os, re, io, sys, csv, time, json, glob, shutil, datetime as dt
import requests, pandas as pd, numpy as np

CONTACT = "Prenom Nom votre.email@exemple.com"     # ← à remplacer (étapes sec et 13f)
DOSSIER_13F = os.path.expanduser("~/donnees_13f")  # déclarations 13F brutes (≈ 600 Mo, hors de l'application)

ICI = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.join(ICI, "scripts")
F_COMPO, F_NDX, F_13F, F_MARGE = (os.path.join(ICI, f) for f in ["compositions_actuelles.csv", "ndx_membres.csv", "institutions_13f.csv", "margin-statistics.xlsx"])
NAV = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36", "Accept": "application/json, text/plain, */*"}
J = open(os.path.join(ICI, "journal_mises_a_jour.txt"), "a", encoding="utf-8")
def note(x): x = f"{dt.datetime.now():%d/%m/%Y %H:%M}  {x}"; print(x); J.write(x + "\n"); J.flush()
def ecrire(df, chemin):
    if os.path.exists(chemin): shutil.copy2(chemin, chemin + ".ancien")
    df.to_csv(chemin + ".tmp", index=False); os.replace(chemin + ".tmp", chemin)

# ------------------------------------------------------------------ péremption (mêmes durées que l'outil)
def age_jours():
    out = {}
    try: out["ndx"] = (pd.Timestamp.today() - pd.to_datetime(pd.read_csv(F_NDX).date).max()).days - 30
    except Exception: out["ndx"] = 999
    try:
        c = pd.read_csv(F_COMPO); d = c.groupby("etf").date.max().map(pd.Timestamp)
        out["ishares"] = (pd.Timestamp.today() - d[["SOXX", "IGV"]].min()).days - 92
        out["sec"] = (pd.Timestamp.today() - d[["GDX", "XLP"]].min()).days - 183
    except Exception: out["ishares"] = out["sec"] = 999
    try: out["13f"] = (pd.Timestamp.today() - pd.to_datetime(pd.read_csv(F_13F).dispo).max()).days - 92
    except Exception: out["13f"] = 999
    try: out["marge"] = (pd.Timestamp.today() - pd.Timestamp(dt.datetime.fromtimestamp(os.path.getmtime(F_MARGE)))).days - 40
    except Exception: out["marge"] = 999
    return out   # > -15 : périmé ou périme dans moins de 15 jours

# ------------------------------------------------------------------ 1. membres du Nasdaq-100
def etape_ndx():
    r = requests.get("https://api.nasdaq.com/api/quote/list-type/nasdaq100", headers=NAV, timeout=30)
    rows = r.json()["data"]["data"]["rows"]; tick = sorted({x["symbol"].strip().upper().replace(".", "-") for x in rows if x.get("symbol")})
    if not 95 <= len(tick) <= 110: raise ValueError(f"{len(tick)} membres lus : liste suspecte, fichier inchangé")
    N = pd.read_csv(F_NDX); d = pd.offsets.BDay().rollback(pd.Timestamp.today().normalize())
    N = pd.concat([N[N.date != f"{d:%Y-%m-%d}"], pd.DataFrame({"date": f"{d:%Y-%m-%d}", "ticker": tick})])
    A0 = pd.read_csv(F_NDX); anc = set(A0[A0.date == A0.date.max()].ticker); ecrire(N, F_NDX)
    note(f"NDX : {len(tick)} membres au {d:%d/%m/%Y} · entrées {sorted(set(tick) - anc) or 'aucune'} · sorties {sorted(anc - set(tick)) or 'aucune'}")

# ------------------------------------------------------------------ 2. poids SOXX et IGV (iShares, fichier du jour)
ISHARES = {"SOXX": 239705, "IGV": 239771}
def lire_ishares(texte, etf):
    lignes = texte.splitlines(); d = None
    for l in lignes[:12]:
        m = re.search(r'as of"?,?\s*"?([A-Za-z]{3} \d{1,2}, \d{4})', l)
        if m: d = pd.Timestamp(dt.datetime.strptime(m.group(1), "%b %d, %Y"))
    i = next(k for k, l in enumerate(lignes) if l.startswith("Ticker,"))
    df = pd.read_csv(io.StringIO("\n".join(lignes[i:])), on_bad_lines="skip")
    if "Asset Class" in df: df = df[df["Asset Class"].astype(str).str.contains("Equity")]
    df = df[df.Ticker.notna() & (df.Ticker.astype(str).str.strip() != "-")]
    df["poids"] = pd.to_numeric(df["Weight (%)"].astype(str).str.replace(",", ""), errors="coerce")
    df = df[df.poids > 0].sort_values("poids", ascending=False)
    return pd.DataFrame({"etf": etf, "ticker": df.Ticker.astype(str).str.strip().str.replace(".", "-", regex=False), "poids": df.poids.round(4),
                         "date": f"{(d or pd.Timestamp.today()):%Y-%m-%d}", "nom": df.Name.astype(str).str.strip()})
def etape_ishares():
    C = pd.read_csv(F_COMPO); neuf = []
    for etf, pid in ISHARES.items():
        r = requests.get(f"https://www.ishares.com/us/products/{pid}/x/1467271812596.ajax?fileType=csv&fileName={etf}_holdings&dataType=fund", headers=NAV, timeout=60)
        df = lire_ishares(r.content.decode("utf-8-sig", errors="ignore"), etf)
        if len(df) < 20: raise ValueError(f"{etf} : {len(df)} lignes lues, fichier inchangé")
        neuf.append(df); note(f"{etf} : {len(df)} titres au {df.date.iloc[0]} · 5 premiers {', '.join(df.ticker.head(5))}")
    C = pd.concat([C[~C.etf.isin(ISHARES)]] + neuf); ecrire(C, F_COMPO)

# ------------------------------------------------------------------ 3. poids GDX et XLP (déclarations NPORT-P à la SEC)
SEC_ETF = {"GDX": "Gold Miners", "XLP": "Consumer Staples"}
def sec_session():
    if "exemple.com" in CONTACT: raise SystemExit("Remplace d'abord la ligne CONTACT (ton nom et ton e-mail) en haut du script.")
    s = requests.Session(); s.headers.update({"User-Agent": CONTACT, "Accept-Encoding": "gzip, deflate"}); return s
def sec_get(s, url):
    for essai in range(5):
        try:
            r = s.get(url, timeout=60); time.sleep(0.12)
            if r.status_code == 200: return r
            if r.status_code in (403, 429, 503): time.sleep(5 * (essai + 1)); continue
            return r
        except Exception: time.sleep(3)
    return None
def lire_nport(x):
    x = re.sub(r"<(/?)[A-Za-z0-9]+:", r"<\1", x); g = lambda t, b: (re.search(rf"<{t}>\s*([^<]*?)\s*</{t}>", b) or [None, ""])[1]
    rows = [(g("name", b), float(g("pctVal", b) or 0), g("assetCat", b)) for b in re.findall(r"<invstOrSec>(.*?)</invstOrSec>", x, re.S)]
    return g("repPdDate", x), g("seriesName", x), pd.DataFrame(rows, columns=["nom", "pct", "cat"])
def correspondance(etf, nom, M):
    u = str(nom).upper()
    for k, t in M[M.etf == etf][["mot_cle", "ticker"]].itertuples(index=False):
        if k in u: return t if isinstance(t, str) and t else "ABSENT"
    return None
def top15(etf, df, M):
    import html
    df = df[(df.cat == "EC") & ~df.nom.str.upper().str.contains("STATE STREET|MONEY MARKET|ETF|REPURCHASE", na=False)].copy(); df["nom"] = df.nom.map(html.unescape)
    df["ticker"] = df.nom.map(lambda n: correspondance(etf, n, M))
    ok = df[df.ticker.notna() & (df.ticker != "ABSENT")].groupby(["ticker"]).agg(poids=("pct", "sum"), nom=("nom", "first")).reset_index()
    ok = ok.sort_values("poids", ascending=False).head(15); inc = df[df.ticker.isna() & (df.pct >= ok.poids.min())]
    if len(inc): note(f"  {etf} : ATTENTION, gros poids sans ticker : {', '.join(f'{n} ({p:.1f} %)' for n, p in zip(inc.nom, inc.pct))} → ajoute une ligne dans scripts/correspondances_noms.csv (etf, mot-clé du nom, ticker Yahoo) puis relance « sec »")
    return ok
def etape_sec():
    s = sec_session(); M = pd.read_csv(os.path.join(SCR, "correspondances_noms.csv"), keep_default_na=False)
    j = sec_get(s, "https://www.sec.gov/files/company_tickers_mf.json").json(); serie = {}
    for ligne in j["data"]:
        d = dict(zip(j["fields"], ligne))
        if d.get("symbol") in SEC_ETF: serie[d["symbol"]] = d["seriesId"]
    C = pd.read_csv(F_COMPO); neuf = []
    for etf, mot in SEC_ETF.items():
        r = sec_get(s, f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={serie[etf]}&type=NPORT-P&dateb=&owner=include&count=10&output=atom")
        meilleur = None
        for href in re.findall(r"<filing-href>(.*?)</filing-href>", r.text)[:6]:
            m = re.search(r"/data/(\d+)/(\d{18})/", href)
            if not m: continue
            base = f"https://www.sec.gov/Archives/edgar/data/{m.group(1)}/{m.group(2)}/"; x = sec_get(s, base + "primary_doc.xml")
            if x is None or x.status_code != 200: continue
            per, nom_serie, df = lire_nport(x.text)
            if mot.lower() in nom_serie.lower() and len(df) and (meilleur is None or per > meilleur[0]): meilleur = (per, df)
        if meilleur is None: raise ValueError(f"{etf} : aucune déclaration NPORT-P lisible")
        t = top15(etf, meilleur[1], M); t.insert(0, "etf", etf); t["date"] = meilleur[0]; t["poids"] = t.poids.round(4)
        neuf.append(t[["etf", "ticker", "poids", "date", "nom"]]); note(f"{etf} : composition au {meilleur[0]} · 5 premiers {', '.join(t.ticker.head(5))}")
    C = pd.concat([C[~C.etf.isin(SEC_ETF)]] + neuf); ecrire(C, F_COMPO)

# ------------------------------------------------------------------ 4. crédit sur marge (FINRA) — copie de secours
def etape_marge():
    r = requests.get("https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx", headers=NAV, timeout=60)
    if r.status_code != 200 or len(r.content) < 5000: raise ValueError(f"FINRA a répondu {r.status_code}")
    F = pd.read_excel(io.BytesIO(r.content)); dernier = pd.to_datetime(F.iloc[:, 0]).max()
    if os.path.exists(F_MARGE): shutil.copy2(F_MARGE, F_MARGE + ".ancien")
    open(F_MARGE, "wb").write(r.content); note(f"Crédit sur marge : dernier mois {dernier:%m/%Y}")

# ------------------------------------------------------------------ 5. déclarations 13F des gérants actifs → institutions_13f.csv
GERANTS = ["FMR LLC", "T. ROWE PRICE ASSOCIATES", "CAPITAL WORLD INVESTORS", "CAPITAL RESEARCH GLOBAL INVESTORS", "WELLINGTON MANAGEMENT GROUP",
           "JENNISON ASSOCIATES", "BAILLIE GIFFORD", "TIGER GLOBAL MANAGEMENT", "COATUE MANAGEMENT", "VIKING GLOBAL INVESTORS", "LONE PINE CAPITAL",
           "MAVERICK CAPITAL", "D1 CAPITAL PARTNERS", "WHALE ROCK CAPITAL MANAGEMENT", "DRAGONEER INVESTMENT GROUP", "SOROS FUND MANAGEMENT",
           "DUQUESNE FAMILY OFFICE", "APPALOOSA", "POINT72 ASSET MANAGEMENT", "ARK INVESTMENT MANAGEMENT", "FRANKLIN RESOURCES",
           "SANDS CAPITAL MANAGEMENT", "BROWN ADVISORY", "ALKEON CAPITAL MANAGEMENT", "LIGHT STREET CAPITAL"]
def telecharger_13f(s):
    os.makedirs(DOSSIER_13F, exist_ok=True); idx_f = os.path.join(DOSSIER_13F, "index.json")
    index = json.load(open(idx_f, encoding="utf-8")) if os.path.exists(idx_f) else {}
    for nom in GERANTS:
        cik = index.get(nom, {}).get("cik")
        if not cik:
            r = sec_get(s, f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={requests.utils.quote(nom)}&type=13F-HR&dateb=&owner=include&count=40&output=atom")
            c = re.findall(r"<cik>(\d+)</cik>", r.text) if r is not None else []
            if not c: note(f"  13F : {nom} introuvable"); continue
            cik = c[0]; index[nom] = dict(cik=cik)
        rep = os.path.join(DOSSIER_13F, re.sub(r"[^A-Za-z0-9]+", "_", nom).strip("_")); os.makedirs(rep, exist_ok=True)
        sub = sec_get(s, f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json").json()["filings"]["recent"]; n = 0
        for forme, acc, dte, per in zip(sub["form"], sub["accessionNumber"], sub["filingDate"], sub.get("reportDate", [""] * len(sub["form"]))):
            if forme != "13F-HR" or dte < "2013-06-01": continue
            dst = os.path.join(rep, f"{per or dte}_{acc}.xml")
            if os.path.exists(dst): continue
            base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"; idx = sec_get(s, base + "index.json")
            if idx is None or idx.status_code != 200: continue
            for f in [x["name"] for x in idx.json()["directory"]["item"] if x["name"].lower().endswith(".xml") and x["name"].lower() != "primary_doc.xml"]:
                r = sec_get(s, base + f)
                if r is not None and r.status_code == 200 and b"infoTable" in r.content[:20000]: open(dst, "wb").write(r.content); n += 1; break
        if n: note(f"  13F : {nom} · {n} nouvelle(s) déclaration(s)")
    json.dump(index, open(idx_f, "w", encoding="utf-8"), indent=1)
def reduire_13f():
    """Une table par gérant (periode, emetteur, valeur), recalculée seulement si une déclaration est arrivée."""
    out = os.path.join(DOSSIER_13F, "reduit"); os.makedirs(out, exist_ok=True); tout = []
    for rep in sorted(d for d in os.listdir(DOSSIER_13F) if os.path.isdir(os.path.join(DOSSIER_13F, d)) and d != "reduit"):
        xs = sorted(glob.glob(os.path.join(DOSSIER_13F, rep, "*.xml"))); dst = os.path.join(out, rep + ".csv")
        if not xs: continue
        if not os.path.exists(dst) or os.path.getmtime(dst) < max(os.path.getmtime(x) for x in xs):
            rows = []
            for f in xs:
                per = os.path.basename(f).split("_")[0]; x = re.sub(r"<(/?)[A-Za-z0-9]+:", r"<\1", open(f, encoding="utf-8", errors="ignore").read())
                for b in re.findall(r"<infoTable>(.*?)</infoTable>", x, re.S):
                    g = lambda t: (re.search(rf"<{t}>\s*([^<]*?)\s*</{t}>", b) or [None, ""])[1]
                    if not g("putCall"): rows.append((per, g("nameOfIssuer"), g("value")))
            pd.DataFrame(rows, columns=["periode", "emetteur", "valeur"]).to_csv(dst, index=False)
        t = pd.read_csv(dst); t["gerant"] = rep; tout.append(t)
    return pd.concat(tout)
STOP = {"INC", "CORP", "CORPORATION", "CO", "LTD", "PLC", "HOLDINGS", "HLDGS", "GROUP", "NEW", "CL", "A", "THE", "COM", "N", "V", "NV", "SA", "AG", "SPONSORED", "ADR", "ADS", "LIMITED", "TECHNOLOGIES", "TECHNOLOGY", "&AMP;", "&"}
def cle(n):
    w = [x for x in re.sub(r"[^A-Z0-9& ]", " ", str(n).upper().replace("&AMP;", "&")).split() if x not in STOP]
    return " ".join(w[:2]) if w else ""
def panel_13f(D, prix):
    """Méthode de 13f.md : part tech de chaque gérant, variation active (effet prix retiré), moyenne à poids égal.
    prix : DataFrame quotidien avec les colonnes SOX, Logiciel, NDX, SP."""
    D = D.copy(); D["periode"] = pd.to_datetime(D.periode); D["valeur"] = pd.to_numeric(D.valeur, errors="coerce"); D = D[D.valeur > 0]
    D = D[~D.emetteur.astype(str).str.upper().str.contains("ISHARES|SPDR|INVESCO QQQ|VANGUARD|SELECT SECTOR|PROSHARES", na=False)]
    tech = set(open(os.path.join(SCR, "noms_tech_13f.txt"), encoding="utf-8").read().split("\n")) - {""}
    try: tech |= set(pd.read_csv(F_COMPO).query("etf in ['SOXX', 'IGV']").groupby("etf").head(30).nom.map(cle)) - {""}
    except Exception: pass
    D["tech"] = D.emetteur.map(cle).isin(tech)
    tot = D.groupby(["gerant", "periode"]).valeur.sum(); te = D[D.tech].groupby(["gerant", "periode"]).valeur.sum()
    G = (te.reindex(tot.index).fillna(0) / tot).rename("part").reset_index()
    def rq(s, a, b): s = s.dropna(); return s.asof(b) / s.asof(a) - 1
    per = sorted(G.periode.unique()); R = {}
    for a, b in zip(per[:-1], per[1:]):
        R[b] = (np.mean([rq(prix[k], a, b) for k in ["SOX", "Logiciel", "NDX"]]), rq(prix["SP"], a, b), rq(prix["NDX"], a, b))
    rows = []
    for g, x in G.sort_values("periode").groupby("gerant"):
        x = x.set_index("periode")
        for a, b in zip(x.index[:-1], x.index[1:]):
            if b not in R or (b - a).days > 100: continue
            rt, ro, rn = R[b]; s0 = x.part[a]; pas = s0 * (1 + rt) / (s0 * (1 + rt) + (1 - s0) * (1 + ro))
            rows.append(dict(periode=b, part=x.part[b], actif=x.part[b] - pas, ndx_q=rn))
    A = pd.DataFrame(rows)
    P = A.groupby("periode").agg(part=("part", "mean"), actif=("actif", "mean"), reduisent=("actif", lambda v: (v < 0).mean()), ndx_q=("ndx_q", "first"), n=("actif", "size")).reset_index()
    P.insert(1, "dispo", (P.periode + pd.Timedelta(days=45)).dt.strftime("%Y-%m-%d")); P["T4"] = ((P.actif < 0) & (P.ndx_q > 0)).astype(int)
    P["periode"] = P.periode.dt.strftime("%Y-%m-%d"); return P.round(4)
def etape_13f():
    import yfinance as yf
    s = sec_session(); telecharger_13f(s); D = reduire_13f()
    px = {}
    for k, t in {"SOX": "^SOX", "Logiciel": "IGV", "NDX": "^NDX", "SP": "^GSPC"}.items():
        c = yf.download(t, start="2013-01-01", auto_adjust=False, progress=False, threads=False)["Close"]
        c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c; c.index = pd.to_datetime(c.index).tz_localize(None); px[k] = c
    P = panel_13f(D, pd.DataFrame(px)); P = P[P.n >= 15]   # trimestre complet : au moins 15 gérants ont déclaré
    ecrire(P, F_13F); r = P.iloc[-1]
    note(f"13F : dernier trimestre {r.periode} (publié le {r.dispo}) · variation active {r.actif * 100:+.1f} pt · {r.reduisent:.0%} des gérants allègent · "
         + ("ALERTE (vendent dans la hausse)" if r.T4 or r.actif <= -0.02 else "pas d'alerte"))

# ------------------------------------------------------------------
ETAPES = {"ndx": etape_ndx, "ishares": etape_ishares, "sec": etape_sec, "marge": etape_marge, "13f": etape_13f}
if __name__ == "__main__":
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg in ETAPES: choix = [arg]
    elif arg == "tout": choix = list(ETAPES)
    else:
        age = age_jours(); choix = [k for k in ETAPES if age.get(k, 999) > -15]
        note("À mettre à jour : " + (", ".join(choix) if choix else "rien, tout est frais (lance « tout » pour forcer)"))
    for k in choix:
        try: ETAPES[k]()
        except SystemExit as e: note(f"{k} : {e}")
        except Exception as e: note(f"{k} : ÉCHEC, fichier inchangé ({type(e).__name__} : {e})")
    note("Terminé. Relance l'application (bouton « Mettre à jour les données »).")
