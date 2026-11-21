# Notice — les fichiers de l'outil et leur mise à jour

Tout ce que l'outil lit et qui périme est dans ce dossier `fichiers/`. Le reste (cours, taux, dollar, VIX, positions des spéculateurs) se télécharge seul à chaque ouverture de l'application.

## La méthode en une commande
Depuis le dossier de l'application, sur ton ordinateur :

```
pip install requests pandas yfinance openpyxl
python fichiers/mettre_a_jour.py
```

- Sans argument, le script met à jour seulement ce qui est périmé ou périme dans les 15 jours.
- `python fichiers/mettre_a_jour.py tout` force tout.
- `python fichiers/mettre_a_jour.py ndx` (ou `ishares`, `sec`, `marge`, `13f`) lance une seule étape.
- **Une seule fois :** ouvre `mettre_a_jour.py` et remplace la ligne `CONTACT` par ton nom et ton e-mail. La SEC l'exige pour les étapes `sec` et `13f` ; l'adresse n'est envoyée qu'à elle.
- Chaque étape garde l'ancien fichier (suffixe `.ancien`) et note ce qu'elle a fait dans `journal_mises_a_jour.txt`.
- Une étape qui échoue ne touche pas au fichier en place.
- Ensuite, dans l'application : bouton « Mettre à jour les données ».

La barre latérale de l'application (« Péremption ») montre la date limite de chaque fichier. Le point passe au jaune à moins de 30 jours et au rouge une fois la date dépassée. Le détail de chaque fichier est dans cette notice.

## Les fichiers

| Fichier | Contenu | Utilisé pour | Durée de vie | Étape | Source |
|---|---|---|---|---|---|
| `ndx_membres.csv` | Membres du Nasdaq-100, une liste datée par mise à jour | NDX à parts égales (alerte concentration) ; candidats du cœur NDX | 30 jours | `ndx` | API publique de Nasdaq (liste officielle du jour) |
| `compositions_actuelles.csv` (lignes SOXX, IGV) | Poids de chaque titre dans SOXX et IGV | Les 15 plus gros poids → liste des 5 et cœur (semis, logiciel) ; noms tech du 13F | 92 jours | `ishares` | Fichier « Holdings » du jour sur ishares.com |
| `compositions_actuelles.csv` (lignes GDX, XLP) | 15 plus gros poids de GDX et XLP | Cœur de 2 mines ; poche défensive hors stratégie | 183 jours | `sec` | Déclaration trimestrielle NPORT-P à la SEC (publiée ~60 jours après la fin du trimestre) |
| `institutions_13f.csv` | Part tech des 23 gérants actifs par trimestre, variation active, part des gérants qui allègent | Carte « Institutions · 13F » (onglet Macro) | 92 jours | `13f` | Déclarations 13F à la SEC (publiées 45 jours après la fin du trimestre) |
| `margin-statistics.xlsx` | Dette sur marge mensuelle (FINRA) | Alerte « crédit sur marge » — copie de secours : l'application essaie d'abord FINRA en ligne | 40 jours | `marge` | finra.org, « Margin Statistics » |

### Fichiers de travail (dans `scripts/`, à ne toucher qu'en cas de message)
| Fichier | Rôle | Quand le modifier |
|---|---|---|
| `correspondances_noms.csv` | Relie un nom de la SEC à un ticker Yahoo (GDX, XLP). Colonnes : etf, mot_cle, ticker ; ticker vide = titre sans cours | Quand l'étape `sec` affiche « ATTENTION, gros poids sans ticker » : ajoute une ligne, par exemple `GDX,TOREX,TXG.TO` |
| `noms_tech_13f.txt` | Noms des émetteurs tech reconnus dans les 13F (forme courte) | Jamais en principe : les noms SOXX/IGV du jour s'y ajoutent seuls |

Les déclarations 13F brutes (environ 600 Mo) restent hors de l'application, dans `C:\Users\<toi>\donnees_13f`. Le script n'y télécharge que les nouvelles.

## Calendrier conseillé
| Quand | Quoi |
|---|---|
| Chaque mois (après le 3e vendredi de décembre pour la refonte annuelle du NDX) | `ndx` ; `marge` vers le 25 |
| Mi-février, mi-mai, mi-août, mi-novembre | `13f` et `ishares` |
| Fin février, fin mai, fin août, fin novembre | `sec` (GDX et XLP du trimestre précédent) |
| Le plus simple | `python fichiers/mettre_a_jour.py` une fois par mois : il ne fait que le nécessaire |

## Ce qui périme et n'est pas un fichier
- **Réglages tech** (S5, P4, interrupteur, règle du cœur) : à revoir au plus tard le 17/11/2028.
- **Réglages or** (P4 or, S5 or repère, cœur de 2 mines) : au plus tard le 17/11/2030.
- **À chaque sortie de cycle :** recalibrage du marché concerné, sans attendre la date.

Ces révisions demandent un nouveau test : envoie-moi les données, je refais le calcul.

## Si une étape échoue
| Message | Que faire |
|---|---|
| « Remplace d'abord la ligne CONTACT » | Mets ton nom et ton e-mail dans `mettre_a_jour.py` |
| « liste suspecte » / « lignes lues » | Le site a changé de format ou était indisponible : réessaie plus tard ; sinon envoie-moi le journal |
| `403` ou `429` de la SEC | Trop de requêtes : relance une heure plus tard |
| « gros poids sans ticker » | Ajoute la correspondance dans `scripts/correspondances_noms.csv` |
