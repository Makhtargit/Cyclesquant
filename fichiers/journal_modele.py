"""Journal du portefeuille modèle (à lancer chaque soir après la clôture : GitHub Actions ou à la main).
    python fichiers/journal_modele.py
Ajoute au fichier fichiers/journal_modele.csv les séances manquantes depuis le déploiement (19/11/2026)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from boussoles.donnees import tout_charger
from boussoles.regles import MARCHES
from boussoles.modele import completer, JOURNAL, valoriser
D, src = tout_charger(MARCHES)
print("sources :", {k: v for k, v in src.items()})
j, n = completer(D, max_seances=400)
j.to_csv(JOURNAL, index=False)
v = valoriser(j, D["titres"]["close"]) if D.get("titres") else None
print(f"{n} séance(s) ajoutée(s) ; journal : {len(j)} lignes" + (f" ; valeur du modèle {v.iloc[-1]:.2f} (base 100)" if v is not None and len(v) else ""))
