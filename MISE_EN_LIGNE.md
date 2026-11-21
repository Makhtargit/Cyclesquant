# Mettre Boussoles en ligne (Streamlit Community Cloud, accès privé)

L'application tourne chez Streamlit et s'ouvre sur le téléphone comme un site. Ton ordinateur ne sert plus qu'une fois par mois, pour les fichiers.

## Une seule fois (environ 20 minutes, plus simple depuis l'ordinateur)
1. **GitHub :** crée un compte sur github.com si tu n'en as pas.
   - Bouton « New repository », nom `boussoles`.
   - Coche **Private**, puis « Create repository ».
2. **Envoyer les fichiers :** sur la page du dépôt, choisis « uploading an existing file ».
   - Décompresse `boussoles_en_ligne.zip` et glisse **tout son contenu** (pas le dossier lui-même) : `app.py`, `boussoles/`, `fichiers/`, `cache/`, `.streamlit/`, `requirements.txt`, `.gitignore`, les `.md`.
   - Remplace ensuite les fichiers de données de `fichiers/` par ceux de ton ordinateur s'ils sont plus récents (`ndx_membres.csv`, `compositions_actuelles.csv`, `institutions_13f.csv`, `margin-statistics.xlsx`). Garde la version du zip de `mettre_a_jour.py` : elle ne contient pas ton e-mail.
   - Vérifie que le dossier `.streamlit` apparaît dans le dépôt (il donne le thème sombre). S'il manque : « Add file » → « Create new file », nom `.streamlit/config.toml`, et colle le contenu du fichier.
   - Clique « Commit changes ».
3. **Streamlit :** va sur share.streamlit.io et connecte-toi avec ton compte GitHub (« Continue with GitHub »). Accepte l'accès aux dépôts privés.
4. **Créer l'application :** choisis « Create app » puis « Deploy a public app from GitHub ».
   - Repository : `boussoles` ; Branch : `main` ; Main file path : `app.py`.
   - Dans « Advanced settings » :
     - Python : **3.12** ;
     - **Secrets**, à coller :
       ```
       [capital]
       plus_haut = 10000
       actuel = 10000
       ```
       (mets tes vrais montants : ce sont les valeurs par défaut du break à −30 %).
   - Clique « Deploy ». Le premier lancement prend 3 à 5 minutes. (Le mot « public » de ce bouton désigne la façon de déployer ; l’accès se restreint à l’étape suivante.)
5. **Rendre l'application privée :** dans l'application, choisis « Share », puis passe la visibilité à **« Only specific people can view this app »** et ajoute ton adresse e-mail. Seuls les comptes invités peuvent alors l'ouvrir.
6. **Téléphone :** ouvre l'adresse de l'application (`https://…streamlit.app`) dans Chrome, connecte-toi, puis menu ⋮ → « Ajouter à l'écran d'accueil ».

## À vérifier dès la première ouverture
- Le badge en haut de page indique combien de sources sont téléchargées en direct.
- **Si Yahoo bloque les serveurs de Streamlit**, le badge reste bas (par exemple « 1/20 sources en direct ») et l'application affiche les cours du dossier `cache/` (ceux du jour où tu l'as envoyé). Dans ce cas, préviens-moi : on passera au petit ordinateur toujours allumé (Raspberry Pi), ou bien tu enverras le cache à jour une fois par semaine.

## Chaque mois (et le soir d'un signal, si Yahoo bloque)
1. Sur l'ordinateur : `python fichiers\mettre_a_jour.py`.
2. Sur github.com, dans le dossier `fichiers/` du dépôt : « Add file » → « Upload files », puis glisse les fichiers mis à jour. Ajoute aussi `cache/` si Yahoo bloque en ligne.
3. L'application en ligne se relance seule avec les nouveaux fichiers.

## Le capital en ligne
- Une saisie dans la barre latérale ne dure que la visite : le serveur ne garde pas les fichiers qu'il écrit.
- Pour changer la valeur par défaut : share.streamlit.io → ton application → « Settings » → « Secrets ».

## Si l'application s'endort
Une application gratuite qu'on n'ouvre pas pendant quelques jours s'endort. À l'ouverture, clique « Yes, get this app back up » : elle redémarre en une minute.

## Le portefeuille modèle et son journal (une seule fois, 5 minutes)
Le bloc « Portefeuille modèle » de la vue d'ensemble suit le système à la lettre depuis le 19/11/2026. Son journal (`fichiers/journal_modele.csv`) s'écrit chaque soir sur les serveurs de GitHub, ce qui fonctionne même ordinateur éteint.
1. Sur la page du dépôt : « Add file » → « Create new file ».
2. Nom du fichier : `.github/workflows/journal.yml` (à la racine du dépôt, pas dans `boussoles_en_ligne`).
3. Colle le contenu du fichier `journal.yml` que je t'ai envoyé, puis « Commit changes ».
4. Dépôt → « Settings » → « Actions » → « General » → tout en bas, « Workflow permissions » : coche **« Read and write permissions »**, puis « Save ».
5. Onglet « Actions » → « Journal du portefeuille modèle » → « Run workflow » pour le premier passage. Ensuite il tourne seul chaque soir de semaine à 22 h 20 (UTC).
6. Chaque passage ajoute la séance du jour ; l'application en ligne se relance avec le nouveau journal. Le vendredi, il renvoie aussi le cache des cours, utile si Yahoo bloque les serveurs de Streamlit.
