# Dossier application — reconstruire Boussoles de A à Z

Nov 18, 2026 · @Makhtar

## Objet et principes

Boussoles est une application Streamlit en Python. Chaque soir, elle télécharge les marchés, applique les règles du système SCANOPTIMUS9 et affiche la position à tenir pour chaque part, avec les alertes qui l'éclairent. Ce dossier permet de la reconstruire de zéro, avec le système qu'elle applique.

**Principes de construction (non négociables)**

1. **La règle décide, le décor éclaire.** La position vient des familles A (cycle) et B (mini-cycle). Les alertes (familles C et D) ne décident jamais.
2. **Rien sans test.** Une règle entre dans `boussoles/regles.py` seulement après un protocole écrit avant le calcul et une victoire au concours (le statu quo concourt toujours).
3. **Pas d'anticipation.** Toute séance passée se rejoue avec les seules données connues ce jour-là. Les délais de publication sont respectés : 13F à 45 jours, marge FINRA le 25 du mois suivant, compositions SEC à 60 jours.
4. **Régime en cours d'abord.** Les réglages sont calés sur les 4 dernières années, avec l'historique en garde-fou. Chaque réglage a une date de péremption, et une sortie de cycle déclenche un recalibrage.
5. **Toujours une copie de secours.** Chaque téléchargement est copié dans `cache/`. Si une source ne répond pas, la dernière copie sert.
6. **Contraintes du trader :** titres seulement (ni ETF ni contrat à terme, sauf PHYS pour l'or), parts dehors en cash, pas de levier, 50 % au plus par part (25 % pour l'or). Break : capital à −30 % → tout couper ; blocage K2 → aucune entrée tech nouvelle (or et or-VIX libres) ; −35 % → arrêt du système.

## Architecture

L'application tient en 5 modules Python, un dossier de fichiers à mettre à jour et un cache. `regles.py` est la seule source des réglages : un changement de règle ne touche que ce fichier.

*(Schéma de l'architecture : voir le Claude Doc « Dossier application ». Sources en ligne et fichiers/ → donnees.py → calcul.py → titres.py → app.py → 4 onglets ; regles.py alimente calcul.py et titres.py.)*

Les données descendent de haut en bas. `donnees.py` télécharge et garde une copie, `calcul.py` calcule l'état de chaque marché, `titres.py` en tire les titres et les poids, et `app.py` affiche le tout.

| Chemin | Contenu |
| --- | --- |
| `app.py` | L'interface : quatre onglets, barre latérale, badge selon la règle, Conclusion du jour |
| `boussoles/regles.py` | `MARCHES`, `REGLAGES`, `SEUIL`, `LOIS`, péremptions, `DATE_CALIBRAGE` |
| `boussoles/donnees.py` | Téléchargements et copie de secours |
| `boussoles/calcul.py` | Signaux, stratégies, lois, climat, or, historique |
| `boussoles/titres.py` | Titres, cœurs, or en titres, portefeuille, péremptions |
| `boussoles/ui.py` | CSS, cartes, pastilles, jauges, sparklines |
| `fichiers/` | Fichiers périssables, `mettre_a_jour.py`, `NOTICE.md`, `scripts/` |
| `cache/` | Dernière copie de chaque série |
| `.streamlit/config.toml` | Thème sombre |
| `LISEZMOI.md`, `DOSSIER_APPLICATION.md` | Mode d'emploi et ce dossier |

## Données

L'application lit deux sortes de données. Les séries de marché se téléchargent seules à chaque ouverture et sont gardées 6 heures. Les fichiers périssables sont dans `fichiers/` et se mettent à jour par une seule commande.

**Séries téléchargées à l'ouverture (`boussoles/donnees.py` → `tout_charger`)**

| Clé | Source | Symbole | Usage |
| --- | --- | --- | --- |
| SOX, Logiciel, NDX, S&P 500 | Yahoo | ^SOX, IGV, ^NDX, ^GSPC | Indices des parts et référence |
| Mines d'or (GDX), Pétrolières (XLE) | Yahoo | GDX (prolongé par ^XAU), XLE (prolongé par XOM) | Repères or et pétrole |
| vix, gvz, dxy, or, brent | Yahoo | ^VIX, ^GVZ, DX-Y.NYB, GC=F, BZ=F | Peur, volatilité de l'or, dollar, matières premières |
| dfii10, dgs10, usd\_large, cpi, fedfunds | FRED | DFII10, DGS10, DTWEXBGS (+ DTWEXM avant 2006), CPIAUCSL, FEDFUNDS | Taux réel, taux 10 ans, dollar large, Fed |
| spec\_or | CFTC | Positions des spéculateurs sur l'or | Décor de l'or |
| ndx\_ew | Yahoo, membres de `ndx_membres.csv` | 2 ans | NDX à parts égales (concentration) |
| titres | Yahoo | Compositions + membres du NDX, 10 ans | Choix des titres, cœurs, poids |
| marge | FINRA (copie de secours : `fichiers/margin-statistics.xlsx`) | Dette sur marge mensuelle | Alerte crédit sur marge |

- Chaque série est copiée dans `cache/<clé>.csv`. Si la source ne répond pas, la copie sert : pastille 🟡 dans la barre latérale.
- Les séries anciennes sont raccordées au premier jour commun (`lier`).

**Fichiers périssables (`fichiers/`, notice complète : `fichiers/NOTICE.md`)**

| Fichier | Contenu | Durée de vie | Mise à jour |
| --- | --- | --- | --- |
| `ndx_membres.csv` | Membres du Nasdaq-100 (date, ticker) | 30 jours | `mettre_a_jour.py ndx` (API Nasdaq) |
| `compositions_actuelles.csv` | Poids SOXX, IGV (iShares) et GDX, XLP (SEC NPORT-P) | 92 jours (SOXX, IGV), 183 jours (GDX, XLP) | `ishares`, `sec` |
| `institutions_13f.csv` | Part tech de 23 gérants actifs, variation active | 92 jours | `13f` |
| `margin-statistics.xlsx` | Dette sur marge FINRA | 40 jours | `marge` |
| `scripts/correspondances_noms.csv` | Nom SEC → ticker Yahoo (GDX, XLP) | — | À la main, quand le script le demande |
| `scripts/noms_tech_13f.txt` | Émetteurs tech reconnus dans les 13F | — | Rarement |

- La commande unique est `python fichiers/mettre_a_jour.py`. Elle ne met à jour que ce qui périme dans les 15 jours.
- La ligne `CONTACT` du script doit porter ton nom et ton e-mail : la SEC l'exige.
- Les déclarations 13F brutes (environ 600 Mo) restent dans `~/donnees_13f`.

## Règles et formules

Toutes les valeurs ci-dessous sont dans `boussoles/regles.py` (`MARCHES`, `REGLAGES`, `SEUIL`). Elles ne changent qu'après un nouveau test.

**Seuils** : ils sont ajustés à la volatilité, avec l'or comme étalon. v est la volatilité annuelle du marché depuis 1990, v\_or celle de l'or sur 2001-2026.

```latex
\text{seuil mini} = 0{,}05 \cdot \frac{v}{v_{or}} \qquad \text{seuil de cycle} = 4 \times \text{seuil mini}
```

| Marché | Cycle | Mini (LT) | Mini (récent) |
| --- | --- | --- | --- |
| SOX | 0,421 | 0,105 | 0,108 |
| Logiciel | 0,325 | 0,081 | 0,073 |
| NDX | 0,292 | 0,073 | 0,057 |
| S&P 500 | 0,199 | 0,050 | 0,041 |
| GDX | 0,436 | 0,109 | 0,107 |
| XLE | 0,296 | 0,074 | 0,063 |

**Famille A, le cycle**

1. **S7 (entrée) :** les conditions sont vérifiées la même séance :
   - krach d'au moins 1 seuil de cycle sous le plus haut de 250 séances, dans les 60 dernières séances ;
   - pic du VIX sur 20 séances ≥ 30, et VIX revenu à 0,85 × ce pic au plus ;
   - rebond d'au moins 1 seuil mini depuis le plus bas ;
   - meilleur que le S&P sur 20 séances ;
   - plus bas de 60 séances vieux d'au moins 10 séances.
2. **Stratégie A :** entrée au S7, au moins 20 séances après la dernière sortie. Sortie quand le cours recule d'un seuil de cycle depuis son plus haut depuis l'entrée.
3. **Interrupteur coût du capital :**
   - il s'arme quand le taux 10 ans gagne au moins 1 pt sur 126 séances, ou la Fed au moins 1 pt sur 12 mois ;
   - il est actif si, en plus, l'indice est sous sa moyenne 50 : la part passe en cash ;
   - retour au S7 suivant, ou dès que l'alerte s'éteint.

**Famille B, le mini-cycle**

1. **Phase en temps réel :** on passe en correction quand le cours ≤ plus haut × (1 − seuil mini), et en hausse quand le cours ≥ plus bas × (1 + seuil mini).
2. **S5 tech (réglage 2022), quatre conditions :**
   - krach : ≤ −0,75 seuil mini sous le plus haut de 21 séances, dans les 5 dernières séances ;
   - peur : VIX maximal des 5 dernières séances ≥ son 70e centile sur 250 séances, sans exigence de reflux ;
   - rebond : ≥ 1/4 de seuil mini depuis le plus bas de 5 séances ;
   - seuil de long terme.
3. **S5 or :** VIX ≥ 60e centile, rebond 1/8 de seuil, meilleur que le S&P, seuil récent. C'est un repère seulement.
4. **Gestion du S5 :**
   - couteau : clôture sous le plus bas des 5 séances avant l'entrée ;
   - sinon, sortie à −1 seuil mini depuis le plus haut du trade.
5. **G3 (hausse effacée) :**
   - dans les 3 séances après un plus haut de 10 séances, une clôture ≤ la plus basse des 10 séances qui précédaient ce plus haut fait passer la part en cash ;
   - retour sur une clôture au-dessus de l'ancien plus haut de 10 séances, ou au S5 suivant.
6. **P4 (lecture) :**
   - vitesse 20 séances au rang ≥ 0,90 (0,95 pour l'or) dans les 10 dernières séances, avec force relative pour la tech ;
   - puis VIX ≥ 1,30 × son plus bas de 20 séances.

**Titres (L3)**

1. **Candidats :** les 15 plus gros poids de SOXX, IGV ou GDX, et pour le NDX les 15 plus gros volumes en dollars sur 60 séances. Il faut au moins 260 séances de cours.
2. **Bêta en correction :** médiane, sur les mini-corrections de l'indice des 2 dernières années, de (baisse du titre) / (baisse de l'indice).
3. **Liste des 5 :** les 5 plus forts bêtas. Le cœur, ce sont les 2 premiers. La liste est figée au S5, et le cœur du NDX exclut le cœur des semis.
4. **Position (cœur permanent, 19/11/2026) :**
   - cycle ouvert (trade S5 en cours ou non) → le cœur de 2 du dernier S5 ;
   - cycle fermé, interrupteur actif ou G3 → cash (« CASH · PIC » pour G3).
5. **Exécution :** à la clôture du jour du signal (ordre au cours de clôture) ; actions entières, arrondies à l'action inférieure.

**Or**

- **Décor, dans les 60 dernières séances :**
  - dollar large au rang ≥ 90 sur 250 séances ;
  - taux réel au rang ≥ 90 ;
  - spéculateurs (CFTC) au rang ≤ 10 sur 3 ans.
- **Amorce, sur 20 séances :** taux réel en baisse, GVZ en baisse, GDX meilleur que le S&P.
- **Sorties :**
  - stop de départ : GDX −10 % tant que GDX n'a pas gagné +10 % ;
  - stop suiveur : or −13 % depuis son plus haut ;
  - règle de cycle : or −15 % et taux réel ou dollar en hausse sur 63 séances.
- **Budget de risque (`budget_or`), d'après les phases de GDX (±10 %) :**
  - 50 % de mines en surchauffe : écart mines / or ≥ +20 % et durée attendue dépassée. La durée attendue d'une hausse vaut 22,6 × (VIX/20)^−0,76 ;
  - 90 % en correction ≤ −17 % ayant dépassé sa durée, qui vaut 17,8 × (VIX/20)^−0,72 ;
  - sinon 70 % ;
  - le reste en PHYS, la part de mines répartie sur les 2 mines du cœur.

**Or · rebond après panique (or-VIX, `or_vix`, 20/11/2026)**

- Déclencheur : le VIX a atteint 30 dans les 20 dernières séances, puis clôture sous 85 % de ce pic.
- Achat à la clôture du déclencheur, seulement si la part or est dehors (K2 ne la bloque pas depuis le 21/11/2026) : cœur de 2 mines figé ce jour-là (`fige_or_vix`), 50 / 50.
- Taille : 15 % du capital au plus, dans la limite or de 25 %, pris sur le cash ; hors W1.
- Sortie : à la 126e séance, ou si GDX clôture 25 % sous son cours d'achat.

**Poche pétrole (hors système)** : carte d'information sous les ordres du jour (accélération du Brent, montant disponible ≤ 25 % et pris sur le cash, règles d'entrée et de sortie). Hors portefeuille modèle.

**Poids du portefeuille**

1. **W1, en fin de mois :** poids = (1 / σ) / Σ(1 / σ). σ est la volatilité annuelle sur 63 séances de ce que la part a détenu (l'indice si investie, cash sinon), avec un plancher de 5 %.
2. **Multiplicateur d'état :**
   - × 1,5 en mini-hausse ;
   - × 0,5 en mini-correction avec un trade S5 ;
   - × 1 en mini-correction sans S5 ;
   - × 0,5 en plus si le recul depuis le plus haut du cycle dépasse la moitié du seuil de cycle.
3. **Limites :** la somme investie est ramenée à 100 % au plus, puis chaque part à 50 % au plus (25 % pour l'or, décision du 19/11/2026). Le reste va en cash.
4. **Break (prioritaire, `etat_break`) :** capital à −30 % de son plus haut → tout couper ; blocage K2 (S&P sous sa moyenne 40 semaines en clôture du vendredi et décor de taux allumé ; levé après 8 vendredis de suite au-dessus, ou 2 si le décor de taux s'est éteint) → aucune part tech nouvelle (SOX, Logiciel, NDX ; l'or et l'or-VIX restent libres, k2_or) ; −35 % → arrêt.

## Calculs de l'application

Une ouverture de page exécute `app.py` de haut en bas. Les calculs lourds sont mis en cache par Streamlit : 6 heures pour les données, 12 jeux de calculs gardés.

| Ordre | Fonction (fichier) | Entrée → sortie |
| --- | --- | --- |
| 1 | `charger` → `tout_charger` (donnees.py) | `MARCHES` → dictionnaire D de séries + sources |
| 2 | `calculer` → `tout_calculer` (calcul.py) | D, séance, mémoire → climat C, états E par marché, or O, statistiques ST, lois LO, verdicts V |
| 2a | `climat` | Taux réel, coût du capital, dollar, VIX et 80e centile, concentration (écart 6 mois, drapeau 60 s.), crédit sur marge |
| 2b | `etat_marche` (un par marché) | Seuils, `zz` (zigzag), `sig7` → `strategie_A`, `sigS5` → `trades_S5`, `sigP4`, mini-phase, carte des prix (`analogues`, `cone`) |
| 2c | `etat_or` + `budget_or` | Décor, amorce, position, niveaux de sortie, budget de mines |
| 2d | `lois_du_jour` | Une carte par loi (niveau, conclusion, source) : lecture seulement |
| 3 | `historique` | Tous les signaux passés (S7, S5, P4) et leur suite à 5, 10, 20 séances |
| 4 | `titres` (titres.py) | Par thème : état (CŒUR, CASH, À L'ABRI, CASH · PIC via `pic_hausse_effacee`), liste, cœur, mesures par titre |
| 5 | `position_regle` (app.py) | Badge de chaque marché = état de la règle, jamais une alerte |
| 6 | `or_titres` | Liste des 5 mines, cœur, budget, répartition mines / PHYS |
| 7 | `portefeuille` | Poids W1 de fin de mois × multiplicateur d'état × limites ; part or-VIX (`or_vix`) ; cash ; poche XLP ; correction généralisée ; dispersion |
| 7a | `modele` (modele.py) | Portefeuille modèle depuis le déploiement : journal `fichiers/journal_modele.csv`, K2 sur les parts tech nouvelles, coupe à −30 % |
| 7b | `ordres_du_jour` (app.py) | Ordres à l'impératif par part, en actions entières ; carte de la poche pétrole |
| 8 | `alertes_decor` → `conclusion_du_jour` | Familles C et D → phrase et tableau de la Conclusion du jour |
| 9 | `series_macro` → `graphique_macro` ; `inst_13f` | Onglet Macro : six panneaux et la carte 13F |
| 10 | `peremptions`, `recalibrages` | Barre latérale : dates limites et recalibrages requis par une sortie de cycle |

**Points délicats à reproduire exactement**

- **Rejouer une séance passée :** chaque série est coupée à la séance (`.loc[:asof]`). Les publications décalées sont respectées (marge, 13F).
- **Date des poids :** c'est la dernière fin de mois avant la séance, sauf si la séance est elle-même le dernier jour ouvré du mois.
- **Mini-phase :** elle est calculée à la clôture et sert à la séance suivante. C'est un état, pas un zigzag recalculé après coup.
- **Titres :** il faut 3 ans de cours avant la date de la liste. En dessous, la thématique est indisponible et la Conclusion du jour aussi : on peut rejouer jusqu'à 2019 avec 10 ans d'historique.

## Interface

L'application a quatre onglets et une barre latérale. Le thème est sombre (`.streamlit/config.toml`), et les cartes, pastilles et jauges viennent de `boussoles/ui.py`.

| Onglet | Blocs, dans l'ordre |
| --- | --- |
| Vue d'ensemble | 0. **Portefeuille modèle** depuis le déploiement (KPI, positions, courbe contre S&P et NDX). 1. **Conclusion du jour** : bandeau du break, revue du vendredi (K2 hebdomadaire et mensuel, alertes de creux, alertes de tension en contexte), ordres du jour à l'impératif (une carte par part, dont or-VIX) et carte de la poche pétrole, puis un tableau par part (cycle, mini-cycle, décision et titres, poids et état, ce qui changerait la décision), puis les pastilles C et D. 2. **Climat du mini-cycle** : VIX et dollar. 3. **Cartes des 6 marchés** : badge selon la règle, sparkline et cône, cycle, mini-cycle, pastilles. 4. **Ce que vaut le système** : simulation et espérance réaliste |
| Marchés | Sélecteur à 6 entrées : semi-conducteurs, logiciel, Nasdaq 100, S&P 500, pétrolières, or et mines. Pour chaque marché : badge, tuiles (cycle, mini-cycle, S5, carte des prix), graphique (cours, VIX, signaux, cône), lecture par les lois, titres de la thématique. Pétrolières : régime d'accélération et Brent. Or et mines : 1. décision (conditions, graphique, sorties) ; 2. titres ; 3. matière première ; 4. repères GDX sans verdict |
| Macro | 6 cartes : interrupteur, VIX, taux réel, crédit sur marge, institutions 13F, concentration. Puis un graphique à panneaux sur un même axe de temps, et un « Comment lire » |
| Interroger l'historique | Choix des marchés, des signaux, des années, d'un VIX minimum et d'un retard sur le S&P → résultats moyens et tableau téléchargeable |

**Barre latérale**

- Bouton « Mettre à jour les données ».
- Séance analysée : rejouer le passé.
- Comparer avec une autre séance : les écarts s'affichent en ⇄.
- Mémoire des statistiques : 4 dernières années ou historique complet.
- Mon capital : plus haut et valeur du jour, pour le break (`fichiers/capital.json`, ou la section [capital] des réglages secrets en ligne).
- Péremption : réglages et fichiers, avec un point 🟢, 🟡 à moins de 30 jours, 🔴 une fois dépassé.
- Sources : en direct ou copie locale.
- Recalibrage requis après une sortie de cycle.

**Règles d'affichage**

- Le badge d'un marché montre la position selon la règle : CŒUR, CASH, À L'ABRI, CASH · PIC, S5 EN COURS, CYCLE FERMÉ, REPÈRE, NON TIMABLE.
- Les lois s'affichent comme une lecture, avec leur couleur. Elles ne changent jamais le badge.

## Recherche : refaire un test

Tout le système sort de 268 scripts de recherche, chacun lié à un protocole écrit avant le calcul. Ils sont livrés avec leurs données dans `recherche_scanoptimus9.zip` (97 Mo, 719 fichiers).

**La chaîne du système final.** Chaque script reprend le précédent : il exécute son début, puis ajoute sa brique.

```text
cycles_tech → entree_base → stop_depart_tech → sortie_cycle_tech → non_retour_tech
→ portefeuille_final (A + interrupteur, S5 2022, stratégie or)
→ defensif → portefeuille_coherent_A → phases_secteurs → sans_defensif (poids W1)
→ concours_poids → pic_distribution (G3) → poids_dynamique → or_phys (budget mines / PHYS)
→ allocation_cycles (état du cycle) → simulation_10k
```

| Étude de contrôle | Script | Ce qu'elle refait |
| --- | --- | --- |
| Espérance et surajustement | `robustesse_futur.py` | Sans les gros coups, bootstrap, Sharpe dégonflé, PBO, décotes |
| Hors échantillon 1995-2015 | `hors_echantillon_1995.py` | Version indices sur 1995-2015 |
| Garde-fous de régime | `garde_fou_baissier.py` | Faber, tendance 12 mois |
| Familles d'indicateurs | `familles_indicateurs.py` | Score d'alertes, G3 conditionnel |
| Pétrole | `petrole_2022.py`, `petrole_acceleration.py` | Cycles 2022-2026, accélération |
| 13F | `analyse_13f.py` | Part tech des gérants actifs |

**Données (`data/`)**

- Entrées brutes :
  - FRED : `cycles.pkl` ;
  - Yahoo : `or.pkl`, `tech.pkl`, `y4_or/yahoo.pkl`, `univers/prix_univers.csv`, `defensif/prix.csv.gz` ;
  - SEC : `compositions/`, `defensif/xlp_*.csv`, `13f/` ;
  - FINRA : `marge/`.
- Résultats intermédiaires : les autres `.pkl`. Ils sont recalculés par leur script.
- Les téléchargements bruts se refont avec les scripts `telecharger_*.py` (dans les sorties, et sur ton ordinateur).
- **Sécurité :** un fichier `.pkl` exécute du code à l'ouverture. N'ouvre que ceux produits par ces scripts.

**Refaire un test (méthode du projet)**

1. Lire le protocole existant dans le projet (`protocole_<sujet>.md`), ou en écrire un avant tout calcul : candidats, fenêtres, critères.
2. Partir du dernier script de la chaîne, en exécutant son début (`exec(open("simulation_10k.py").read().split(...)[0])`), puis ajouter le candidat.
3. Faire concourir le statu quo. On juge sur 2022-2026 (décisif), avec un garde-fou sur l'historique.
4. Écrire le résultat (`<sujet>.md`) et la ligne du journal de décisions. Ne changer `regles.py` qu'en cas d'adoption.

## Reconstruire pas à pas, tester, maintenir

Avec les deux archives, une réinstallation complète prend environ 30 minutes, dont 5 à 10 pour le premier téléchargement des données.

**Installer et lancer**

1. Installer Python 3.10 ou plus récent.
2. Dézipper `boussoles_app.zip`, puis, dans le dossier : `pip install -r requirements.txt` (streamlit, yfinance, pandas, numpy, plotly, requests, openpyxl).
3. `streamlit run app.py` : la page s'ouvre dans le navigateur. Le premier chargement prend plusieurs minutes, le temps de télécharger 10 ans de titres.
4. Pour la mettre en ligne : dépôt GitHub, puis share.streamlit.io, « New app », fichier `app.py`.

**Reconstruire de zéro, sans les archives (ordre conseillé)**

1. `boussoles/regles.py` : recopier les seuils, les réglages, les lois et les péremptions (section Règles et formules).
2. `boussoles/donnees.py` : `yahoo`, `fred`, `cftc_or`, `marge_finra`, `ndx_parts_egales`, `titres_cours`, chacun avec sa copie dans `cache/`.
3. `boussoles/calcul.py` : `zz`, `sig7`, `strategie_A`, `sigS5`, `trades_S5`, `sigP4`, `climat`, `etat_marche`, `etat_or`, `budget_or`, `etat_break`, `or_vix`, `lois_du_jour`, `historique`, `tout_calculer`.
4. `boussoles/titres.py` : `beta_corr`, `selection`, `titres`, `pic_hausse_effacee`, `or_titres`, `fige_or_vix`, `phase_temps_reel`, `portefeuille`, `peremptions`, `recalibrages`.
5. `app.py` : les quatre onglets (section Interface).
6. `fichiers/` : les fichiers de départ, plus `mettre_a_jour.py` et `NOTICE.md`.
7. **Vérifier la reconstruction :** rejouer la séance du 13/11/2026. Elle doit afficher les cœurs MRVL · MU, APP · ORCL et TSLA · AMD, l'or en attente (décor 2/3) et 81 % de cash.

**Tester après chaque modification**

- **Test automatique :** `streamlit.testing.v1.AppTest` sur `app.py`. On ouvre la page, chaque marché du sélecteur, le mode comparaison et quelques séances passées (2024-06-03, 2022-10-03). Il ne doit y avoir aucune exception.
- **Contrôle visuel :** une capture de la vue d'ensemble et de l'onglet Or & mines.
- **Compatibilité :** pas d'antislash ni de guillemets identiques imbriqués dans les f-strings (Python 3.10 et 3.11).

**Maintenir**

| Quand | Quoi |
| --- | --- |
| Chaque mois | `python fichiers/mettre_a_jour.py` (ne fait que le nécessaire) |
| À chaque sortie de cycle | Recalibrage du marché concerné (S5, P4, interrupteur, cœur) sur les 4 dernières années |
| Chaque année | Comparer les trades réels à l'espérance (robustesse\_futur) ; recalibrer si moins de +12 %/an sur 2 ans ou baisse au-delà de −35 % |
| 17/11/2028 | Révision des réglages tech |
| 17/11/2030 | Révision des réglages or |

- Toute règle nouvelle suit la méthode du projet : protocole avant calcul, concours contre le statu quo, ligne au journal de décisions.
- Les copies Markdown de ce dossier sont dans l'application (`DOSSIER_APPLICATION.md`) et dans le projet (`dossier_application.md`).
