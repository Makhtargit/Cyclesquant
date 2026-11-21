"""Cours d'ouverture et de clôture des titres tenus par le système depuis 2016 (test « nuit », 19/11/2026).
À lancer depuis le dossier de l'application :  python fichiers/cours_ouverture.py
Résultat : fichiers/cours_ouverture.zip — à m'envoyer."""
import zipfile
from pathlib import Path
import pandas as pd, yfinance as yf

ICI = Path(__file__).resolve().parent
TECH = ['AAPL', 'ADBE', 'ADSK', 'AMAT', 'AMD', 'APP', 'BIDU', 'BIIB', 'CDNS', 'CRM', 'CRWD', 'DOCU', 'FTNT', 'GOOG', 'INTC', 'KLAC',
        'LRCX', 'MCHP', 'MPWR', 'MRNA', 'MRVL', 'MU', 'NFLX', 'NOW', 'NVDA', 'NXPI', 'ORCL', 'PANW', 'PLTR', 'PYPL', 'QCOM', 'SNAP',
        'TER', 'TSLA', 'TTWO', 'WDAY', 'ZM']
OR = ['AU', 'BTG', 'CDE', 'EDV.L', 'GFI', 'HMY', 'KGC', 'PAAS', 'PHYS']
REPERES = ['^NDX', '^SOX', 'IGV', 'GDX', '^GSPC']
lignes = []
for t in TECH + OR + REPERES:
    try:
        d = yf.download(t, start="2015-11-01", interval="1d", auto_adjust=True, progress=False)
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        d = d[["Open", "Close"]].dropna(); d["ticker"] = t; lignes.append(d.reset_index())
        print(f"{t:6s} {len(d)} séances")
    except Exception as e:
        print(f"{t:6s} ÉCHEC : {e}")
R = pd.concat(lignes); R.columns = ["date", "open", "close", "ticker"]
f = ICI / "cours_ouverture.csv"; R.to_csv(f, index=False)
with zipfile.ZipFile(ICI / "cours_ouverture.zip", "w", zipfile.ZIP_DEFLATED) as z: z.write(f, f.name)
print(f"\nFini : {R.ticker.nunique()} titres. Envoie-moi fichiers/cours_ouverture.zip")
