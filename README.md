# Doctrine + outillage Meta Ads pour Claude Code

Ce repo regroupe une doctrine de gestion de campagnes Meta Ads (stratégie
créative, cycle de vie de campagne, tracking) et l'outillage Python + agents
Claude Code qui l'opérationnalisent. Il est brand-agnostic : aucune donnée de
compte réelle n'y vit, tout se configure par variables d'environnement.

## Ce qu'il y a dedans

```
doctrines/    doctrine stratégique Meta Ads
  andromeda-strategy.md       comment penser le créatif sous l'algorithme Andromeda
  meta-campaign-lifecycle.md  comment piloter une campagne dans le temps (harvest, kill/backtrack, wind-down)
  meta-tracking-doctrine.md   principes de tracking/attribution fiables (pixel + CAPI)
  email-launch.md             courriel et SMS autour d'un lancement (flows, principes d'envoi)

api/          contrat technique
  meta-api-errors.md          erreurs Graph API connues et fixes confirmés
  SCHEMA.md                   schéma du manifeste de build (contrat creation -> deploy)

code/         librairie + scripts
  meta_lib.py                 librairie Graph API (upload assets, creatives, kill/backtrack...)
  validate_manifest.py        validateur du manifeste de build
  pull_insights.py            snapshot d'insights par ad
  budget_drop.py              exemple de job de baisse de budget planifiée
  evening_kill.py             exemple de re-check autonome (kill/backtrack)
  snooze_swap.py              exemple de countdown en place sur une seule ad
  tests/                      tests des règles de seuil, de fenêtre et de cascade (python3 -m unittest)

agents/       définitions d'agents Claude Code (pipeline analyse -> création -> déploiement)
  meta-analyse.md         diagnostic de performance (saturation, gagnants/perdants), aucune écriture
  meta-creation.md
  meta-deploy.md
  meta-tracking-audit.md  diagnostic du tracking (pixel, CAPI, dédup, EMQ), aucune écriture
```

Historique des révisions : `CHANGELOG.md`.

## Prérequis

- **Claude Code** installé (`npm install -g @anthropic-ai/claude-code` ou voir la doc officielle).
- **Python 3** et le module standard uniquement (aucune dépendance externe : `meta_lib.py` n'utilise que `urllib`/`json`/`re`).
- **ffmpeg** installé si vous comptez générer des thumbnails vidéo (`video_thumbnail`).
- **Un compte publicitaire Meta** avec un accès admin, et idéalement un **token system-user** (voir `api/meta-api-errors.md`, section Token) plutôt qu'un token temporaire collé à la main.

## Installation, étape par étape

### 1. Cloner le repo

```bash
git clone <url-de-ce-repo>
cd <nom-du-repo>
```

### 2. Créer votre token Meta

Dans Business Settings Meta > Utilisateurs système, créez un système-user avec
les scopes `ads_management`, `ads_read`, `business_management`,
`pages_manage_ads`, durée "Never". Générez un token, puis :

```bash
mkdir -p ~/.meta_ads
echo "VOTRE_TOKEN_ICI" > ~/.meta_ads/meta_token
chmod 600 ~/.meta_ads/meta_token
```

### 3. Configurer vos variables d'environnement

Trouvez vos IDs (compte, page, pixel) dans Meta Business Suite / Events
Manager, puis exportez-les (ex. dans votre `.zshrc`/`.bashrc`, ou un fichier
`.env` local que vous chargez avant de travailler) :

```bash
export META_ACCOUNT_ID="act_XXXXXXXXXX"
export META_PAGE_ID="XXXXXXXXXXXXXXX"
export META_IG_USER_ID="XXXXXXXXXXXXXXX"   # optionnel, pour les vidéos/placement custom
export META_PIXEL_ID="XXXXXXXXXXXXXXX"
export META_TOKEN_FILE="$HOME/.meta_ads/meta_token"
```

Vérifiez que ça fonctionne :

```bash
python3 code/meta_lib.py
# doit imprimer: token OK: {'id': '...', 'name': '...'}
```

### 4. Installer les agents dans Claude Code

Copiez les 4 fichiers d'agents dans votre dossier d'agents Claude Code
personnel ou de projet (`~/.claude/agents/` pour un usage global, ou
`.claude/agents/` à la racine d'un projet) :

```bash
mkdir -p ~/.claude/agents
cp agents/*.md ~/.claude/agents/
```

Ouvrez ensuite une session Claude Code dans ce dossier et vérifiez que les
agents apparaissent (tapez `analyse mes campagnes` ou invoquez-les
explicitement).

### 5. Premier run

1. Lisez `doctrines/andromeda-strategy.md` et `doctrines/meta-tracking-doctrine.md`
   en entier (c'est la doctrine que les agents appliquent).
2. Avant de faire confiance à un seul chiffre : demandez à l'agent
   **meta-tracking-audit** un diagnostic de votre tracking (pixel, CAPI, dédup,
   qualité de correspondance). Un coût par résultat n'a de sens que si le
   tracking derrière est fiable.
3. Demandez ensuite à l'agent **meta-analyse** un diagnostic sur une campagne
   existante (il ne fait AUCUNE écriture, c'est l'entrée en matière la plus
   sûre pour valider que votre config fonctionne).
4. Quand vous êtes prêt à builder un batch : préparez un dossier de créas et
   invoquez **meta-creation**. Il produit un manifeste JSON dans
   `manifests/` (créez ce dossier s'il n'existe pas) et le fait valider par
   `code/validate_manifest.py` avant de vous le présenter pour approbation.
5. Une fois le manifeste approuvé : invoquez **meta-deploy** pour l'exécuter
   contre la Graph API. Tout est déployé `PAUSED` par défaut.

## Ce que ce repo n'est PAS

- Ce n'est pas un connecteur no-code : vous (ou Claude, via ces agents) écrivez
  et exécutez des scripts Python contre la Graph API directement.
- La doctrine créative (Andromeda, cycle de vie) est indépendante de votre
  marque : elle s'applique à n'importe quel compte Meta Ads. Les exemples
  concrets (prix, codes promo, noms de campagne) dans les scripts sont des
  placeholders à remplacer par les vôtres.
- Les modes de budget, le tracking et les règles de validation sont des
  points de départ solides, pas des règles universelles : adaptez
  `MESURE_QS_PARAMS`, `MOTS_DESACCENTUES`-style checks (aucun ici par défaut),
  ou les escape hatches `_meta.*` à votre propre contexte.

## Garde-fous

Ne commitez jamais votre token Meta ni vos IDs de compte réels dans ce repo.
Gardez-les dans des variables d'environnement ou un fichier `.env` local
ignoré par git (`.gitignore` fourni bloque `*token*`, `*.env`, `*.log`,
`__pycache__/`, `snapshots/`, `manifests/*.deploy.json`).
