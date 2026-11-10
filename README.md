# Application privée de test SUP'COM–6NLG

Petite application Flask destinée aux essais réseau et sécurité sur une VM cliente, Skyhigh et une VM serveur. Elle permet de constater ce que le backend reçoit ; elle ne prend aucune décision SWG, ZTNA ou DLP.

## Pages et API

| Route | Usage |
| --- | --- |
| `GET /` | Accueil et état général visible. |
| `GET /portal` | Page ordinaire pour l'accès, le transfert et une éventuelle réécriture d'URL. |
| `GET /admin` | Ressource identifiable pour les futurs essais de contrôle d'accès. |
| `GET /upload` | Formulaires séparés pour fichier et texte. |
| `POST /upload/file` | Confirme la réception et affiche nom, taille et type déclarés du fichier. |
| `POST /upload/text` | Confirme la réception et affiche la longueur du texte, sans le réafficher. |
| `GET /observations` | Montre les données réseau non sensibles effectivement reçues par Flask. |
| `GET /health` | Retourne `{"status":"ok", "request_id":"…"}`. |

La route `/admin` est **accessible sans authentification applicative** dans cette version. Elle ne constitue pas encore une ressource protégée. La politique d'accès Skyhigh sera configurée et testée ultérieurement. Aucun IdP ni Okta n'est intégré à Flask.

## Installation et lancement local

Python 3.10 ou plus récent est recommandé. Depuis le dossier du projet :

### Windows / Windows Server 2025 (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Si l'activation des scripts est désactivée, utilisez directement `.\.venv\Scripts\python.exe` à la place de `python` pour l'installation et le lancement. Ouvrez `http://127.0.0.1:5000/` sur la même machine.

### Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ouvrez `http://127.0.0.1:5000/` sur la même machine.

## Configuration

| Variable | Valeur par défaut | Usage |
| --- | --- | --- |
| `APP_HOST` | `127.0.0.1` | Interface d'écoute du serveur de développement. |
| `APP_PORT` | `5000` | Port du serveur de développement. |
| `TLS_CERT_FILE` | absente | Chemin du certificat TLS pour un **test HTTPS** avec `python app.py`. |
| `TLS_KEY_FILE` | absente | Chemin de la clé privée correspondante. Les deux variables TLS sont obligatoires ensemble. |

Le serveur de développement Flask convient uniquement aux tests locaux. Pour un test HTTPS ponctuel, indiquez les deux fichiers déjà préparés, hors du dépôt :

```powershell
$env:TLS_CERT_FILE = 'C:\chemin\vers\certificat.pem'
$env:TLS_KEY_FILE = 'C:\chemin\vers\cle-privee.key'
python app.py
```

Sous Linux, définissez ces variables avec `export TLS_CERT_FILE=/chemin/...` et `export TLS_KEY_FILE=/chemin/...`. Le navigateur devra faire confiance au certificat de test pour éviter son avertissement.

Il peut y avoir **deux connexions distinctes** : client → Skyhigh, puis Skyhigh → application. Le certificat chargé par Flask dans le mode de test ci-dessus ne concerne que la seconde connexion si elle utilise HTTPS ; il ne configure pas le certificat présenté au client par Skyhigh. Le nom DNS définitif, les certificats et la méthode de raccordement seront fixés avec 6NLG.

## Préparation du déploiement sur la VM

Installez Python, copiez le projet et les dépendances dans un environnement virtuel comme ci-dessus. Pour servir l'application avec un serveur WSGI compatible Windows et Linux, lancez Waitress depuis cet environnement :

```powershell
# Windows Server 2025, après activation de .venv
waitress-serve --listen=0.0.0.0:8080 app:app
```

```bash
# Linux, après activation de .venv
waitress-serve --listen=0.0.0.0:8080 app:app
```

Adaptez l'interface et le port à la configuration réseau validée avec 6NLG et limitez l'accès par le pare-feu de la VM. Ces commandes lancent un processus au premier plan ; elles n'installent aucun service système. Pour une connexion HTTPS Skyhigh → application en déploiement, placez un terminateur TLS adapté à la VM devant Waitress (par exemple IIS sur Windows ou Nginx sur Linux) et configurez le certificat sur ce terminateur. Waitress ne charge pas `TLS_CERT_FILE` et `TLS_KEY_FILE` ; ces variables ne servent qu'au mode de test Flask. Ne placez jamais une clé privée dans le dépôt.

## Observabilité

Chaque réponse porte `X-Request-ID`. L'application reprend un identifiant reçu dans cet en-tête s'il contient 1 à 64 caractères alphanumériques, points, tirets ou soulignés ; sinon elle génère un nouvel identifiant. L'identifiant reçu est une valeur de corrélation, **pas une preuve d'identité**.

Chaque requête produit une ligne JSON dans la sortie du processus : date et heure UTC, identifiant, méthode, chemin, code HTTP, adresse du pair réseau (`network_peer`), puis `Host`, `X-Forwarded-For` et `X-Forwarded-Proto` observés. Ces en-têtes peuvent être fournis par n'importe quel client ; ils ne servent jamais à autoriser un accès. La page `/observations` expose ces mêmes données de transport pour comparer navigateur, Skyhigh et Flask. Les corps des fichiers et textes POST ne sont ni enregistrés dans les journaux ni conservés par l'application. Le fichier reçu est lu pour compter ses octets, puis abandonné ; aucune route ne le sert. Une requête est limitée à 1 Mio et un texte à 10 000 caractères.

Pour les essais DLP futurs, le formulaire propose uniquement la chaîne fictive `CONFIDENTIEL-6NLG-TEST`. N'utilisez pas de données personnelles ou confidentielles réelles.

## Tests locaux

```powershell
python -m pytest -q
```

Les tests automatisés vérifient les pages, `/health`, les deux POST, la limite de taille, l'identifiant de corrélation et l'affichage distinct du pair réseau et des en-têtes déclarés.

## Essais nécessitant Skyhigh et les VM (non réalisés localement)

- Accès via Reverse Proxy ou ZTNA depuis la VM cliente, y compris la réécriture d'URL et le transfert réel des en-têtes.
- Politique d'accès Skyhigh sur `/admin` et éventuelle intégration de l'IdP préparé séparément.
- Décisions DLP/SWG sur l'envoi du fichier et du texte fictif.
- Validation des certificats et des deux connexions TLS selon l'architecture retenue.

Aucun de ces résultats d'intégration ou de sécurité n'est revendiqué par les tests locaux.
