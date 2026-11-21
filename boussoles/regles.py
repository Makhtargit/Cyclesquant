"""Seuils et lois validés dans les dossiers SCANOPTIMUS9 (protocoles écrits avant calcul).
Ne modifier qu'après un nouveau test : ce sont des références, pas des réglages."""

# Marchés : symbole Yahoo, seuil de cycle, seuil de mini-cycle (ajustés à la volatilité, règle de l'or)
MARCHES = {
    "SOX": dict(ticker="^SOX", cycle=0.421, mini=0.105, mini_recent=0.108, tech=True, groupe="tech"),
    "Logiciel": dict(ticker="IGV", cycle=0.325, mini=0.081, mini_recent=0.073, tech=True, groupe="tech"),
    "NDX": dict(ticker="^NDX", cycle=0.292, mini=0.073, mini_recent=0.057, tech=True, groupe="tech"),
    "S&P 500": dict(ticker="^GSPC", cycle=0.199, mini=0.050, mini_recent=0.041, tech=False, groupe="tech"),
    "Mines d'or (GDX)": dict(ticker="GDX", avant="^XAU", cycle=0.436, mini=0.109, mini_recent=0.107, tech=False, groupe="or"),
    "Pétrolières (XLE)": dict(ticker="XLE", avant="XOM", cycle=0.296, mini=0.074, mini_recent=0.063, tech=False, groupe="pétrole"),
}

# Réglages des signaux par groupe (recalibrage_2022, recalibrage_or_petrole, peremption — 17/11/2026).
# S5 : krach k × seuil sous le plus haut 21 s. (5 dernières séances) ; VIX max 5 s. ≥ son centile q (250 s.) ; reflux rf (None = sans) ;
#      rebond r × seuil depuis le plus bas 5 s. ; rel = meilleur que le S&P sur 5 s. ; seuil = "LT" ou "récent".
# P4 : vitesse 20 s. au rang ≥ q (dans les 10 s.) ; rel = avec force relative ; VIX ≥ reveil × son plus bas 20 s.
REGLAGES = {
    "tech": dict(s5=dict(k=0.75, q=0.70, rf=None, r=0.25, rel=False, seuil="LT"), p4=dict(q=0.90, reveil=1.30, rel=True),
                 revision="novembre 2028", s5_preuve="+5,7 % par trade, 74 % des mini-creux attrapés (2022-2026, 88 trades)", timable=True),
    "or": dict(s5=dict(k=0.75, q=0.60, rf=None, r=0.125, rel=True, seuil="récent"), p4=dict(q=0.95, reveil=1.30, rel=False),
               revision="novembre 2030", s5_preuve="+7,3 % par trade sur 2022-2026, mais dégrade la stratégie or sur 2013-2026 : repère seulement, ne pas trader dessus", timable=True, repere=True),
    "pétrole": dict(s5=dict(k=0.75, q=0.70, rf=None, r=0.25, rel=False, seuil="LT"), p4=dict(q=0.90, reveil=1.30, rel=True),
                    revision="—", s5_preuve="aucune règle de creux ne bat le hasard sur le pétrole", timable=False),
}
SP = "S&P 500"

SEUIL = dict(
    vix_s7=30.0,            # S7 des cycles : pic du VIX sur 20 séances ≥ 30
    reflux=0.85,            # peur qui reflue : VIX ≤ 0,85 × son pic
    vix_q=0.80,             # S7 mini : VIX max 5 s. ≥ son 80e percentile sur 250 s.
    retard=-0.033,          # gros retard sur le S&P (20 séances)
    taux_reel_12m=0.5,      # point de taux réel sur 12 mois : fond défavorable tech
    taux10_6m=1.0,          # point de taux 10 ans sur 6 mois : alerte de sortie (avec indice sous moyenne 50)
    ruee_dollar=0.0114,     # dollar large sur 10 séances
    non_retour=2.5,         # seuils mini : la correction finit souvent le cycle
    approche=2.0,
    p4_vitesse=0.95, p4_reveil=1.15,
    depart_vif=0.93,        # rebond des 5 premières séances, en seuils mini
)

def duree_attendue_mini(vix_au_pic):
    """Loi du VIX des mini-corrections (tech 1990-2009, n = 236) : durée en séances, facteur d'erreur ≈ 2."""
    return 13.8 * (vix_au_pic / 20.0) ** -1.24

LOIS = [
    ("Creux", "VIX au-dessus de son 80e percentile + gros retard sur le S&P", "Premier franchissement du 80e percentile du VIX dans les 7 séances ET indice ≤ −3,3 pts contre le S&P sur 20 séances", "Mini-creux dans les 7 séances", "36-40 % (tech), 19-46 % (aveugle)", "6-15 %", "reperes_mini_cycles"),
    ("Creux", "VIX au-dessus de son 80e percentile", "Premier franchissement après 10 séances en dessous", "Mini-creux dans les 7 séances", "14-36 %", "8-16 %", "reperes_mini_cycles"),
    ("Creux", "Signal de creux S5 (réglage 2022)", "Tech : −0,75 seuil mini sous le plus haut 21 s. ; VIX max 5 s. ≥ 70e centile, sans reflux ; rebond ≥ 1/4 de seuil. Or : VIX ≥ 60e centile, rebond 1/8, meilleur que le S&P, seuil récent", "Près d'un mini-creux ; gain moyen par trade géré", "Tech +5,7 % (74 % des creux) ; or +7,3 % (81 %), 2022-2026", "", "recalibrage_2022, recalibrage_or_petrole, peremption"),
    ("Risque", "Point d'invalidation du S5 (couteau)", "Clôture sous le plus bas des 5 séances avant le signal", "Sortir, attendre le signal suivant", "≈ 45 % des signaux ; perte type −5 à −7,5 %", "", "gestion_couteau_tech"),
    ("Risque", "Ruée vers le dollar", "Dollar large ≥ +1,14 % sur 10 séances", "Part de couteaux", "57-74 %", "30-45 %", "diag_s7_mini_tech"),
    ("Creux", "Départ vif après le creux", "Rebond ≥ 0,93 seuil mini en 5 séances", "Creux de rebond (hausse ≥ 2 seuils)", "75-80 %", "≈ 65 %", "creux_rebond_tech"),
    ("Loi", "Loi du VIX (mini-corrections)", "Durée ≈ 13,8 × (VIX au pic / 20)^−1,24 séances ; vitesse ∝ VIX", "Durée attendue (facteur d'erreur ≈ 2)", "ρ −0,34 à −0,55", "", "mini_cycles_tech"),
    ("Risque", "Point de non-retour", "Correction ≥ 2,5 seuils mini depuis le mini-pic", "La correction finit le cycle", "54-78 % (tech)", "", "mini_cycles_tech"),
    ("Cycle", "Signal S7 des cycles (entrée A)", "Krach ≥ 1 seuil de cycle sous le plus haut 1 an (60 s.) ; VIX ≥ 30 puis −15 % ; amorce ≥ 1 seuil mini ; meilleur que le S&P (20 s.) ; plus bas vieux de 10 s.", "Creux de cycle", "7-9 creux sur 8-9, p < 0,001", "", "entree_tech"),
    ("Cycle", "Sortie de la stratégie A", "Recul d'un seuil de cycle depuis le plus haut depuis l'entrée", "Fin de cycle", "Bat la détention 1990-2009, égale 2010-2026", "", "strategie_actuelle_tech"),
    ("Pic", "Signal de pic P4 (réglage 2022)", "Tech : vitesse 20 s. au rang ≥ 0,90 avec force relative, puis VIX ≥ 1,30 × son plus bas 20 s. Or : rang ≥ 0,95, VIX ≥ 1,30", "Près d'un mini-pic", "Tech 37 % (hasard 17 %) ; or 46 % (15 %), puis −0,4 % à 20 s.", "15-17 %", "recalibrage_2022, recalibrage_or_petrole"),
    ("Risque", "Interrupteur coût du capital (X5)", "Taux 10 ans +1 pt sur 6 mois OU Fed +1 pt sur 12 mois, ET indice sous sa moyenne 50 ; retour au S7 suivant ou dès que l'alerte s'éteint", "Se mettre à l'abri pendant les chocs de taux", "NDX pire baisse −28 % contre −39 % (2010-2026), rendement égal", "", "alerte_taux_sortie"),
    ("Fond", "Taux réel 10 ans sur 12 mois", "Hausse ≥ +0,5 pt", "Tech contre le marché sur 12 mois", "NDX +2 % (contre +11 % quand il baisse)", "", "niveau_tech"),
    ("Titres", "Bêta selon la phase", "Hausse → bêta élevé ; baisse → bêta faible", "Écart haut − bas tiers de bêta par mois", "+1,6 à +3,3 % / −2,7 à −2,9 %", "", "fond_titres_tech"),
    ("Or", "Décor + amorce du creux de l'or", "Décor (60 s.) : dollar rang ≥ 90, taux réel rang ≥ 90, spéculateurs rang ≤ 10 (3 ans) ; amorce (20 s.) : taux réel en baisse, GVZ en baisse, GDX meilleur que le S&P", "Entrée : part de mines = budget (cœur de 2 mines), le reste en PHYS", "Part or 2013-2026 : +20,5 %/an, −36 % ; 2022-2026 : +40,6 %, −28 % (or_phys)", "", "dossier_or_final"),
    ("Or", "Budget de risque or", "50 % de mines en surchauffe ; 90 % en correction de 17-25 % ayant dépassé sa durée ; sinon 70 % ; le reste en PHYS", "Part de mines", "Validé en apprentissage croisé", "", "budget_risque_or"),
]

# Péremption (journal de décisions, 17/11/2026) : réglages = date fixe ; fichiers = date du fichier + durée de vie (jours).
PEREMPTION_REGLAGES = [
    ("Réglages tech · S5, P4, interrupteur, cœur", "2028-11-17"),
    ("Réglages or · P4 or, S5 or (repère)", "2030-11-17"),
]
PEREMPTION_FICHIERS = {"compositions_actuelles.csv": ("Poids SOXX / IGV", 92), "ndx_membres.csv": ("Membres du NDX", 30), "institutions_13f.csv": ("Déclarations 13F", 92)}
PEREMPTION_GDX = 183   # vaut aussi pour XLP (composition SEC)   # GDX : composition SEC (NPORT), publiée avec ~60 jours de retard ; une nouvelle chaque trimestre

# Fin de cycle déclarée par le trader : mécanisme supprimé le 20/11/2026 — le système décide seul de la fin des cycles (sortie A).
DATE_CALIBRAGE = "2026-11-17"   # dernier recalibrage (recalibrage_2022, données au 13/11/2026)
