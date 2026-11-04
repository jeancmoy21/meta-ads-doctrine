# SCHÉMA CANONIQUE, Manifeste de build Meta (contrat "creation" → "deploy")

Source de vérité unique du format échangé entre l'agent/étape "creation" (producteur) et
l'agent/étape "deploy" (consommateur).

Règles absolues :
- "creation" écrit le manifeste dans `manifests/<batch>.json`, conforme à CE schéma, et le passe à `code/validate_manifest.py` (0 erreur exigé) avant handoff.
- "deploy" revalide avec le même script avant toute exécution. Aucun champ inventé, aucun champ deviné : si une info manque, ARRÊTER et demander.
- Tout `default_status` = `PAUSED` sauf go explicite du propriétaire du compte.

## Deux modes de manifeste

1. **Mode batch** (le plus courant) : ajouter des ads dans un ad set EXISTANT. Champs requis : `adset_id`, `default_status`, `static_ads` et/ou `video_ads`.
2. **Mode complet** : créer campagne + ad sets + ads. Champs requis : `campaign_spec`, `ad_sets`, `static_ads` et/ou `video_ads` (pas de `adset_id` racine; les ads sont dupliquées dans chaque ad set si `ads_placement_note` le dit).

Ordre d'exécution en mode complet : **campaign → ad sets → ads**. Jamais l'inverse.

## Blocs EXÉCUTABLES ("deploy" agit dessus)

| Champ | Type | Requis | Notes |
|---|---|---|---|
| `adset_id` | string | mode batch | ID de l'ad set cible existant |
| `default_status` | string | oui | `PAUSED` par défaut. `ACTIVE` seulement sur go explicite |
| `ad_account_id` | string | mode complet | ex. `act_1234567890` |
| `objective` | string | mode complet | ex. `OUTCOME_SALES`, `OUTCOME_LEADS`, `OUTCOME_TRAFFIC` |
| `optimization_goal` | string | mode complet | ex. `OFFSITE_CONVERSIONS`, `LANDING_PAGE_VIEWS` (jamais `CONVERSIONS`) |
| `billing_event` | string | mode complet | normalement `IMPRESSIONS` |
| `page_id` / `instagram_user_id` / `pixel_id` | string | mode complet | défauts du compte dans `code/meta_lib.py` (variables d'environnement) |
| `campaign_spec` | objet | mode complet | voir table suivante |
| `destination` | objet | mode complet | `link_url` (URL absolue de destination), `display_caption`. Voir « Destination et UTM » ci-dessous |
| `ad_sets` | array | mode complet | voir table suivante |
| `ad_routing` | objet | si placement nominatif | mapping `"__SUFFIXE"` → `name` d'ad set. Voir « Routage des ads vers les ad sets ». Absent = duplication dans chaque ad set |
| `static_ads` | array | oui (peut être `[]`) | voir table suivante |
| `video_ads` | array | oui (peut être `[]`) | voir table suivante |

### `campaign_spec`
| Champ | Type | Requis | Notes |
|---|---|---|---|
| `name` | string | oui | votre propre convention de nommage |
| `objective` | string | oui | idem racine |
| `default_status` | string | oui | `PAUSED` |
| `budget_mode` | string | oui | Valeurs RECONNUES, voir la table « Modes de budget » ci-dessous. Toute autre valeur est REFUSÉE : ne pas inventer |
| `daily_budget_cad` | number | oui | en devise du compte (le déploiement convertit en cents pour l'API) |
| `bid_strategy` | string | oui | ex. `LOWEST_COST_WITHOUT_CAP` |
| `special_ad_categories` | array | oui | `[]` ou `["NONE"]` en liste, jamais une string |
| `schedule` | objet | non | `start_time`, `end_time` ISO-8601 avec fuseau, `note` informative. Sur une campagne adossée à une date d'événement, `end_time` est exigé de fait : sans lui le budget continue de dépenser après l'événement (le validateur AVERTIT) |

### Modes de budget (`campaign_spec.budget_mode`)

Deux modes seulement. Se tromper de mode ne lève AUCUNE erreur API : la structure de budget est simplement autre que celle prévue, et le pilotage prévu par le plan devient impossible.

| Valeur | Où vit le budget | Conséquences pour le déploiement |
|---|---|---|
| `CBO_DAILY_CAMPAIGN_LEVEL` | Campagne. `campaign_spec.daily_budget_cad` est le budget RÉEL | Poser `daily_budget` sur la CAMPAGNE. AUCUN `daily_budget` / `lifetime_budget` sur les ad sets (err API 1885621). Meta redistribue entre ad sets |
| `ABO_DAILY_ADSET_LEVEL` | Chaque ad set. `ad_sets[].daily_budget_cad` est le budget RÉEL | Poser `daily_budget` sur CHAQUE ad set. NE POSER NI `daily_budget` NI `lifetime_budget` sur la campagne, et passer `is_adset_budget_sharing_enabled=false`. `campaign_spec.daily_budget_cad` devient INFORMATIF (somme des ad sets au lancement) et ne doit pas être envoyé à l'API |

Quand choisir ABO : quand le plan impose une trajectoire de budget par palier d'audience (froid vs retargeting), ou quand un ad set doit être bridé à une date fixe. Le CBO ne permet pas de garantir un plancher par ad set.
Si `budget_mode` n'est ni l'une ni l'autre de ces valeurs, ARRÊTER et demander : ne jamais retomber silencieusement sur le CBO, cela casserait toute la structure de budget.

**Appliqué mécaniquement** (liste blanche implémentée dans `code/validate_manifest.py`, `BUDGET_MODES`) : toute autre valeur est une ERREUR bloquante. Corollaires eux aussi bloquants :
- `ABO_DAILY_ADSET_LEVEL` : `daily_budget_cad` est EXIGÉ sur CHAQUE ad set, et doit être un nombre positif. Sans lui, le palier prévu par le plan ne dépense pas.
- `CBO_DAILY_CAMPAIGN_LEVEL` : tout `daily_budget` / `daily_budget_cad` sur un ad set est une ERREUR (err API 1885621).
- En ABO, un écart entre `campaign_spec.daily_budget_cad` et la somme des ad sets déclenche un AVERTISSEMENT (ce champ est informatif en ABO, mais l'écart signale un plan désynchronisé).

### `ad_sets[]`
| Champ | Type | Requis | Notes |
|---|---|---|---|
| `name` | string | oui | |
| `tier` | string | non | informatif (`broad`, `retargeting`...) |
| `default_status` | string | oui | `PAUSED` |
| `optimization_goal` / `billing_event` / `destination_type` | string | oui | |
| `budget_note` | string | non | informatif. Si CBO, pas de budget ici |
| `daily_budget_cad` | number | si ABO | REQUIS en `ABO_DAILY_ADSET_LEVEL` (budget réel de cet ad set). INTERDIT en CBO (err API 1885621) |
| `start_time` / `end_time` | string | non | Bornes temporelles de CET ad set, ISO-8601 avec fuseau. Sert à ouvrir un palier plus tard que la campagne ou à brider un ad set avant la fin. Si absentes, l'ad set suit les bornes de la campagne. Un `start_time` sans `end_time` et sans `end_time` de campagne déclenche un AVERTISSEMENT |
| `promoted_object` | objet | si conversions | `{"custom_conversion_id": "..."}` PRÉFÉRÉ, surtout si votre pixel est partagé entre plusieurs produits/offres : la forme `{"pixel_id": ..., "custom_event_type": ...}` utilise le pixel NU, donc l'événement compte aussi les conversions des autres offres et l'optimisation apprend sur du trafic hors campagne. Le validateur AVERTIT, et BLOQUE si une conversion personnalisée bornée existe dans le manifeste sans être utilisée |
| `activation_date` | string | non | informatif (date de mise en marche prévue du palier) |
| `targeting.geo_locations.regions[].key` | string | oui | Vérifiez la clé exacte via `GET search?type=adgeolocation` avant de déployer : une clé erronée ne lève AUCUNE erreur côté API, le budget part simplement dans la mauvaise région en silence (voir `api/meta-api-errors.md`) |
| `targeting.locales` | array int | oui | Décodez toujours via `GET search?type=adlocale` avant d'utiliser une valeur : les codes numériques ne sont pas intuitifs (ex. `24` = anglais UK) |
| `targeting.age_min` / `age_max` | int | oui | |
| `targeting.custom_audiences` | array string | oui | IDs, peut être `[]` |
| `targeting.excluded_custom_audiences` | array string | oui | Bonne pratique : toujours exclure l'audience de vos inscrits/acheteurs existants de la campagne |
| `targeting.note` | string | non | informatif |

### `static_ads[]`
| Champ | Type | Requis | Notes |
|---|---|---|---|
| `name` | string | oui | unique dans le batch, sert de clé d'idempotence |
| `image_path` | string | oui | chemin ABSOLU vers un VRAI visuel (`.jpg`, `.jpeg`, `.png`), qui existe et pèse au moins 25 Ko. Le validateur BLOQUE tout chemin contenant un jeton placeholder (`PLACEHOLDER`, `TODO_ASSET`, ...), toute extension non-image (un brief `.md` n'est pas un visuel) et tout fichier sous le plancher de taille |
| `utm` | string | oui | PRÉFÉRÉ : URL ABSOLUE complète de destination, UTM inclus, propre à ce créatif (utilisée telle quelle, voir « Destination et UTM »). Un token court seul n'est accepté que sur une destination SANS querystring, et seulement si `META_LINK_BASE` est configuré. `utm_content` unique par créatif |
| `cta` | string | non | défaut configurable via `META_DEFAULT_CTA` |
| `bodies` / `titles` / `descriptions` | arrays | mode pool | POOL : 5-6 bodies, ~5 titres, ~5 descriptions (DEGREES_OF_FREEDOM, `make_static_creative`) |
| `body` / `title` / `description` | strings | mode simple | single-image 1 texte chacun (`make_static_simple`, DOF plante avec 1 seul asset, subcode 2446218) |

Un static est soit en mode pool (`bodies[]`), soit en mode simple (`body`), jamais les deux.

### `video_ads[]`
| Champ | Type | Requis | Notes |
|---|---|---|---|
| `name` | string | oui | unique dans le batch, clé d'idempotence |
| `vert_path` | string | oui | chemin ABSOLU 9:16 (1080x1920) vers un VRAI fichier vidéo (`.mp4`, `.mov`) d'au moins 300 Ko. Mêmes blocages que `image_path` (placeholder, extension, plancher de taille) |
| `sq_path` | string ou null | oui | chemin ABSOLU 1:1 (1080x1080). Si `null` : single-format 9:16, PAS de `make_video_placement_creative` (qui exige la paire), monter un creative single-video standard. Justifier dans `creative_build_note` |
| `format` | string | non | informatif (dimensions, durée) |
| `utm` | string | oui | PRÉFÉRÉ : URL ABSOLUE complète, UTM inclus (voir « Destination et UTM »). `utm_content` unique |
| `cta` | string | non | défaut configurable via `META_DEFAULT_CTA` |
| `body` / `title` / `description` | string | oui | UN SEUL chacun (contrainte API customization placement, err 1885878) |

## Destination et UTM, règle de précédence

`meta_lib.py` ne code aucune URL en dur. `meta_lib.resolve_link(link, utm)` applique cette précédence, et les quatre constructeurs de créatives (`make_static_creative`, `make_static_simple`, `make_static_placement_creative`, `make_video_placement_creative`) acceptent `link=` et `caption=` :

1. `link` fourni et absolu (`http://` / `https://`) : utilisé **TEL QUEL**. Aucune concaténation, aucune réécriture, aucun ajout de séparateur. Un `utm` fourni en plus est ignoré.
2. `link` absent mais `utm` est lui-même une URL absolue : utilisé **TEL QUEL**. C'est la forme recommandée pour tout manifeste récent : chaque ad porte son URL complète, UTM inclus, dans son champ `utm`.
3. Ni l'un ni l'autre absolu : repli sur `META_LINK_BASE` si configuré (`link_base.format(utm=utm)`), sinon `resolve_link` lève une erreur explicite plutôt que de deviner une destination.

Un `link` non absolu lève une `ValueError` : on refuse plutôt que de deviner.

`caption` (le `caption` / `link_caption` / `display_url` affiché sous le créatif) suit la même logique : fourni par `destination.display_caption`, sinon repli `META_DEFAULT_CAPTION`.

**Interdit, cause d'un défaut classique** : une URL de destination qui porte déjà une querystring (ex. `.../paiement/?param=x`) combinée à un champ `utm` séparé sous forme de token. La concaténation naïve produit `?param=xutm_source=...`, ce qui casse le paramètre et envoie le trafic vers la mauvaise destination. Le validateur BLOQUE ce cas.

## Routage des ads vers les ad sets

Deux placements possibles, et il faut en choisir un explicitement :

1. **Duplication** (défaut historique) : les mêmes créatives sont montées dans CHAQUE ad set. Se déclare dans `ads_placement_note`. Rien à valider.
2. **Placement nominatif par suffixe de nom** : chaque ad va dans UN SEUL ad set, désigné par le suffixe de son `name` après un double souligné (ex. `MonBatch-IMG1-MonAngle__FROID-LARGE`).

Le placement nominatif est SUPPORTÉ, à condition de le déclarer dans un champ STRUCTURÉ, pas seulement en prose :

```json
"ad_routing": {
  "__FROID-LARGE": "MaCampagne-Froid-Large",
  "__WARM-RETARGETING": "MaCampagne-Warm-Retargeting"
}
```

Règles, toutes appliquées par le validateur :
- Chaque clé commence par `__`. Chaque valeur doit être le `name` exact d'un ad set du manifeste (sinon ERREUR : l'ad ne serait routée nulle part).
- Chaque ad doit correspondre à exactement une clé par `name.endswith(clé)` (sinon ERREUR).
- **Aucune clé ne peut être le PRÉFIXE d'une autre clé.** `__WARM` et `__WARM-PARTNERX` se chevauchent : c'est une ERREUR bloquante. Toute implémentation qui route par appartenance (`clé in name`) ou par premier match dans l'ordre du mapping envoie les ads `...__WARM-PARTNERX` dans l'ad set de `__WARM`, silencieusement, sans aucune erreur API : mauvais palier, mauvais budget, mauvaise audience. Renommer pour rendre les clés mutuellement exclusives.
- Côté consommateur, le déploiement DOIT appliquer le **match le plus long**, jamais le premier match. La règle de nommage ci-dessus rend la question théorique, la règle de match est la ceinture de sécurité.
- Une clé que plus aucune ad ne porte déclenche un AVERTISSEMENT (ad set déployé sans créatif).
- Si les noms d'ads portent des suffixes `__` alors qu'aucun `ad_routing` n'est déclaré et que le manifeste a plus d'un ad set : AVERTISSEMENT (routage en prose, ni vérifiable ni opposable). Le contrôle de chevauchement de préfixes s'applique quand même, sur les suffixes dérivés des noms.

## Blocs INFORMATIFS (le déploiement les lit, n'agit pas dessus)

`note`, `status`, `doctrine_gate`, `creative_build_note`, `budget_note`, `ads_placement_note`, `global_exclusions_note`, `audiences_resolved`, `redeploy_note`, tout champ `*_note` ou `_comment`.
Exception : `creative_build_note` et `ads_placement_note` peuvent contenir des DIRECTIVES d'exécution (ex. override du caption, duplication des creatives dans chaque ad set). Le déploiement doit les lire et les suivre, mais elles ne remplacent jamais les champs structurés.

## Champs ajoutés en rev. 2026-11

Tous consommés par `code/validate_manifest.py` (sévérités dans la table « Ce que le validateur applique VRAIMENT »).

| Champ | Niveau | Sens |
|---|---|---|
| `cible_cpic` | racine | OBLIGATOIRE. Coût cible par IC (nombre > 0). Base du seuil de kill relatif et de `fenetre_min`. |
| `pack_type` | racine | `neuf` (défaut, 4 à 8 ads), `iteration` ou `prouve`. |
| `message_id`, `asset_id` | ad | Optionnels. Plafonds par asset (3 messages distincts) et par message. |
| `message_statut` | ad | `nouveau` (2 ads max par message) ou `prouve` (3 à 6 itérations). |
| `avatar`, `avatar_statut` | ad set | Optionnels. `avatar_statut` : `neuf` ou `prouve`. |
| `daily_min_spend_target_cad` | ad set | Optionnel. Somme <= 20 % du budget CBO. |
| `exclusions_roles` | racine | `{audience_id: rôle}`. Rôles acceptés en prospection : `registered`, `buyers` (configurable, `META_EXCLUSION_ROLES_ALLOWED`). |
| `conversions_disponibles` | racine | `{"achat": bool, "lead_qualifie": bool}`. |
| `tier` | ad set | `retargeting` ou `remarketing` exempte l'ad set de la règle d'exclusion. |

## Exemple complet valide (mode complet, condensé, entièrement fictif)

```json
{
  "note": "MANIFESTE DE BUILD. Campagne remplissage J-5. CBO 400$/j, 1 ad set, 1 vidéo 9:16 only. Tout PAUSED.",
  "status": "READY_FOR_DEPLOY",
  "doctrine_gate": {
    "piliers_couverts": ["Autorité/Résultat", "Circonstance"],
    "angles_couverts": ["Autorité inattendue", "Circonstance concrète"],
    "angles_morts": "Recours sceptique non couvert (pool d'assets limité).",
    "diversite": "Créatifs uniques de bout en bout, pas de hook-swap.",
    "format_note": "9:16 only = [hors-doctrine / secondaire].",
    "plafonnement": "Événement one-shot, pas de SOP plafonnement prévue."
  },
  "cible_cpic": 40,
  "pack_type": "iteration",
  "exclusions_roles": {"9999999999999": "registered"},
  "conversions_disponibles": {"achat": false, "lead_qualifie": false},
  "ad_account_id": "act_1234567890",
  "objective": "OUTCOME_TRAFFIC",
  "optimization_goal": "LANDING_PAGE_VIEWS",
  "billing_event": "IMPRESSIONS",
  "page_id": "111111111111111",
  "instagram_user_id": "222222222222222",
  "pixel_id": "333333333333333",
  "campaign_spec": {
    "name": "MonEvenement_Remplissage",
    "objective": "OUTCOME_TRAFFIC",
    "default_status": "PAUSED",
    "budget_mode": "CBO_DAILY_CAMPAIGN_LEVEL",
    "daily_budget_cad": 400,
    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    "special_ad_categories": [],
    "schedule": {"start_time": "2026-06-15T06:00:00-04:00", "end_time": "2026-06-20T18:00:00-04:00"}
  },
  "creative_build_note": {
    "format": "Vidéos 9:16 UNIQUEMENT, pas de paire carrée. NE PAS utiliser make_video_placement_creative. Creative single-video standard.",
    "thumbnail": "thumbnail_hash par vidéo via video_thumbnail(path, at_sec=2)."
  },
  "destination": {"link_url": "https://exemple.com/landing", "display_caption": "exemple.com"},
  "ad_sets": [
    {
      "name": "MonEvenement-Broad",
      "tier": "broad",
      "avatar": "exemple-avatar",
      "avatar_statut": "prouve",
      "daily_min_spend_target_cad": 40,
      "default_status": "PAUSED",
      "optimization_goal": "LANDING_PAGE_VIEWS",
      "billing_event": "IMPRESSIONS",
      "destination_type": "WEBSITE",
      "budget_note": "CBO niveau campagne, pas de budget ad set",
      "targeting": {
        "geo_locations": {"regions": [{"key": "REPLACE_ME", "country_code": "CA"}]},
        "age_min": 25, "age_max": 65,
        "custom_audiences": [], "excluded_custom_audiences": ["9999999999999"]
      }
    }
  ],
  "ads_placement_note": "Les mêmes créatives sont montées dans CHAQUE ad set.",
  "video_ads": [
    {
      "name": "MonEvenement_HookA_Autorite",
      "message_id": "msg-autorite",
      "message_statut": "prouve",
      "vert_path": "/abs/path/exemple_hook_a.mp4",
      "sq_path": null,
      "format": "9:16 single (1080x1920, ~50s)",
      "utm": "https://exemple.com/landing?utm_source=facebook&utm_medium=paid-social&utm_campaign=MonEvenement&utm_content=hookA-autorite",
      "cta": "LEARN_MORE",
      "body": "Exemple de corps de texte pour cette ad. Remplacer par votre propre copy.",
      "title": "Exemple de titre accrocheur",
      "description": "Exemple de description courte."
    }
  ],
  "static_ads": []
}
```

## Ce que le validateur applique VRAIMENT (contrat de vérité)

Ce tableau est le contrat de vérité entre ce document et `code/validate_manifest.py`. Un garde-fou documenté mais non implémenté est plus dangereux qu'un garde-fou absent : personne ne revérifie. **Toute règle ajoutée ici sans code correspondant est un bug de ce fichier.** « Requis » dans les tables ci-dessus veut dire *le producteur doit le fournir*; la colonne ci-dessous dit *ce qui arrive s'il ne le fait pas*.

| Règle | Sévérité réelle | Note |
|---|---|---|
| JSON valide, mode batch OU complet | ERREUR | |
| `campaign_spec` : `name`, `objective`, `default_status`, `budget_mode`, `daily_budget_cad`, `bid_strategy` présents | ERREUR | |
| `budget_mode` hors liste blanche | ERREUR | |
| ABO : `daily_budget_cad` sur chaque ad set | ERREUR | |
| CBO : budget sur un ad set | ERREUR | |
| `objective` racine ≠ `campaign_spec.objective` | ERREUR | |
| `optimization_goal` = `CONVERSIONS` (valeur retirée de l'API) | ERREUR | |
| `excluded_custom_audiences` vide ou absent sur un ad set | AVERTISSEMENT | escape `_meta.exclusion_approved` |
| `default_status`/`status` = `ACTIVE` n'importe où | ERREUR | escape `_meta.active_go` |
| asset placeholder, extension non-média, sous le plancher de taille | ERREUR | |
| `utm` token + URL de destination avec querystring | ERREUR | |
| paramètre(s) de mesure listés dans `MESURE_QS_PARAMS` (vide par défaut, à configurer si vous en avez besoin) qui ne sont pas le PREMIER de la querystring, ou présents plus d'une fois | ERREUR | S'applique aux champs `utm` et `link` de chaque ad et à `destination.link_url` |
| deux URL absolues contradictoires (`link` et `utm`) | ERREUR | |
| `utm_content` ou `name` d'ad dupliqué | ERREUR | |
| `ad_routing` : clé préfixe d'une autre, cible inexistante, ad non routée, ad multi-routée | ERREUR | |
| suffixes `__` dérivés des noms d'ads qui se chevauchent par préfixe | ERREUR | |
| `destination` absent ET des ads sans URL absolue | ERREUR, sauf si un journal `.deploy.json` existe (manifeste historique déjà déployé) : AVERTISSEMENT | |
| `promoted_object` sur pixel nu | ERREUR si une conversion personnalisée est mentionnée dans le manifeste, sinon AVERTISSEMENT | escape `_meta.pixel_shared_approved` |
| clé de région sans `country_code` | AVERTISSEMENT | |
| géo resserrée + restriction de langue simultanées | AVERTISSEMENT | escape `_meta.locales_approved` |
| `special_ad_categories` absent / non-liste | AVERTISSEMENT si absent, ERREUR si string | volontaire : `[]` est le défaut sûr |
| `default_status` racine absent | AVERTISSEMENT | |
| racine mode complet : `ad_account_id`, `objective`, `optimization_goal`, `billing_event`, `page_id`, `instagram_user_id`, `pixel_id` absents | AVERTISSEMENT | le déploiement a des défauts de compte dans `meta_lib.py`; bloquer casserait les manifestes en mode batch et les archives |
| ad set : `optimization_goal`, `billing_event`, `destination_type` absents | AVERTISSEMENT | repli sur les valeurs racine |
| ad set : `targeting.locales`, `age_min`, `age_max`, `custom_audiences` absents | AVERTISSEMENT | |
| `campaign_spec.schedule.end_time` absent | AVERTISSEMENT | |
| `start_time` d'ad set sans aucune borne de fin | AVERTISSEMENT | |
| `sq_path: null` (single-format 9:16) | AVERTISSEMENT | |
| pool statique : `titles`/`descriptions` < 3 | ERREUR (< 3), l'idéal de ~5 n'est pas mécanisé | |
| `cible_cpic` absent, non numérique ou <= 0 | ERREUR | rev. 2026-11 |
| `pack_type` hors `neuf`/`iteration`/`prouve` | ERREUR | rev. 2026-11 |
| pack `neuf` hors de 4 à 8 ads | ERREUR | rev. 2026-11, escape `_meta.pack_size_approved` |
| CBO : somme de `daily_min_spend_target_cad` > 20 % du budget (ou valeur négative/non numérique) | ERREUR | rev. 2026-11, escape `_meta.minimums_approved` |
| CBO : plus d'un événement d'optimisation entre les ad sets | ERREUR | rev. 2026-11 |
| `message_id`/`asset_id` non chaîne, `message_statut` hors `nouveau`/`prouve` | ERREUR | rev. 2026-11 |
| plus de 3 `message_id` distincts sur un `asset_id` dans un ad set | ERREUR | rev. 2026-11 |
| plus de 2 ads sur un message `nouveau` ; plus de 6 sur un message `prouve` ; message marqué des deux statuts | ERREUR | rev. 2026-11 |
| plus de 2 avatars `neuf` simultanés | AVERTISSEMENT | rev. 2026-11 |
| exclusion en prospection d'un rôle hors `registered`/`buyers` | ERREUR | rev. 2026-11, escape `_meta.engagement_exclusion_approved` |
| audience exclue en prospection sans rôle dans `exclusions_roles` | AVERTISSEMENT | rev. 2026-11 |
| `conversions_disponibles` vraie alors qu'un ad set optimise sur IC ou lead brut | AVERTISSEMENT | rev. 2026-11, nouvel ad set requis |

Les fichiers `<batch>.deploy.json`, `.deploy-result.json`, `.journal.json` et les caches d'assets ne sont PAS des manifestes : les passer au validateur produit des erreurs attendues et sans signification.

## Journal de déploiement (produit par "deploy", PAS par "creation")

Le déploiement tient `manifests/<batch>.deploy.json` : après CHAQUE étape réussie, il écrit
`{"<ad name>": {"image_hash": ..., "video_ids": [...], "thumb_hashes": [...], "creative_id": ..., "ad_id": ..., "adset_id": ...}}`.
À la reprise après un plantage : recharger ce journal, lister les ads existantes de l'ad set par nom, et SAUTER toute ad du manifeste dont le nom existe déjà. Le nom d'ad est la clé d'idempotence : jamais deux ads du même nom dans le même ad set.
