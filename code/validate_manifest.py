#!/usr/bin/env python3
"""Validateur du manifeste de build Meta (contrat "creation" -> "deploy").

Usage: python3 validate_manifest.py manifests/<batch>.json

Vérifie (voir api/SCHEMA.md) :
- JSON valide
- mode batch (adset_id) OU mode complet (campaign_spec + ad_sets)
- chemins d'assets existants (image_path, vert_path, sq_path non-null)
- statics: pool 5-6 bodies OU mode simple (body unique), jamais les deux
- videos: exactement 1 body/title/description (strings non vides)
- utm_content uniques entre tous les ads
- default_status PAUSED (avertissement sinon)
- special_ad_categories = liste (jamais string)

Garde-fous bloquants :
- chemin d'asset placeholder (PLACEHOLDER, TODO_ASSET, ...), extension non-média
  (.md), ou fichier sous le plancher de taille (25 Ko image / 300 Ko vidéo)
- clé de région Meta incohérente avec le pays ciblé (ex. Québec = '535', pas '10'
  qui est Dubai et ne lève AUCUNE erreur API : le budget partirait en silence)
- promoted_object sur un pixel PARTAGÉ entre plusieurs produits/offres +
  custom_event_type brut, alors qu'une conversion personnalisée bornée existe
  dans le manifeste et n'est pas utilisée
- URL de destination avec querystring + champ 'utm' token séparé (concaténation
  cassée '?param=xutm_source=...')
- ordre des paramètres de mesure dans une URL, si vous en dépendez pour vos
  règles de conversion/audience personnalisée (voir MESURE_QS_PARAMS)
- routage des ads vers les ad sets par suffixe de nom ('ad_routing') : clé
  préfixe d'une autre clé, cible inexistante, ad non routée ou multi-routée
  (voir SCHEMA.md, section "Routage des ads vers les ad sets")
- AVERTISSEMENT : campagne sans end_time (borne temporelle)

Le tableau de sévérité réelle de CHAQUE règle vit dans SCHEMA.md, section
"Ce que le validateur applique VRAIMENT". Toute règle ajoutée ici doit y être
reportée, et inversement.

Escape hatches sous _meta (à utiliser consciemment, jamais par défaut) :
region_key_approved, pixel_shared_approved, exclusion_approved, active_go.

Sortie: rapport ERREUR/AVERTISSEMENT. Exit 0 si zéro erreur, 1 sinon.
Les avertissements ne bloquent pas mais doivent être lus.
"""
import json
import os
import re
import sys

# --- Garde-fous assets ---
# Un chemin qui contient un de ces jetons n'est PAS un asset livrable.
PLACEHOLDER_TOKENS = ("PLACEHOLDER", "A_FOURNIR", "TODO_ASSET", "TBD")
IMAGE_EXT = (".jpg", ".jpeg", ".png")
VIDEO_EXT = (".mp4", ".mov")
# Planchers de taille : assez bas pour n'attraper que les aplats vides, icônes
# et fichiers tronqués, jamais un vrai visuel. Ajustez selon vos formats réels.
MIN_IMAGE_BYTES = 25 * 1024
MIN_VIDEO_BYTES = 300 * 1024

# --- Modes de budget (liste blanche) ---
# Se tromper de mode ne lève AUCUNE erreur côté API (la structure de budget est
# simplement autre que celle du plan) : d'où la liste blanche stricte.
BUDGET_MODES = ("CBO_DAILY_CAMPAIGN_LEVEL", "ABO_DAILY_ADSET_LEVEL")

# Paramètres de querystring DONT DÉPEND une règle de mesure (conversion
# personnalisée ou audience pixel en i_contains). Si une de vos règles Meta lit
# un paramètre précis dans l'URL pour distinguer une offre d'une autre, ajoutez-le
# ici : le validateur exige alors qu'il soit TOUJOURS le premier de la querystring
# et qu'il n'apparaisse qu'une fois. Laisser vide si vous n'avez pas ce besoin.
MESURE_QS_PARAMS = ()

CHAMPS_COPY = ("body", "title", "description", "bodies", "titles", "descriptions",
               "message", "primary_text", "headline")

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def check_path(path, where, required=True, kind=None):
    """Vérifie qu'un chemin d'asset pointe vers un VRAI visuel livrable.
    kind: 'image' | 'video' | None. Bloque : jeton placeholder, extension non
    média, fichier sous le plancher de taille. Un brief .md n'est pas un visuel."""
    if path is None:
        if required:
            err(f"{where}: chemin manquant")
        return
    if not isinstance(path, str) or not path.strip():
        err(f"{where}: chemin vide ou invalide")
        return
    if not os.path.isabs(os.path.expanduser(path)):
        err(f"{where}: le chemin doit être absolu ({path})")
        return
    up = path.upper()
    for tok in PLACEHOLDER_TOKENS:
        if tok in up:
            err(f"{where}: chemin PLACEHOLDER ('{tok}') = aucun visuel livré. "
                f"Un déploiement sur ce manifeste monterait des ads sans créatif. "
                f"Fournir le vrai visuel, remplacer le chemin, REVALIDER ({path})")
            return
    full = os.path.expanduser(path)
    if not os.path.exists(full):
        err(f"{where}: fichier introuvable ({path})")
        return
    ext = os.path.splitext(full)[1].lower()
    allowed = IMAGE_EXT if kind == "image" else VIDEO_EXT if kind == "video" else IMAGE_EXT + VIDEO_EXT
    if ext not in allowed:
        err(f"{where}: extension '{ext}' n'est pas un asset {kind or 'media'} "
            f"({', '.join(allowed)}). Un brief .md ou .txt n'est pas un visuel ({path})")
        return
    size = os.path.getsize(full)
    floor = MIN_VIDEO_BYTES if ext in VIDEO_EXT else MIN_IMAGE_BYTES
    if size < floor:
        err(f"{where}: fichier de {size} octets, sous le plancher de {floor} "
            f"({floor // 1024} Ko). Un aplat vide ou un fichier tronqué n'est pas "
            f"un visuel ({path})")


def extract_utm_content(utm):
    if not isinstance(utm, str) or not utm.strip():
        return None
    if "utm_content=" in utm:
        frag = utm.split("utm_content=", 1)[1]
        return frag.split("&", 1)[0]
    return utm.strip()


def validate_static(ad, i):
    where = f"static_ads[{i}] ({ad.get('name', 'sans nom')})"
    if not ad.get("name"):
        err(f"{where}: 'name' manquant")
    check_path(ad.get("image_path"), f"{where}.image_path", kind="image")
    if not ad.get("utm"):
        err(f"{where}: 'utm' manquant")
    has_pool = "bodies" in ad
    has_simple = "body" in ad
    if has_pool and has_simple:
        err(f"{where}: 'bodies' (pool) ET 'body' (simple) présents, choisir un mode")
    elif has_pool:
        bodies = ad.get("bodies") or []
        titles = ad.get("titles") or []
        descs = ad.get("descriptions") or []
        if not (5 <= len(bodies) <= 6):
            err(f"{where}: pool de {len(bodies)} bodies, attendu 5-6 (DEGREES_OF_FREEDOM)")
        if len(titles) < 3:
            err(f"{where}: {len(titles)} titres, attendu >= 3 (idéalement 5)")
        if len(descs) < 3:
            err(f"{where}: {len(descs)} descriptions, attendu >= 3 (idéalement 5)")
        for field, lst in (("bodies", bodies), ("titles", titles), ("descriptions", descs)):
            for j, t in enumerate(lst):
                if not isinstance(t, str) or not t.strip():
                    err(f"{where}.{field}[{j}]: texte vide")
    elif has_simple:
        for field in ("body", "title", "description"):
            t = ad.get(field)
            if not isinstance(t, str) or not t.strip():
                err(f"{where}.{field}: texte manquant ou vide (mode simple)")
    else:
        err(f"{where}: ni 'bodies' (pool) ni 'body' (simple)")
    return extract_utm_content(ad.get("utm"))


def validate_video(ad, i):
    where = f"video_ads[{i}] ({ad.get('name', 'sans nom')})"
    if not ad.get("name"):
        err(f"{where}: 'name' manquant")
    check_path(ad.get("vert_path"), f"{where}.vert_path", kind="video")
    sq = ad.get("sq_path", "ABSENT")
    if sq == "ABSENT":
        err(f"{where}: 'sq_path' manquant (mettre null si single-format 9:16 assumé)")
    elif sq is None:
        warn(f"{where}: sq_path null = single-format 9:16. NE PAS utiliser "
             "make_video_placement_creative (exige la paire). Justifier dans creative_build_note.")
    else:
        check_path(sq, f"{where}.sq_path", kind="video")
    if not ad.get("utm"):
        err(f"{where}: 'utm' manquant")
    for field in ("body", "title", "description"):
        t = ad.get(field)
        if not isinstance(t, str) or not t.strip():
            err(f"{where}.{field}: texte manquant ou vide (1 seul {field} requis, contrainte API)")
        elif isinstance(t, list):
            err(f"{where}.{field}: liste interdite pour une vidéo (1 seul texte, err API 1885878)")
    for field in ("bodies", "titles", "descriptions"):
        if field in ad:
            err(f"{where}: champ pluriel '{field}' interdit sur une vidéo (1 seul texte)")
    return extract_utm_content(ad.get("utm"))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    path = os.path.expanduser(sys.argv[1])
    try:
        with open(path) as f:
            m = json.load(f)
    except FileNotFoundError:
        print(f"ERREUR: fichier introuvable: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERREUR: JSON invalide: {e}")
        sys.exit(1)

    statics = m.get("static_ads")
    videos = m.get("video_ads")
    if statics is None and videos is None:
        err("ni 'static_ads' ni 'video_ads' (au moins un des deux, même vide, est requis)")
    statics = statics or []
    videos = videos or []
    if not statics and not videos:
        err("manifeste sans aucun ad (static_ads et video_ads vides)")

    mode_batch = bool(m.get("adset_id"))
    mode_complet = bool(m.get("campaign_spec"))
    if not mode_batch and not mode_complet:
        err("ni 'adset_id' (mode batch) ni 'campaign_spec' (mode complet)")
    if mode_complet:
        cs = m["campaign_spec"]
        for f in ("name", "objective", "default_status", "budget_mode",
                  "daily_budget_cad", "bid_strategy"):
            if f not in cs:
                err(f"campaign_spec.{f} manquant")
        sac = cs.get("special_ad_categories", None)
        if sac is None:
            warn("campaign_spec.special_ad_categories absent : le schéma le déclare "
                 "requis. Poser [] explicitement (ou [\"NONE\"]).")
        elif not isinstance(sac, list):
            err("campaign_spec.special_ad_categories doit être une LISTE "
                "(jamais une string), ex. [] ou [\"NONE\"]")
        if cs.get("default_status", "PAUSED") != "PAUSED":
            warn("campaign_spec.default_status != PAUSED : confirmer que c'est un go explicite")

        # --- Liste blanche budget_mode ---
        bm = cs.get("budget_mode")
        mode_cbo = bm == "CBO_DAILY_CAMPAIGN_LEVEL"
        mode_abo = bm == "ABO_DAILY_ADSET_LEVEL"
        if bm is not None and bm not in BUDGET_MODES:
            err(f"campaign_spec.budget_mode={bm!r} : valeur NON RECONNUE. Seules "
                f"valeurs admises: {', '.join(BUDGET_MODES)}. Se tromper de mode ne "
                "lève AUCUNE erreur côté API : le budget se retrouve au mauvais "
                "niveau et le pilotage prévu par le plan devient impossible.")

        ad_sets = m.get("ad_sets") or []
        if not ad_sets:
            err("mode complet sans 'ad_sets'")
        for i, a in enumerate(ad_sets):
            w = f"ad_sets[{i}] ({a.get('name', 'sans nom')})"
            if not a.get("name"):
                err(f"{w}: 'name' manquant")
            if a.get("default_status", "PAUSED") != "PAUSED":
                warn(f"{w}: default_status != PAUSED")
            for f in ("optimization_goal", "billing_event", "destination_type"):
                if not a.get(f):
                    warn(f"{w}: '{f}' absent (déclaré requis par SCHEMA.md; "
                         "le déploiement retombe sur le défaut racine du manifeste)")
            tgt = a.get("targeting") or {}
            if not tgt:
                err(f"{w}: 'targeting' manquant")
            else:
                for f in ("locales", "age_min", "age_max", "custom_audiences"):
                    if f not in tgt:
                        warn(f"{w}.targeting.{f} absent (déclaré requis par SCHEMA.md)")
            if "excluded_custom_audiences" not in tgt and not (m.get("_meta") or {}).get("exclusion_approved"):
                warn(f"{w}: pas de 'excluded_custom_audiences'. Bonne pratique: "
                     "toujours exclure vos inscrits/acheteurs existants de la "
                     "diffusion. Override conscient: _meta.exclusion_approved=true")

            a_budget = a.get("daily_budget_cad", a.get("daily_budget"))
            if "daily_budget" in a or "daily_budget_cad" in a:
                if mode_cbo:
                    err(f"{w}: budget sur l'ad set avec CBO (interdit, err API 1885621)")
                elif a_budget is not None and (
                        not isinstance(a_budget, (int, float))
                        or isinstance(a_budget, bool) or a_budget <= 0):
                    err(f"{w}.daily_budget_cad={a_budget!r} : doit être un nombre "
                        "positif en dollars.")
            elif mode_abo:
                err(f"{w}: 'daily_budget_cad' MANQUANT alors que "
                    "campaign_spec.budget_mode=ABO_DAILY_ADSET_LEVEL. En ABO le "
                    "budget RÉEL vit sur chaque ad set : sans lui, l'ad set part "
                    "sans budget (ou hérite d'un défaut non voulu) et le palier "
                    "prévu par le plan ne dépense pas. Poser le budget sur CET ad set.")

        if mode_abo and isinstance(cs.get("daily_budget_cad"), (int, float)):
            somme = sum(a.get("daily_budget_cad") or 0 for a in ad_sets
                        if isinstance(a.get("daily_budget_cad"), (int, float)))
            if somme and abs(somme - cs["daily_budget_cad"]) > 0.01:
                warn(f"ABO : campaign_spec.daily_budget_cad={cs['daily_budget_cad']} "
                     f"ne correspond pas à la somme des ad sets ({somme}). Ce champ "
                     "est INFORMATIF en ABO et ne doit pas être envoyé à l'API, mais "
                     "un écart signale souvent un plan de budget désynchronisé.")

    ds = m.get("default_status") or (m.get("campaign_spec") or {}).get("default_status")
    if ds and ds != "PAUSED":
        warn(f"default_status={ds} : confirmer que c'est un go explicite avant de déployer ACTIVE")
    if not ds:
        warn("'default_status' absent du manifeste (déclaré requis par SCHEMA.md). "
             "Poser \"PAUSED\" explicitement plutôt que de dépendre d'un défaut.")

    if mode_complet:
        cs0 = m["campaign_spec"]
        for f in ("ad_account_id", "objective", "optimization_goal", "billing_event"):
            if not m.get(f):
                warn(f"'{f}' absent à la racine (déclaré requis en mode complet par "
                     "SCHEMA.md)")
        for f in ("page_id", "instagram_user_id", "pixel_id"):
            if not m.get(f):
                warn(f"'{f}' absent à la racine : le déploiement retombe sur le "
                     "défaut de compte de meta_lib.py. L'expliciter évite de publier "
                     "sous la mauvaise page.")
        for label, goal in [("racine", m.get("optimization_goal"))] + [
                (f"ad_sets[{i}]", a.get("optimization_goal"))
                for i, a in enumerate(m.get("ad_sets") or [])]:
            if goal == "CONVERSIONS":
                err(f"{label}.optimization_goal='CONVERSIONS' : valeur retirée de "
                    "l'API. Utiliser 'OFFSITE_CONVERSIONS' (SCHEMA.md).")
        if m.get("objective") and cs0.get("objective") \
                and m["objective"] != cs0["objective"]:
            err(f"objective racine ({m['objective']!r}) != "
                f"campaign_spec.objective ({cs0['objective']!r}) : SCHEMA.md exige "
                "'idem racine'. Le déploiement lit campaign_spec, la valeur racine "
                "devient un mensonge documentaire.")

    meta = m.get("_meta") or {}

    # (a) ACTIVE interdit par défaut (déploys PAUSED) : scan récursif.
    if not meta.get("active_go"):
        def scan_active(obj, where):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("default_status", "status") and v == "ACTIVE":
                        err(f"{where}.{k}=ACTIVE : les déploys sont PAUSED par défaut. "
                            "Override conscient: _meta.active_go=true")
                    scan_active(v, f"{where}.{k}")
            elif isinstance(obj, list):
                for idx, v in enumerate(obj):
                    scan_active(v, f"{where}[{idx}]")
        scan_active(m, "manifest")

    ad_sets_all = m.get("ad_sets") or []

    # (b) Clé de région Meta cohérente avec le pays ciblé. Exemple réel : la clé
    # '10' est DUBAI et ne lève AUCUNE erreur côté API si vous vouliez le Québec
    # ('535') : une campagne mal cléée brûle tout son budget dans le mauvais pays,
    # en silence. Adaptez cette règle à VOS régions habituelles si besoin.
    QC_REGION_KEY = "535"
    if not meta.get("region_key_approved"):
        for i, a in enumerate(ad_sets_all):
            w = f"ad_sets[{i}] ({a.get('name', 'sans nom')})"
            geo = ((a.get("targeting") or {}).get("geo_locations") or {})
            for j, r in enumerate(geo.get("regions") or []):
                cc = r.get("country_code")
                if cc is None:
                    warn(f"{w}.targeting.geo_locations.regions[{j}] : pas de "
                         "'country_code'. Préciser le pays : une clé de région "
                         "seule est ambiguë entre pays (vérifier via "
                         "GET search?type=adgeolocation avant de déployer).")

    # (c) Doctrine langue/geo : SOIT une géo large avec les variantes de langue
    # correspondantes dans 'locales', SOIT une géo resserrée avec AUCUNE
    # restriction de langue. Jamais l'un et l'autre à moitié. Piège réel : la
    # locale Meta '24' est l'ANGLAIS UK, pas française malgré ce qu'on pourrait
    # supposer. Toute valeur de 'locales' doit être décodée (GET search?type=
    # adlocale), jamais recopiée d'un manifeste antérieur.
    if not meta.get("locales_approved"):
        for i, a in enumerate(ad_sets_all):
            w = f"ad_sets[{i}] ({a.get('name', 'sans nom')})"
            tgt = a.get("targeting") or {}
            locales = tgt.get("locales") or []
            regions = ((tgt.get("geo_locations") or {}).get("regions") or [])
            if locales and regions:
                warn(f"{w}: géo resserrée (regions) ET restriction de langue "
                     "(locales) en même temps. Vérifier : c'est rarement voulu, "
                     "une géo resserrée n'a normalement besoin d'aucune "
                     "restriction de langue. Override conscient si volontaire: "
                     "_meta.locales_approved=true")

    # (d) promoted_object sur un pixel PARTAGÉ entre plusieurs produits/offres :
    # un custom_event_type brut (INITIATED_CHECKOUT, PURCHASE, ...) compte les
    # événements de TOUS les produits qui partagent ce pixel, donc l'optimisation
    # apprend sur du trafic hors campagne. La forme bornée est une conversion
    # personnalisée (custom_conversion_id) filtrée par URL. ERREUR si une
    # conversion bornée existe dans le manifeste et n'est pas utilisée ;
    # AVERTISSEMENT sinon. Ne s'applique évidemment que si votre pixel est
    # partagé entre plusieurs offres — ignorez cette règle sinon.
    blob = json.dumps(m, ensure_ascii=False)
    cc_dispo = "custom_conversion_id" in blob or "custom_conversion" in blob
    for i, a in enumerate(ad_sets_all):
        w = f"ad_sets[{i}] ({a.get('name', 'sans nom')})"
        po = a.get("promoted_object")
        if not isinstance(po, dict):
            continue
        if po.get("custom_conversion_id"):
            continue
        if po.get("pixel_id") and po.get("custom_event_type"):
            msg = (f"{w}.promoted_object : pixel nu + "
                   f"custom_event_type={po['custom_event_type']!r}. Si ce pixel "
                   "est partagé entre plusieurs produits/offres, cet événement "
                   "compte aussi les conversions des autres offres, et "
                   "l'optimisation apprend sur du trafic hors campagne. Forme "
                   "bornée attendue : conversion personnalisée filtrée par URL "
                   "de destination (custom_conversion_id).")
            if cc_dispo and not meta.get("pixel_shared_approved"):
                err(msg + " Une conversion personnalisée est mentionnée dans ce "
                          "manifeste et n'est pas utilisée. Override conscient: "
                          "_meta.pixel_shared_approved=true")
            else:
                warn(msg + " Si aucune conversion personnalisée n'existe encore et "
                           "que le pixel n'est pas partagé, ignorer cet avertissement.")

    # (e) Collision querystring / utm. Défaut connu: une URL qui porte déjà
    # '?param=x' concaténée naïvement avec un token utm produit
    # '?param=xutm_source=...', ce qui casse le paramètre. Règle de précédence
    # côté code: meta_lib.resolve_link (URL absolue du manifeste = utilisée
    # TELLE QUELLE).
    dest = m.get("destination") or {}
    dest_url = dest.get("link_url")
    if dest_url and not str(dest_url).startswith(("http://", "https://")):
        err("destination.link_url doit être une URL absolue http(s) "
            f"({dest_url!r})")
    if mode_complet and not dest_url:
        orphelines = [ad.get("name", "sans nom") for ad in statics + videos
                      if not (isinstance(ad.get("utm"), str)
                              and ad["utm"].startswith(("http://", "https://")))
                      and not (isinstance(ad.get("link"), str)
                               and ad["link"].startswith(("http://", "https://")))]
        deja_deploye = os.path.exists(
            re.sub(r"\.json$", ".deploy.json", path)) or os.path.exists(
            re.sub(r"\.json$", ".deploy-result.json", path))
        if orphelines and deja_deploye:
            warn(f"'destination' absent et {len(orphelines)} ad(s) sans URL absolue, "
                 "mais un journal .deploy.json existe : manifeste HISTORIQUE déjà "
                 "déployé sous un repli META_LINK_BASE (voir meta_lib.resolve_link). "
                 "Toléré en archive. Tout NOUVEAU manifeste doit porter son URL complète.")
        elif orphelines:
            err("'destination' absent en mode complet et "
                f"{len(orphelines)} ad(s) ne portent pas d'URL absolue "
                f"({', '.join(orphelines[:4])}...) : meta_lib.resolve_link lèvera "
                "une erreur (ou retombera sur META_LINK_BASE si configuré). "
                "Fournir une URL complète par ad ou en 'destination'.")
        else:
            warn("'destination' absent en mode complet (déclaré requis par "
                 "SCHEMA.md). Toléré ici parce que chaque ad porte son URL absolue "
                 "dans 'utm'. Poser destination.display_caption pour le caption.")

    def check_qs_mesure(url, where):
        if not isinstance(url, str) or "?" not in url or not MESURE_QS_PARAMS:
            return
        qs = url.split("?", 1)[1]
        paires = [p for p in qs.split("&") if p]
        noms = [p.split("=", 1)[0] for p in paires]
        for p_mesure in MESURE_QS_PARAMS:
            if p_mesure not in noms:
                continue
            if noms.count(p_mesure) > 1:
                err(f"{where}: le paramètre de mesure '{p_mesure}' apparaît "
                    f"{noms.count(p_mesure)} fois dans {url}. Une seule occurrence, "
                    "sinon la valeur lue par la règle de mesure est indéterminée.")
            if noms[0] != p_mesure:
                err(f"{where}: le paramètre de mesure '{p_mesure}' n'est PAS le "
                    f"premier de la querystring ({url}). Il est précédé de "
                    f"'{noms[0]}'. Toute règle de conversion personnalisée ou "
                    "d'audience pixel écrite comme un i_contains sur la chaîne "
                    f"'.../?{p_mesure}=...' cesse alors de matcher, et la mesure "
                    "devient aveugle sans lever d'erreur. Deux corrections : (1) "
                    f"remettre '{p_mesure}=' en premier dans cette URL ; (2) côté "
                    "Meta, écrire la règle en conditions INDÉPENDANTES plutôt "
                    "qu'en une seule longue chaîne, pour qu'elle survive à l'ordre "
                    "des paramètres.")

    def check_url_utm(ad, where):
        utm = ad.get("utm")
        link = ad.get("link") or ad.get("link_url")
        utm_abs = isinstance(utm, str) and utm.startswith(("http://", "https://"))
        link_abs = isinstance(link, str) and link.startswith(("http://", "https://"))
        if utm_abs:
            check_qs_mesure(utm, where + " (utm)")
        if link_abs:
            check_qs_mesure(link, where + " (link)")
        if link_abs and utm_abs and link.split("?")[0] != utm.split("?")[0]:
            err(f"{where}: deux URL de destination contradictoires ('link' et 'utm' "
                "portent chacune une URL absolue différente). Une seule source: "
                "mettre l'URL complète dans 'utm' OU dans 'link', jamais les deux.")
        if utm_abs:
            if "?" in utm and "utm_source=" not in utm:
                warn(f"{where}: URL avec querystring mais sans utm_source. "
                     "Vérifier que le tracking est bien porté par l'URL.")
            return
        base = link if link_abs else dest_url
        if utm and base and "?" in str(base):
            err(f"{where}: 'utm' est un token ({utm!r}) et l'URL de destination "
                f"contient déjà une querystring ({base}). La concatenation naïve "
                "casse le paramètre et envoie le trafic au mauvais endroit. "
                "Fournir l'URL COMPLÈTE (avec ses utm_*) dans le champ 'utm' de "
                "l'ad, ou une URL de destination SANS querystring.")

    sched = (m.get("campaign_spec") or {}).get("schedule") or {}
    if m.get("campaign_spec"):
        if not sched.get("end_time"):
            warn("campaign_spec.schedule.end_time absent : si cette campagne est "
                 "adossée à une date d'événement, le budget continue de dépenser "
                 "après l'événement sans cette borne. Poser end_time ISO-8601 avec fuseau.")
        if sched.get("end_time") and not sched.get("start_time"):
            warn("campaign_spec.schedule.start_time absent alors que end_time est posé.")
    for i, a in enumerate(ad_sets_all):
        w = f"ad_sets[{i}] ({a.get('name', 'sans nom')})"
        if a.get("start_time") and not a.get("end_time") and not sched.get("end_time"):
            warn(f"{w}: start_time posé sans end_time, et aucune borne de fin au "
                 "niveau campagne.")

    # ============================================================
    # Routage des ads vers les ad sets. Certains manifestes ne dupliquent PAS
    # toutes les créatives dans tous les ad sets : ils routent chaque ad vers UN
    # SEUL ad set par SUFFIXE de nom après '__'. Danger : deux clés de routage
    # dont l'une est le PRÉFIXE de l'autre ('__WARM' et '__WARM-PARTNERX'). Toute
    # implémentation qui teste l'appartenance ou itère le mapping dans l'ordre
    # d'insertion affecte l'ad '..__WARM-PARTNERX' au premier ad set qui matche,
    # donc au mauvais. Aucune erreur API : l'ad part dans le mauvais palier.
    # ============================================================
    def _cle_suffixe(nom):
        if not isinstance(nom, str) or "__" not in nom:
            return None
        return "__" + nom.rsplit("__", 1)[1]

    def _chevauchements(cles):
        out = []
        for a in cles:
            for b in cles:
                if a != b and b.startswith(a):
                    out.append((a, b))
        return out

    noms_ads = [ad.get("name") for ad in statics + videos if ad.get("name")]
    adset_noms = [a.get("name") for a in ad_sets_all if a.get("name")]
    routing = m.get("ad_routing") or meta.get("ad_routing")

    if isinstance(routing, dict) and routing:
        cles = list(routing.keys())
        for cle, cible in routing.items():
            if not str(cle).startswith("__"):
                err(f"ad_routing['{cle}'] : une clé de routage doit commencer par "
                    "'__' (suffixe de nom d'ad). Voir SCHEMA.md, section Routage.")
            if cible not in adset_noms:
                err(f"ad_routing['{cle}'] pointe vers l'ad set {cible!r}, qui "
                    f"n'existe pas dans 'ad_sets' ({', '.join(adset_noms) or 'aucun'}). "
                    "L'ad ne serait routée nulle part.")
        for court, long_ in _chevauchements(cles):
            err(f"ad_routing : la clé {court!r} est un PRÉFIXE STRICT de {long_!r}. "
                "Un routage par suffixe de nom devient ambigu : toute affectation "
                "par appartenance ou par premier match envoie les ads "
                f"'...{long_}' dans l'ad set de {court!r}, silencieusement, sans "
                "aucune erreur API (mauvais palier, mauvais budget, mauvaise "
                "audience). Corriger en renommant l'une des deux clés pour qu'elles "
                "soient mutuellement exclusives (ex. '__WARM-RETARGETING' et "
                "'__WARM-PARTNERX'). Le consommateur DOIT de toute façon appliquer le "
                "match le PLUS LONG (voir SCHEMA.md, section Routage).")
        for nom in noms_ads:
            matches = [c for c in cles if nom.endswith(c)]
            if not matches:
                err(f"ad '{nom}' : aucune clé de 'ad_routing' ne correspond à son "
                    "suffixe. Chaque ad doit être routable vers exactement un ad "
                    "set. Ajouter la clé ou renommer l'ad.")
            elif len(matches) > 1:
                gagnant = max(matches, key=len)
                err(f"ad '{nom}' : {len(matches)} clés de routage correspondent "
                    f"({', '.join(sorted(matches))}). Le match le plus long "
                    f"({gagnant!r}) est le seul correct, mais l'ambiguïté est une "
                    "source d'affectation silencieusement fausse : rendre les clés "
                    "mutuellement exclusives.")
        cles_utilisees = {max([c for c in cles if n.endswith(c)], key=len)
                          for n in noms_ads if any(n.endswith(c) for c in cles)}
        for cle in cles:
            if cle not in cles_utilisees:
                warn(f"ad_routing['{cle}'] : aucune ad ne porte ce suffixe. Ad set "
                     f"{routing[cle]!r} déployé sans créatif.")
    else:
        cles_derivees = sorted({c for c in (_cle_suffixe(n) for n in noms_ads) if c})
        if cles_derivees and len(adset_noms) > 1:
            warn("routage des ads : les noms d'ads portent des suffixes '__' "
                 f"({', '.join(cles_derivees)}) mais le manifeste ne déclare aucun "
                 "'ad_routing' structuré. Le placement nominatif n'existe alors que "
                 "dans 'ads_placement_note', en prose : ni vérifiable, ni opposable. "
                 "Déclarer 'ad_routing' (voir SCHEMA.md, section Routage).")
        for court, long_ in _chevauchements(cles_derivees):
            err(f"routage des ads : le suffixe {court!r} est un PRÉFIXE STRICT de "
                f"{long_!r} dans les noms d'ads. Si le déploiement route par "
                "suffixe (placement nominatif), les ads peuvent être affectées à "
                "l'ad set du préfixe court sans aucune erreur API. Renommer pour "
                "rendre les suffixes mutuellement exclusifs, et déclarer 'ad_routing'.")

    utms = []
    names = []
    for i, ad in enumerate(statics):
        utms.append(validate_static(ad, i))
        names.append(ad.get("name"))
        check_url_utm(ad, f"static_ads[{i}] ({ad.get('name', 'sans nom')})")
    for i, ad in enumerate(videos):
        utms.append(validate_video(ad, i))
        names.append(ad.get("name"))
        check_url_utm(ad, f"video_ads[{i}] ({ad.get('name', 'sans nom')})")

    check_qs_mesure(dest_url, "destination.link_url")

    seen = {}
    for u in utms:
        if u:
            seen[u] = seen.get(u, 0) + 1
    for u, n in seen.items():
        if n > 1:
            err(f"utm_content '{u}' dupliqué ({n} ads) : doit être unique par créatif")
    seen_n = {}
    for n in names:
        if n:
            seen_n[n] = seen_n.get(n, 0) + 1
    for n, c in seen_n.items():
        if c > 1:
            err(f"nom d'ad '{n}' dupliqué ({c} fois) : le nom est la clé d'idempotence")

    for w in warnings:
        print(f"AVERTISSEMENT: {w}")
    for e in errors:
        print(f"ERREUR: {e}")
    total_ads = len(statics) + len(videos)
    if errors:
        print(f"\nINVALIDE: {len(errors)} erreur(s), {len(warnings)} avertissement(s), {total_ads} ad(s).")
        sys.exit(1)
    print(f"\nVALIDE: 0 erreur, {len(warnings)} avertissement(s), {total_ads} ad(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()
