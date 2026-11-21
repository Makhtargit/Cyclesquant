"""Cours des titres et indices de l'énergie (test protocole_energie, 20/11/2026).
À lancer depuis le dossier de l'application :  python fichiers/cours_energie.py
Résultat : fichiers/cours_energie.zip — à m'envoyer."""
import zipfile
from pathlib import Path
import pandas as pd, yfinance as yf

ICI = Path(__file__).resolve().parent
INDICES = ["XLE", "XLU", "URA", "NLR", "ICLN", "XOP", "OIH", "TAN"]
TITRES = ["XOM", "CVX", "COP", "EOG", "WMB", "SLB", "KMI", "PSX", "MPC", "OKE", "VLO", "OXY", "BKR", "HAL", "FANG", "EQT", "TRGP", "DVN", "CTRA", "APA",
          "NEE", "SO", "DUK", "CEG", "VST", "AEP", "SRE", "D", "EXC", "PCG", "XEL", "ED", "PEG", "ETR", "NRG",
          "CCJ", "LEU", "OKLO", "SMR", "NXE", "UEC", "BWXT", "UUUU", "DNN",
          "FSLR", "ENPH", "SEDG", "RUN", "PLUG", "BE", "ORA"]
lignes = []
for t in INDICES + TITRES:
    try:
        d = yf.download(t, start="1998-12-01", interval="1d", auto_adjust=True, progress=False)
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        d = d[["Close", "Volume"]].dropna(subset=["Close"])
        if d.empty:
            print(f"{t:5s} aucune donnée"); continue
        lignes.append(pd.DataFrame({"date": pd.to_datetime(d.index).tz_localize(None).date, "close": d["Close"].values,
                                    "volume": d["Volume"].values, "ticker": t}))
        print(f"{t:5s} {len(d)} séances depuis {d.index[0].date()}")
    except Exception as e:
        print(f"{t:5s} ÉCHEC : {e}")
R = pd.concat(lignes, ignore_index=True)
f = ICI / "cours_energie.csv"; R.to_csv(f, index=False)
with zipfile.ZipFile(ICI / "cours_energie.zip", "w", zipfile.ZIP_DEFLATED) as z: z.write(f, f.name)
print(f"\nFini : {R.ticker.nunique()} titres. Envoie-moi fichiers/cours_energie.zip")
