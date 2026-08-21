# Erreurs API Meta connues et fixes confirmés

Lecture PRÉ-REQUISE avant tout appel Graph API via l'agent "deploy". Consignez ici toute
nouvelle erreur rencontrée + son fix confirmé.

API version : v19.0+ (testé jusqu'à v21.0).

---

## Erreurs connues et fixes

### #100 4834011 : special_ad_categories invalide
**Cause:** Passer `[]` ou `["NONE"]` (string) au lieu de `['NONE']` (liste Python)
**Fix:** Toujours `'special_ad_categories': ['NONE']` pour campagnes non-régulées

### #100 1815857 : Region invalide
**Cause:** Utiliser la mauvaise clé de région Meta
**Fix:** Vérifiez toujours la clé exacte via l'API avant de déployer :
`GET search?type=adgeolocation&location_types=['region']&q=<votre region>`.
Exemple réel : pour le Québec, la clé correcte est `'535'` avec `country_code: 'CA'`.
La clé `'10'` est **Dubai (AE)** et ne lève AUCUNE erreur : la campagne diffuse
simplement hors de la région visée, en silence. Ne jamais recopier une clé de
région d'un ancien manifeste sans revalider.
```python
'geo_locations': {
    'regions': [{'key': '535', 'country_code': 'CA'}],
    'location_types': ['home', 'recent'],
}
```

### #100 1885621 : Budget sur ad set avec CBO
**Cause:** Spécifier `daily_budget` sur les ad sets quand CBO est activé au niveau campagne
**Fix:** Ne jamais mettre `daily_budget` sur les ad sets si la campagne a CBO. Le budget est sur la campagne uniquement.

### Bid strategy : bid_amount requis
**Cause:** Certaines bid strategies requièrent `bid_amount`
**Fix via curl PATCH:**
```bash
curl -X POST "https://graph.facebook.com/v19.0/{campaign_id}" \
  -d "bid_strategy=LOWEST_COST_WITHOUT_CAP&access_token=TOKEN"
```

### Form encoding vs JSON encoding
**Cause critique:** `requests.post(url, data={...})` encode en form-urlencoded : les arrays/dicts imbriqués ne passent pas correctement
**Fix:** Toujours utiliser `requests.post(url, params={'access_token': TOKEN}, json=data)` : le token dans params, le body en JSON

### object_story_spec doit être un dict
**Cause:** Passer `json.dumps(spec)` au lieu du dict directement quand on utilise `json=` dans requests
**Fix:** Passer le dict directement : requests sérialise tout automatiquement

### instagram_actor_id invalide
**Cause:** Inclure `instagram_actor_id` dans le creative sans permission appropriée
**Fix:** Ne pas inclure du tout. L'ad apparaît sur Instagram automatiquement via la Page.

### CONVERSIONS n'est pas un optimization_goal valide
**Valeur correcte:** `OFFSITE_CONVERSIONS` (pas `CONVERSIONS`)

### destination_type WEBSITE_AND_PHONE_CALL : erreur #2061044
**Cause:** Ad sets existants configurés avec `WEBSITE_AND_PHONE_CALL` : impossible de créer des ads sans numéro de téléphone
**Fix:** PATCH l'ad set pour changer en `WEBSITE` avant de créer les nouvelles ads:
```python
api_patch(adset_id, {'destination_type': 'WEBSITE'})
```
Les ads existantes actives ne sont pas affectées.

### Limite 50 ads par ad set
Les ad sets atteignent la limite de 50 ads (incluant PAUSED/ARCHIVED). Archiver les vieilles PAUSED avant un nouveau batch si proche de la limite.

### Ad creatives immuables
Une fois créé, le copy d'un creative ne peut pas être modifié. Pour corriger le copy:
1. Créer un nouveau creative avec le copy corrigé
2. Mettre les anciennes ads en PAUSE
3. Créer de nouvelles ads avec le nouveau creative

### MCP Meta Ads : validation client incorrecte
Certains MCP/connecteurs tiers pour Meta Ads ont une validation côté client qui
rejette des combinaisons valides (ex: OFFSITE_CONVERSIONS + IMPRESSIONS).
Contourner en utilisant l'API directement via Python/requests ou curl.

---

## Guardrails : état et corrections

- Un compteur de guardrail (ex. `weekly_count`) peut être gonflé par des runs échoués.
- Après un lancement réussi, vérifier que le compteur reflète le vrai nombre d'ads actives.
- Prévoir un override explicite (`--force`) pour contourner les guardrails de jour/cooldown en urgence validée, jamais par défaut.

---

## Video ads : structure creative

```python
'object_story_spec': {
    'page_id': PAGE_ID,
    'video_data': {
        'video_id': video_id,   # obtenu via upload /advideos
        'message': primary_text,
        'title': headline,
        'call_to_action': {
            'type': 'LEARN_MORE',
            'value': {'link': destination_url},
        },
    },
}
```

Upload video: `POST /{AD_ACCOUNT}/advideos` avec multipart `source=<fichier>`

### Upload video > 100 Mo : HTTP 413, utiliser resumable
Simple upload `source=@file` plafonne ~100 Mo (HTTP 413 sur 116-127 Mo). Pour les gros fichiers (ex: verticaux 9:16), utiliser le protocole resumable: phases `start` (file_size) -> `transfer` (upload_session_id + start_offset + video_file_chunk) en boucle -> `finish` (upload_session_id + title). Carrés ~66 Mo passent en simple upload.

### Customization vidéo par placement (vertical 9:16 Reels/Stories + carré 1:1 Feed dans UNE ad) : recette confirmée
Structure qui MARCHE. Erreurs traversées dans l'ordre: link required (2061015) -> thumbnail manquant -> multi-body interdit (1885878) -> default rule manquante (1885923) -> geo rule (2446501). Fixes:
- PAS de `video_data` dans object_story_spec (sinon il écrase silencieusement les videos/rules). object_story_spec = `{page_id, instagram_user_id}` seulement.
- Tout dans `asset_feed_spec`: `videos:[{video_id, thumbnail_hash, adlabels:[{name:'vert'}]}, {...'sq'}]`, `bodies/titles/descriptions` (UN SEUL chacun, multi-body incompatible avec customization placement), `link_urls`, `call_to_action_types`, `call_to_actions:[{type, value:{link, link_caption}}]` (le `call_to_actions[]` règle l'erreur link), `ad_formats:['SINGLE_VIDEO']`.
- **`optimization_type: 'PLACEMENT'`** obligatoire (sinon erreur geo 2446501 car FB lit les règles comme localisation).
- `asset_customization_rules`: règle 1 = spec placements verticaux (fb story/facebook_reels/facebook_reels_overlay, ig story/reels, messenger story) -> video_label vert; règle 2 = `customization_spec: {}` VIDE + `is_default: true` -> video_label sq (capte tout le reste).
- Thumbnails: 1 par vidéo (ffmpeg frame -> upload /adimages -> `thumbnail_hash`). Le champ dans videos[] est `thumbnail_hash`, pas `image_hash`.
- Vérifier après création: GET creative `fields=asset_feed_spec{videos,asset_customization_rules,...}` : si videos/rules reviennent vides, ils ont été droppés (cause: video_data présent ou optimization_type absent).

### Token : system-user never-expire stocké localement
Un token collé à la main (EAA) expire en quelques heures. Recette qui fonctionne
en production : créer un **token system-user** (Business Settings > Utilisateurs
système), scopes `ads_management`/`ads_read`/`business_management`/`pages_manage_ads`,
généré avec durée "Never" (`expires_at: 0`). Stocker ce token dans un fichier local
(chmod 600), et faire lire ce fichier par tous les scripts/agents plutôt que de
coller un token à chaque session.
- Si erreur 190: le token a été révoqué (régénérer dans Business Settings avec les
  mêmes scopes). Ne pas retomber sur un EAA temporaire collé à la main.
- Le login navigateur automatisé pour récupérer un token est généralement bloqué
  par la 2FA (passkey/WebAuthn) : le system-user token contourne complètement ce
  problème.

### Librairie + agents Meta
- **`meta_lib.py`**: librairie testée encodant toutes les recettes (upload image/vidéo + resumable, thumbnails ffmpeg, static flexible creative, vidéo placement-custom, create_ad, verify). Lit le token depuis le fichier configuré. Les scripts importent cette lib, ne réinventent pas les appels.
- **Pipeline en 3 agents** (voir `agents/`): `meta-analyse` (diagnostic Andromeda, aucune écriture) → `meta-creation` (copy + manifeste JSON, point d'approbation) → `meta-deploy` (exécution Graph API via meta_lib, manifeste dans `manifests/`). Flux: analyse → humain décide → création → approbation copy → deploy.

---

## Gestion de cycle de vie : édition de copy, refresh, wind-down

Recettes confirmées en production. Encodées dans `meta_lib.py` (`clone_creative_new_copy`, `swap_ad_creative`, `strip_promo_from_text`, `make_static_simple`). Doctrine stratégique: `doctrines/meta-campaign-lifecycle.md`.

### Éditer la copy d'une ad (créatives immuables) sans tout recréer
Une créative ne se modifie pas, mais on peut faire pointer l'ad vers une NOUVELLE créative clonée:
1. Pull la créative: GET `fields=name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec`.
2. Cloner ces 3 specs, modifier seulement bodies/descriptions.
3. POST `{ACCOUNT}/adcreatives` -> nouveau creative_id.
4. PATCH l'ad: POST `{ad_id}` avec `creative={"creative_id": new_id}`.
Réversible: les anciennes créatives restent intactes (rollback = swap vers l'ancien id).

### 3 champs cassent à la RECRÉATION et doivent être nettoyés
- `object_story_spec.video_data` (ou `link_data`): retirer `image_url` si `image_hash` présent : subcode **1443051** "ObjectStorySpecRedundant".
- `degrees_of_freedom_spec.creative_features_spec`: retirer `standard_enhancements` ET `standard_enhancements_catalog` : déprécié à la création, subcode **3858504**.
- `asset_feed_spec.promotional_metadata`: retirer quand on enlève le promo (wind-down).
(Encodé dans `_clean_recreate_spec`.)

### make_static_creative (DOF) plante avec 1 seul asset par champ
Subcode **2446218** "Not enough creative assets": DEGREES_OF_FREEDOM exige qu'au moins un champ ait >1 asset. FALLBACK static single-image propre = `make_static_simple`: `object_story_spec.link_data` avec `{image_hash, link, caption, message(body), name(title), description, call_to_action:{type}}`, SANS asset_feed_spec.

### Retrait promo au niveau PHRASE
Pour enlever une mention de code promo tissée dans une phrase, retirer la PHRASE/clause entière qui contient le token (ex. regex sur votre code promo), pas juste le mot, sinon fragments cassés. Découper `re.split(r'(?<=[.!?])\s+')`, drop celles avec le token, rejoindre. Une description 100% promo devient vide et doit être droppée. (`strip_promo_from_text`.)

### Dimensions static feed
1080x1350 (ratio 4:5).

### Métrique de vérité = paiement initié, pas achat
Pour les décisions de kill/réactivation en harvest: `offsite_conversion.fb_pixel_initiate_checkout` (pas `..._purchase` qui lag davantage). Kill = high CTR + 0 IC = mauvaise poche sémantique. Backtrack: registre `killed_ads.json` avec IC au kill, réactiver si `IC_actuel - IC_au_kill >= seuil`.

### Kill / backtrack = 2 fonctions canoniques dans meta_lib (ne plus re-coder)
Toujours passer par ces helpers plutôt que de réécrire la logique inline:
- `m.record_kill(registry_path, ad_name, ad_id, ic_at_kill, by)`: pause l'ad (PAUSED) + inscrit au registre. Idempotent, crée le fichier si absent.
- `m.check_backtrack(registry_path, campaign_id, gained_threshold)`: pull l'IC actuel par ad de la campagne, réactive (ACTIVE) toute ad dont `IC_actuel - ic_at_kill >= gained_threshold`, la retire du registre, retourne les réactivées.
- Registre par défaut: `KILL_REGISTRY` (voir `META_KILL_REGISTRY` dans meta_lib.py).
- **Format figé**: `{ ad_name: {"ad_id", "ic_at_kill", "killed_at", "by"} }`. Compat ascendante: vieilles entrées sans `ad_id` re-résolues par nom via `{campaign}/ads`.

---

## Décisions structurelles utiles (retenues d'un compte en production)

- Même creative dans TOUS les ad sets (pas un par pilier) : évite la fréquence fragmentée
- CBO au niveau campagne : pas de budget par ad set
- **Why:** Distribution par pilier = fréquence trop basse par ad set. CBO + même creative partout = apprentissage plus rapide.

### #100 1870227 : Advantage Audience Flag Required (création ad set)
**Cause:** Depuis 2024, tout nouvel ad set exige un choix explicite Advantage+ audience. Créer un ad set sans le flag échoue.
**Fix:** Ajouter dans targeting `"targeting_automation": {"advantage_audience": 1}` (broad/Advantage+, laisse l'algo élargir) ou `0` (respecte strictement le ciblage par intérêts/custom audiences). Confirmé en production : intérêts -> 0, broad -> 1.

---

## Audiences personnalisées : recettes confirmées

### Video engagement : le format de règle "moderne" est REFUSÉ (#100 subcode 1870049)
Erreur exacte : `Rule Format Not Available For Video Engagement Audience` / `Please use previous audience
rule format format instead.` Le format `{"inclusions":{"operator":"or","rules":[{"event_sources":[{"type":"video",...}]}]}}`
ne marche PAS pour les audiences d'engagement vidéo.
**Format legacy obligatoire** : `rule` = un TABLEAU plat, `retention_days` en paramètre séparé.
```python
rule = [{"event_name": "video_view_25_percent", "object_id": PAGE_VIDEO_ID},
        {"event_name": "video_view_25_percent", "object_id": AUTRE_PAGE_VIDEO_ID}]
params = {"name": ..., "subtype": "ENGAGEMENT", "retention_days": 365,
          "rule": json.dumps(rule)}
```
Valeurs de `event_name` : `video_view_25_percent`, `video_view_50_percent`, `video_view_75_percent`,
`video_view_95_percent`, `video_view_10s`, `video_view_3s`, `video_view_thruplay`.

### #2654 subcode 1713216 : "video isn't associated with a Page"
**Cause :** utiliser le `video_id` qui se trouve dans `object_story_spec.video_data.video_id` du créatif.
Celui-là est la vidéo du COMPTE PUBLICITAIRE (/advideos), pas ciblable en audience d'engagement.
**Fix :** utiliser le champ `creative.video_id` (vidéo de la Page, créée au moment de la publication de l'ad).
Il y en a UN PAR AD, même si toutes les ads partagent la même vidéo source. Il faut donc lister les ads
de la campagne et mettre TOUS les `creative.video_id` dans la règle, sinon on perd une partie de l'audience.
```
GET /{campaign_id}/ads?fields=id,name,creative{id,video_id,effective_object_story_id,object_story_spec}
```

### #2654 nu "Failed to create custom audience" : c'est la longueur de `description`
Le message est générique et ne dit RIEN sur la cause. Ne pas chercher du côté de la règle.
Bisection confirmée : `description` de 262 caractères = OK, 327 caractères = FAIL.
Une chaîne de 300 `A` passe, une vraie phrase de 327 échoue : la limite pratique est autour de 300.
**Fix :** garder `description` sous ~250 caractères sur `/customaudiences`.
Note : `/customconversions` n'a pas ce problème.

### Audience d'exclusion vide (pour la réserver dans un manifeste avant le lancement)
```python
{"name": "...-EXCL", "subtype": "CUSTOM",
 "customer_file_source": "USER_PROVIDED_ONLY", "description": "..."}
```
Pas de `rule`. Elle est immédiatement `delivery_status 200` et référençable en `excluded_custom_audiences`.
Le `approximate_count_lower_bound: 1000` retourné par l'API est un plancher de confidentialité, pas un vrai
compte : ne jamais le lire comme "il y a 1000 personnes dedans".

### Conversions personnalisées : quand le pixel est partagé entre plusieurs offres
```python
rule = {"and": [{"event": {"eq": "InitiateCheckout"}},
                {"or": [{"URL": {"i_contains": "votredomaine.com/paiement"}}]}]}
POST /act_XXXXXXXXXX/customconversions
  {name, event_source_id: PIXEL_ID, custom_event_type, rule: json.dumps(rule), description,
   default_conversion_value}
```
`custom_event_type` valides utilisés : `INITIATED_CHECKOUT`, `LEAD`, `PURCHASE`, `COMPLETE_REGISTRATION`, `OTHER`.
**Pourquoi c'est important si votre pixel sert plusieurs produits :** un `promoted_object` avec le
pixel nu entraîne Meta sur les achats de TOUS les produits qui partagent ce pixel. Toujours passer
par une conversion personnalisée filtrée par URL : `{"custom_conversion_id": ...}`.

---

## Pièges avancés : locales, targeting POST, réutilisation vidéo

### `meta_lib._post` N'INJECTE PAS le token : erreur #100 subcode 33 trompeuse
`_get` ajoute `access_token` tout seul, `_post` NON (les appelants historiques le passent dans `params`).
Un POST sans token retourne : `Unsupported post request. Object with ID '<id>' does not exist, cannot be
loaded due to missing permissions, or does not support this operation` (code 100, **subcode 33**).
Le message pointe vers un problème de permission ou d'objet inexistant : c'est FAUX, l'objet existe et le
GET juste avant fonctionnait. **Fix :** toujours `m._post(path, {..., "access_token": m.token()})`.

### Décoder les locales Meta avant de les utiliser
Vérifiez toujours via `GET search?type=adlocale`. Piège réel rencontré : la locale
`24` est **English (UK)**, pas français, malgré ce qu'on pourrait supposer.
Table utile : `6` English (US), `9` French (France), `24` **English (UK)**, `44`
**French (Canada)**, `1003` French (All). Croiser une géo resserrée avec une
locale mal décodée étrangle la diffusion **sans lever aucune erreur API**.
**Doctrine :** soit une géo large + les variantes de langue correspondantes dans
`locales`, soit une géo resserrée avec AUCUNE restriction de langue. Sur une
cible géo resserrée, ne pas mettre `locales` du tout.

### Un POST `targeting` REMPLACE l'objet complet
Renvoyer geo_locations, age_min/max, custom_audiences, excluded_custom_audiences, targeting_automation et
targeting_relaxation_types en entier, sinon ils sont perdus en silence. Le GET retourne les audiences en
`{id, name}` : les renormaliser en `[{"id": ...}]` avant le POST. Idem `regions` : `{key, country_code}`.
Le statut de l'ad set n'est pas touché, mais l'`effective_status` repasse `IN_PROCESS` (re-revue de l'edit).

### Réutiliser une vidéo déjà uploadée dans une nouvelle ad
Pas besoin de re-uploader un master : reprendre `creative.object_story_spec.video_data.video_id` ET son
`image_hash` (le thumbnail) depuis une créative existante, et les poser dans une NOUVELLE créative.
Ne PAS recopier `image_url` en même temps que `image_hash` (subcode 1443051).
Attention : ce `video_id` est celui du compte publicitaire, il n'est PAS ciblable en audience d'engagement
vidéo (voir #2654 subcode 1713216 plus haut).

### Aperçu d'une ad
`GET /{ad_id}/previews?ad_format=MOBILE_FEED_STANDARD` (ou `INSTAGRAM_STORY`, etc.) retourne
`data[0].body` = un `<iframe src="...">`. Extraire le `src` et remplacer `&amp;` par `&`. URL temporaire.

---

## Pièges avancés : promoted_object, stop_time, rate limits, Conversions API

### `promoted_object` avec `pixel_id` + `custom_conversion_id` combinés : subcode 1885014 "Promoted Object Invalid"
**Cause :** Passer `{"pixel_id": ..., "custom_conversion_id": ...}` ensemble dans `promoted_object` à la création
d'un ad set. Meta refuse cette combinaison (message générique "invalid combination of parameters").
**Fix :** Ne passer QUE `{"custom_conversion_id": ...}` (forme préférée, déjà documentée dans SCHEMA.md). La
conversion personnalisée porte déjà son propre `pixel_id` côté Meta (`event_source_id` à la création), inutile
et casse la création si on le répète dans le `promoted_object` de l'ad set.

### Campaign-level `stop_time` : silencieusement ignoré sur une campagne CBO (daily_budget)
**Symptôme :** `POST {campaign_id} {"stop_time": "2026-08-29T08:30:00-04:00"}` retourne `{"success": true}`
(et `updated_time` avance), mais un GET immédiat ou différé sur `fields=stop_time` ne retourne JAMAIS le champ
(il est absent, pas juste vide). Testé avec offset ISO avec et sans les deux-points, et en epoch Unix : même
résultat dans les trois cas. Campagne testée : `daily_budget` posé (CBO), `bid_strategy
LOWEST_COST_WITHOUT_CAP`, `objective OUTCOME_LEADS`, aucun ad set encore rattaché au moment du premier essai.
**Fix confirmé :** poser `end_time` (pas `stop_time`) sur CHAQUE AD SET individuellement plutôt que sur la
campagne. `POST {adset_id} {"end_time": "2026-08-29T08:30:00-0400"}` persiste correctement et se relit tel
quel (converti dans le fuseau du compte). **Conséquence pratique pour le déploiement :** quand
`campaign_spec.schedule.end_time` est fourni dans un manifeste, NE PAS compter sur le `stop_time` de la
campagne pour l'auto-stop. Répliquer la même valeur en `end_time` sur chacun des ad sets créés. À vérifier
post-deploy par un GET `fields=end_time` sur chaque ad set (pas sur la campagne).

### Rate limit `code 17 / subcode 2446079` "User request limit reached" sur rafales de création
**Cause :** Créer ~10 ad sets + uploader/créer ~20 creatives + ads en boucle serrée tape le rate limit de
l'ad account (pas le rate limit de l'app). Le message est clair (pas besoin de deviner), mais des retries
courts (5-15s) ne suffisent pas toujours à le lever : blocages observés qui nécessitent plusieurs dizaines
de secondes, parfois plus d'une minute, avant que les appels repassent.
**Fix :** wrapper `_get`/`_post` d'un retry à backoff progressif (ex. 20s, 40s, 60s... jusqu'à 8-10 tentatives)
sur cette signature d'erreur précise (`error_subcode 2446079` ou message "User request limit reached"), et
espacer les appels de création en boucle (quelques secondes entre chaque `create_ad`/upload). Si une boucle de
vérification post-deploy tape le même mur, ne PAS multiplier les appels un par un : batcher les lectures via
`{campaign_id}/adsets?fields=...` et `{campaign_id}/ads?fields=...` (2 appels au lieu de N), et le endpoint
`/?ids=id1,id2,...&fields=...` pour lire plusieurs creatives en un seul appel. Réduit une vérification de ~30
appels à 3-4.

### Conversions API `POST /{pixel_id}/events` : encodage, test_event_code, et onglet Test Events
**Contexte :** trois apprentissages confirmés en production sur une implantation CAPI leads.
**1. Encodage :** le body doit être du JSON réel (`Content-Type: application/json`), jamais form-urlencoded : le
tableau `data[]` et l'objet `user_data` sont silencieusement mal parsés sinon. `access_token` accepté en query
param ou dans le JSON. `test_event_code` va au NIVEAU RACINE du payload, pas dans `data[]`.
**2. Déduplication :** même `event_id` + même `event_name` des deux côtés (pixel + CAPI), fenêtre 48h. Un
event_id déterministe construit à partir d'un préfixe fixe + sha256(email normalisé) fonctionne bien.
Attention : si le pixel fire SANS eventID explicite, le plugin auto-setup Meta génère un id auto-généré qui
ne matchera jamais un id serveur calculé : le event CAPI serait alors COMPTÉ EN DOUBLE. Toujours vérifier par
capture réseau (`facebook.com/tr`, param `eid`) que le pixel émet bien l'id attendu avant d'activer un flux serveur.
**3. Onglet Test Events du Events Manager NON FIABLE :** des events acceptés (HTTP 200, `events_received:1`,
`test_event_code` valide et confirmé à l'écran) peuvent ne JAMAIS s'afficher dans l'onglet. Ne pas debugger en
boucle là-dessus : valider par (a) capture réseau du pixel, (b) logs serveur avec la réponse Meta, (c) panneaux
« Couverture des événements » et « Déduplication d'événement » du pixel à J+1/J+2.
**4. Gateway serveur tierce (ex. Stape) :** si votre pixel a déjà une Conversions API Gateway qui relaie les
events navigateur en server-side, tout nouveau flux CAPI doit partager l'eventID du pixel pour déduper avec elle aussi.
