# Boussoles SCANOPTIMUS9 (Streamlit)

## Lancer sur ton ordinateur
1. Installer Python 3.10 ou plus récent.
2. Dans ce dossier : `pip install -r requirements.txt`
3. `streamlit run app.py` : la page s'ouvre dans le navigateur.

- Les cours, taux, dollar, VIX et positions des spéculateurs se téléchargent à l'ouverture, puis sont gardés 6 heures. Le bouton « Mettre à jour les données » force un nouveau téléchargement.
- Si une source ne répond pas, l'application reprend la dernière copie de `cache/` (pastille 🟡).
- **Fichiers qui périment** (compositions, membres du NDX, 13F, crédit sur marge) : tous dans `fichiers/`, mis à jour par `python fichiers/mettre_a_jour.py`. Voir `fichiers/NOTICE.md`.

## Comment lire l'outil
**Règle d'or :** la position vient des règles. Les lois et les alertes éclairent, elles ne décident pas. Si une alerte contredit la règle, la règle gagne.

| Onglet | Ce qu'il dit |
|---|---|
| Vue d'ensemble | Conclusion du jour (position et poids de chaque part, ce qui changerait la décision, alertes du décor), climat du mini-cycle (VIX, dollar), une carte par marché |
| Marchés | Un marché à la fois : badge = position selon la règle ; tuiles cycle, mini-cycle, S5 et carte des prix ; graphique ; lecture par les lois ; titres. « Or & mines » : décision, titres, matière première, repères GDX |
| Macro | Interrupteur, VIX, taux, dollar, crédit sur marge, institutions 13F, concentration, sur un même axe de temps |
| Interroger l'historique | Ce qui s'est passé après chaque signal passé |

**Les familles d'indicateurs** (familles_indicateurs) :
- **A, cycle :** si l'on peut être investi (stratégie A, S7, interrupteur coût du capital).
- **B, mini-cycle :** quand et quoi détenir (S5, couteau, G3 « hausse effacée », poids).
- **C, tension de fin de cycle :** alertes (interrupteur armé, taux réel, crédit sur marge, 13F, concentration, dispersion).
- **D, climat de creux :** alertes (correction généralisée, peur VIX).

## Le système (journal de décisions)
| Brique | Règle |
|---|---|
| Univers | SOX, logiciel (IGV), NDX en titres ; or à part ; pétrole non timable (poche hors système à ton arbitrage) ; S&P 500 affiché, non tradé |
| Position par part | Cycle ouvert → cœur de 2 titres, figé au dernier S5 (cœur permanent, 19/11/2026) ; cycle fermé, interrupteur actif ou hausse effacée (G3) → cash |
| Exécution | À la clôture du jour du signal (ordre au cours de clôture). Les sorties sont des niveaux connus la veille |
| Or | Stratégie décor + amorce. Part de mines = budget de risque (cœur de 2 mines), le reste en PHYS |
| Or · rebond après panique (or-VIX) | VIX ≥ 30 dans les 20 séances puis reflux sous 85 % de son pic → cœur de 2 mines (figé à l'achat), 15 % du capital au plus dans la limite or de 25 %, si la part or est dehors et K2 éteint ; vente à la 126e séance ou si GDX perd 25 % |
| Poche pétrole (hors système) | Ton arbitrage : jusqu'à 25 % du capital si le cash est disponible, seulement avec un catalyseur d'offre durable et l'accélération du Brent allumée ; XOM · CVX · COP, stops COP −8 %, XOM −5,4 %, CVX −5,8 % ; sortie vitesse du Brent sous zéro ou XLE −15 % du plus haut. Compte dans le capital du break, hors portefeuille modèle |
| Poids | W1 en fin de mois (inverse de la volatilité, cash compris, plancher 5 %) × l'état du cycle de la part : cycle porteur × 1,5, couteau pris par un S5 × 0,5, fin de cycle proche × 0,5 ; total investi ≤ 100 %, 50 % au plus par part, 25 % pour l'or tant qu'il n'a pas de trades réels, le reste en cash |
| **Break (il l'emporte sur tout)** | Capital à −30 % de son plus haut → tout couper ; retour au plus tôt 3 mois après, quand le S&P a clôturé deux fins de mois au-dessus de sa moyenne 10 mois. Blocage K2 (S&P sous sa moyenne 40 semaines en clôture du vendredi et décor de taux allumé, depuis le 20/11/2026) → aucune entrée nouvelle, levé après 8 clôtures hebdomadaires de suite au-dessus, ou 2 si le décor de taux s'est éteint. −35 % → arrêt du système (break) |
| Résultat testé | Système actuel (break, or à 25 %, cœur permanent), dans l'échantillon : 04/01/2016 → 13/11/2026 +36,2 %/an, pire baisse −25 % ; 03/01/2022 → 13/11/2026 +42,1 %/an, −19 %. Or-VIX : +0,8 à +1,2 pt/an en plus. Espérance réaliste ≈ +17 %/an, −30 %, si le régime haussier dure ; régime type 2000-2009 ≈ −50 % (hors échantillon 1995-2015, indices, avec le break : +7,1 %/an, −51 %) |

## Barre latérale
- **Séance analysée :** rejoue n'importe quelle séance passée, avec les seules données connues ce jour-là.
- **Comparer avec une autre séance :** affiche les écarts (⇄).
- **Mémoire des statistiques :** les 4 dernières années (par défaut) ou tout l'historique.
- **Mon capital :** plus haut atteint et valeur du jour, pour le break à −30 %. Gardés dans `fichiers/capital.json`, sur ton ordinateur seulement.
- **Péremption :** date limite de chaque réglage et de chaque fichier.

## Organisation du code
| Fichier | Contenu |
|---|---|
| `boussoles/regles.py` | Seuils, lois, péremptions, décisions du trader. On n'y touche qu'après un nouveau test |
| `boussoles/donnees.py` | Téléchargements et copie de secours |
| `boussoles/calcul.py` | Cycles, S7, stratégie A, S5, P4, lois du jour, climat, or |
| `boussoles/titres.py` | Choix des titres, cœur, G3, portefeuille et poids |
| `boussoles/ui.py` | Cartes, jauges, pastilles |
| `fichiers/` | Fichiers à mettre à jour, notice et script de mise à jour |

---
# Annexe · historique des versions

## v7.0 (24/11/2026) — système optimisé
- **Règles changées** (optimisation du 24/11/2026, moteur officiel) : l'interrupteur coût du capital (X5) est retiré (lecture seulement ; K2 inchangé) ; le cœur de chaque thématique tech passe à **un titre** (le premier de la liste des 5 au bêta en correction ; NDX sans doublon avec les semis). L'or garde son cœur de 2 mines.
- Résultat historique (titres) : 2016-2021 rapport 1,81 contre 1,52 ; 2022-2026 3,98 contre 2,75 ; 2016-2026 +44,5 %/an, pire baisse −20 % (contre +36,5 %, −21 %). Indices 1995-2015 (sans X5) : 0,32 contre 0,26.
- Partie test retirée : plus de variantes A/B/C/E/F, plus de tableau de validation prospective ni de copie figée. Le portefeuille modèle suit le système optimisé à partir du 25/11/2026.
- Risque : 3 titres tech au total ; le risque propre à un titre n'est pas couvert par le break.

## v6.18 (24/11/2026)
- Expérience F : le système sans X5 et avec un cœur d'un seul titre par part (le premier de la liste des 5), depuis la clôture du 25/11/2026, hors test C. Optimisation du 24/11/2026, moteur officiel : cœur de 1 seul, titres 2016-2021 1,76 contre 1,52, 2022-2026 3,74 contre 2,75 ; avec sans X5 : 1,81 et 3,98. Plus concentré (3 titres tech au total) : risque propre à un titre plus élevé, non mesurable sur 2016-2026.

## v6.17 (24/11/2026)
- Expérience E dans le journal du portefeuille modèle : le système sans l'interrupteur coût du capital (X5), K2 inchangé, à partir de la clôture du 25/11/2026. Hors test C (qui garde ses 4 variantes et ses dates) ; candidat pour la révision de novembre 2028 (optimisation, 24/11/2026 : titres 2016-2021 1,57 contre 1,52, 2022-2026 2,92 contre 2,75, indices 1995-2015 0,32 contre 0,26, moteur officiel). Les règles de décision ne changent pas.

## v6.16 (22/11/2026)
- Avenant n° 1 au protocole de validation prospective : base 100 des 4 variantes à la clôture du vendredi 20/11/2026 ; seuils de verdict fixés d'avance (timing validé si D − C ≥ +2 pts/an, D − A ≥ +3 pts/an et meilleur Calmar ; échec si D − C ≤ 0 et Calmar D ≤ Calmar C) ; frais inchangés (0,2 % du montant échangé à chaque achat et vente). Prédictions écrites dans `predictions_validation_reelle`.

## v6.15 (22/11/2026)
- Validation prospective (protocole_validation_reelle, figé le 22/11/2026) : le journal du portefeuille modèle suit chaque soir 4 variantes gelées — A poids fixes sur les indices, B timing du système sur les indices, C poids fixes sur les cœurs de titres, D le système. Poids fixes : SOX 17,9 %, logiciel 18,6 %, NDX 17,7 % ; or identique partout. Tableau sous le portefeuille modèle. Verdict principal le 21/11/2028 ; aucune règle ne change d'ici là.
- Chaque ligne du journal porte la version du code (colonne `version`). Bouton « Télécharger la copie figée du journal » : à archiver chaque semaine sur GitHub (en ligne, le journal est recalculé à chaque redémarrage).
- `fichiers/journal_modele.py` affiche la valeur des 4 variantes.

## v6.14 (22/11/2026)
- Nouvelle alerte de tension « Défensives en tête » (revue du vendredi et Conclusion du jour) : NDX à moins de 5 % de son plus haut de 126 séances et XLP qui bat le S&P d'au moins 5 pts sur 21 séances, apparue dans les 21 dernières séances. Depuis 1999 (14 cas), baisse du NDX d'au moins 10 % dans les 3 mois une fois sur deux, contre 15 % en temps normal (defensives_signal). Lecture, pas règle.

## v6.13 (21/11/2026)
- Onglet Or : tableau « Niveaux de GDX et équivalent or » sous le graphique GDX (fin de correction, non-retour, sortie du cycle A, bascule), et l'équivalent or sur les étiquettes du graphique ; graphique du cours de l'or avec ces niveaux convertis en or (même période que le graphique GDX). Or ≈ or du jour × (niveau / GDX)^(1/β), β = sensibilité de GDX à l'or sur 250 séances (≈ 1,44). Lecture, pas une règle.
- Point de non-retour de GDX : la carte cite désormais la statistique des mines (corrections de GDX au-delà de −25 % pendant un cycle de l'or : 0 reprise sur 7, corrections_phases_or) au lieu de celle de la tech (54-78 %).

## v6.12 (21/11/2026)
- K2 ne bloque plus que la tech (SOX, Logiciel, NDX) ; l'or et l'or-VIX restent libres (décision du trader, k2_or). Titres 2016-2026 : rapport 1,56 → 1,70, pire baisse −23 % → −21 % ; les entrées or de 12/2018 et 10/2022 étaient bloquées. Les 10 trades or-VIX que K2 bloquait faisaient +14,8 % en moyenne.
- Or-VIX : on achète au signal. Attendre 1 à 2 semaines fait payer 1,5 à 2 % plus cher et rater 3 à 4 trades ; l'achat en deux fois n'aide pas (or_vix_attente).

## v6.11 (20/11/2026)
- Levée rapide de K2 (décision du trader, k2_levee_taux) : 2 vendredis au-dessus de la moyenne 40 semaines suffisent si le décor de taux est éteint ; 8 tant qu'il est allumé. Titres 2016-2026 : +36,3 %/an au lieu de +34,7 % ; indices 1995-2015 : pire baisse −33 % au lieu de −40 %.

## v6.10 (20/11/2026)
- Revue du vendredi, en tête des ordres du jour (alertes_frequence) : K2 hebdomadaire lu à la dernière clôture du vendredi, K2 mensuel (ancien) affiché pour comparaison jusqu'à la révision de 2028, alertes de creux (correction généralisée, peur du VIX) mises en avant, alertes de tension affichées comme contexte sans pouvoir d'annonce. Les ordres restent quotidiens.

## v6.9 (20/11/2026)
- Blocage K2 hebdomadaire (décision du trader du 20/11/2026, k2_frequence · k2_duree) : clôture du vendredi du S&P sous sa moyenne 40 semaines avec le décor de taux allumé ; levée après 8 clôtures hebdomadaires de suite au-dessus. Indices 1995-2015 : pire baisse −40 % au lieu de −51 % ; coût ≈ −1,6 pt/an sur 2016-2026. La coupe à −30 % garde son retour mensuel (deux fins de mois au-dessus de la moyenne 10 mois).

## v6.8 (20/11/2026)
- Nouvelle part « Or · rebond après panique » (or-VIX, décision du trader du 20/11/2026) : quand le VIX a atteint 30 puis repasse sous 85 % de son pic, achat du cœur de 2 mines (figé au jour de l'achat), 15 % du capital au plus dans la limite or de 25 %, seulement si la part or est dehors et K2 éteint ; vente à la 126e séance ou si GDX perd 25 % depuis l'achat (or_vix · or_vix_risque · or_vix_fraction). Ordre du jour, ligne du tableau, portefeuille modèle.
- Poche pétrole, hors système (arbitrage du trader) : carte sous les ordres du jour. Jusqu'à 25 % du capital si le cash est disponible, seulement avec un catalyseur d'offre durable et l'accélération du Brent allumée ; XOM · CVX · COP ; stops COP −8 %, XOM −5,4 %, CVX −5,8 % ; sortie vitesse du Brent sous zéro ou XLE −15 % du plus haut. Hors portefeuille modèle.
- Passe finale : retrait du choix « Parts que je trade » (pas d'exclusion manuelle : le système décide), de l'état « LISTE DES 5 » (cœur permanent) et du mécanisme de fin de cycle déclarée (DECISIONS_CYCLE).

## v6.7 (19-20/11/2026)
- La fin du cycle SOX déclarée le 16/11 est retirée (20/11) : le système décide seul de la fin des cycles.
- Ordres en actions entières (arrondi à l'action inférieure, le reste en cash), avec le montant ; colonne « Actions · montant » dans le portefeuille modèle.
- Ordres du jour à l'impératif en tête de la Conclusion (ACHETER / VENDRE / REMPLACER / AJUSTER / TENIR / RESTER EN CASH / INTERDIT K2), avec les montants si le capital est saisi. Onglet or : ordres à l'impératif, repères GDX hors des ordres.
- Portefeuille modèle dans la vue d'ensemble : le système appliqué à la lettre depuis le 19/11/2026, comparé au S&P 500 et au Nasdaq 100 (boussoles/modele.py, journal fichiers/journal_modele.csv écrit chaque soir par fichiers/journal_modele.py).
- Graphiques sur téléphone : légende sous le graphique, pas de zoom au doigt, étiquettes de niveaux sur fond.

## v6.6 (19/11/2026)
- Téléphone : barre latérale repliée sur petit écran, tableau des positions défilant, lanceur lancer_telephone.bat (accès depuis le téléphone sur le même Wi-Fi ou par Tailscale).
- Cœur permanent : la liste des 5 n'est plus détenue ; un couteau touché en cycle ouvert garde le cœur (coeur_permanent). Exécution à la clôture du jour du signal (timing_entree).
- « Ce que vaut le système » : espérance et scénario 2000-2009 en premier, résultats avec leurs dates exactes (dossier sectoriel du 19/11).
- Break du trader en tête de la Conclusion du jour : distance du capital aux −30 %, blocage K2, S&P contre sa moyenne (40 semaines depuis v6.9), décor de taux (break, simplification).
- Saisie du capital dans la barre latérale.
- Part or limitée à 25 % (limite_or : coût −2,6 pts/an sur 2016-2026).

## v6.5 (19/11/2026)
- Conclusion du jour en fin de vue d'ensemble, présentation revue : 4 chiffres clés, tableau des positions (statut, titres, poids avec jauge et état du cycle, prochain déclencheur), alertes en étiquettes, légende repliable.
- « Prochain déclencheur » corrigé quand un S5 est en cours alors que le cycle est fermé (couteau → cash).
- Onglet Or & mines : les repères GDX passent juste avant les signaux d'entrée.

## v6.4 (18/11/2026) · dernière passe
- Vitrine : espérance réaliste et résultat hors échantillon affichés à côté de la simulation.
- Historique des titres porté à 10 ans (rejouer une séance jusqu'à 2019 ; avant, la Conclusion du jour est indisponible faute de titres).
- Documentation complète : DOSSIER_APPLICATION.md (reconstruire le système et l'application de A à Z).

## v6.3 (18/11/2026)
- Plafond au poids actif retiré ; limite de prudence de 50 % du capital par part (décision du trader, posée après le test).

## v6.2 (18/11/2026)
- Poids dynamiques (P4) retirés (décision du trader). Ils sont remplacés par l'allocation selon l'état du cycle (allocation_cycles), avec un plafond au poids actif.
- Or : budget mines + PHYS confirmé.
- Onglet Pétrolières : repère « Régime du pétrole · accélération » (petrole_acceleration). Le pétrole reste non timable.

## v6.1 (18/11/2026) · revue de cohérence
- Badge des marchés = position selon la règle (CŒUR, LISTE DES 5, CASH, CASH · PIC, S5 EN COURS, CYCLE FERMÉ, REPÈRE, NON TIMABLE). Il ne reprend plus « la loi la plus sévère ».
- Poids dynamiques (poids_dynamique, P4) : W1 plafonné au poids actif du secteur, × 0,5 si le secteur perd de la vitesse. Une part dehors affiche son poids « si entrée ».
- Or : part de mines = budget de risque, le reste en PHYS (or_phys).
- Vue d'ensemble allégée : la Conclusion du jour remplace « Signaux du jour », le bloc Or et « Portefeuille du jour ». Le climat garde le VIX et le dollar.
- Une seule définition de la concentration (≥ 5 pts dans les 60 dernières séances).
- Textes corrigés : loi de l'interrupteur (volet Fed), doublon retiré, chiffres de l'or et de la vitrine mis à jour, repères GDX sans cycle A.
- Pétrole (petrole_2022) : toujours non timable sur 2022-2026.

## Titres de chaque thématique (v5, 17/11/2026)
- Sous l'analyse de SOX, Logiciel et NDX, l'application affiche :
  - la position en titres : cœur, liste des 5, cash ou à l'abri ;
  - les 5 titres choisis et le cœur ;
  - pour chaque titre : son bêta en correction, sa performance depuis le S5 et sa moyenne 50.
- Fichier à rafraîchir chaque trimestre : `fichiers/compositions_actuelles.csv` (poids de SOXX et IGV). Pour le NDX, les membres sont dans `fichiers/ndx_membres.csv` et le classement se fait par volume en dollars.

## Or en titres et péremption (v5.1, 17/11/2026)
- Onglet « Or · stratégie » : cœur de 2 mines (parmi les 15 plus gros poids de GDX, les 2 au bêta en correction le plus élevé), détenu quand la stratégie or est investie (choix du trader, or_sans_etf).
- Barre latérale « Péremption » : réglages et fichiers, avec 🟢, 🟡 (30 jours) ou 🔴 (expiré), et une alerte en haut de page si une date est dépassée.
- La composition GDX vient de la dernière déclaration SEC (telecharger_y4_or.py).

## Décisions de cycle et recalibrage (v5.3, 17/11/2026)
- `regles.DECISIONS_CYCLE` : une fin de cycle déclarée par le trader force la sortie de la stratégie A ce jour-là, et l'onglet l'affiche (« fermé · décision du trader »). (Retirée le 20/11/2026 ; mécanisme supprimé en v6.8 : le système décide seul de la fin des cycles.)
- Barre latérale : « Recalibrage requis · marché » dès qu'un marché sort de son cycle après `DATE_CALIBRAGE`.

## Portefeuille du jour (v5.5, 18/11/2026 : défensif hors stratégie, poids en fin de mois)
- **Vue d'ensemble, section « Portefeuille du jour » :**
  - pour chaque part : son poids, son état et ce qu'il faut détenir ;
  - la part du capital en défensif (5 plus gros poids de XLP) ;
  - deux alertes : « Correction généralisée · tech » et « Dispersion des secteurs tech ».
- **Calcul des poids :** inverse de la volatilité sur 63 séances de ce que chaque part a détenu (l'indice si investie, XLP sinon).
- **Composition XLP** (déclaration SEC) dans compositions_actuelles.csv. Péremption : 6 mois, comme pour GDX.
- **v5.5 :**
  - une part dehors est en cash ;
  - poids : inverse de la volatilité de chaque part sur 63 séances, cash compris (plancher 5 %), revus à la dernière fin de mois ;
  - XLP n'est plus qu'une poche affichée, hors stratégie.

## Sortie de pic « hausse effacée » (v5.6, 18/11/2026)
- **Règle :** dans les 3 séances qui suivent un plus haut de 10 séances, si la clôture repasse sous la plus basse clôture des 10 séances d'avant, la part passe en « CASH · PIC ».
- **Retour en position :** à une clôture au-dessus du plus haut de 10 séances qui précédait le signal, ou au prochain S5.
- **Source :** pic_distribution.

## Alerte crédit sur marge (v5.7, 18/11/2026)
- **Tuile « Crédit sur marge »** dans la vue d'ensemble, et carte d'alerte sur les marchés tech.
- **Source :** dette sur marge FINRA, téléchargée à chaque lancement. Une copie de secours, `fichiers/margin-statistics.xlsx`, est livrée avec l'application.
- **Délai :** un mois n'est utilisé qu'à partir du 25 du mois suivant.
- **Alerte :** elle s'allume quand la croissance sur 12 mois recule de 20 points ou plus depuis son plus haut de 6 mois, avec le NDX à moins de 5 % de son plus haut d'un an. C'est une lecture, pas une règle (dette_marge).
- **Nouvelle dépendance :** openpyxl (`pip install openpyxl`).

## Matières premières et onglet Macro (v5.8, 18/11/2026)
- **Matières premières :**
  - Mines d'or et Or · stratégie : cours de l'or (GC=F) ;
  - Pétrolières : cours du Brent (BZ=F) ;
  - chaque bloc montre le cours avec ses moyennes 50 et 200, son plus haut et son plus bas d'un an, et le secteur rapporté à la matière première ;
  - choix de la période : 6 mois, 1 an, 3 ans ou 10 ans.
- **Nouvel onglet « Macro » :** un graphique à panneaux sur un même axe de temps, avec les seuils et une légende :
  1. le NDX, avec les zones de l'interrupteur actif et de l'alerte crédit ;
  2. le VIX et son 80e percentile ;
  3. le coût du capital (10 ans et Fed) ;
  4. le taux réel et le dollar ;
  5. le crédit sur marge ;
  6. la concentration.

## Onglet « Or & mines » et alerte 13F (v5.9, 18/11/2026)
- **Un seul onglet pour l'or** (« Mines d'or » disparaît du sélecteur, qui garde 6 entrées) :
  1. décision : stratégie or, six conditions, graphique des signaux, puis les sorties ;
  2. titres : liste des 5 mines et cœur de 2 ;
  3. matière première : cours de l'or et rapport mines / or ;
  4. repères GDX (cycle, mini-cycle, S5, carte des prix) : lecture seule, sans verdict.
- **Onglet Macro :** nouvelle carte « Institutions · 13F » (13f.md). Elle s'allume si la dernière déclaration disponible montre des gérants qui vendent la tech pendant une hausse du NDX, ou une baisse active de 2 points ou plus.
  - Données : `fichiers/institutions_13f.csv` (23 gérants actifs, 2013-2026).
  - Péremption : 92 jours après la dernière publication. Mise à jour : `python fichiers/mettre_a_jour.py 13f` (v6.0).
- Légende du graphique des matières premières placée sous le graphique.

## Un seul dossier pour les mises à jour (v6.0, 18/11/2026)
- Tous les fichiers qui périment sont dans `fichiers/` : `ndx_membres.csv`, `compositions_actuelles.csv` (SOXX, IGV, GDX, XLP), `institutions_13f.csv`, `margin-statistics.xlsx`.
- Une seule commande les met à jour : `python fichiers/mettre_a_jour.py` (seulement ce qui périme ; `tout` pour forcer ; ou une étape : `ndx`, `ishares`, `sec`, `marge`, `13f`). Le 13F est recalculé sur ton ordinateur : plus besoin de m'envoyer les fichiers.
- Notice complète : `fichiers/NOTICE.md` (contenu, source, durée de vie, calendrier, que faire en cas d'erreur).
- Les anciens scripts `telecharger_*.py` ne servent plus pour l'outil (seulement pour refaire des tests historiques).
- **Conclusion du jour** (en tête de la vue d'ensemble) : une phrase et un tableau par part. Le tableau montre le cycle (famille A), le mini-cycle (B), la décision et les titres, le poids, et ce qui changerait la décision. Les alertes de tension de fin de cycle (C) et de climat de creux (D) sont affichées en pastilles. Elles éclairent sans décider (familles_indicateurs).
