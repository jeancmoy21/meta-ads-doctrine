#!/usr/bin/env python3
"""
meta_lib.py, Librairie Meta Marketing API pour la gestion de campagnes.
Encode des recettes confirmées en production pour ne plus jamais re-débugger
les mêmes erreurs Graph API (voir api/meta-api-errors.md).

Configuration : toutes les valeurs de compte se lisent depuis des variables
d'environnement (ou un fichier .env chargé en amont). Rien de hardcodé ici.

Variables attendues :
  META_ACCOUNT_ID      ex. "act_1234567890"
  META_PAGE_ID
  META_IG_USER_ID       (optionnel, requis seulement pour les creatives vidéo/placement)
  META_PIXEL_ID
  META_TOKEN_FILE       chemin vers un fichier contenant le token (chmod 600 recommandé)
                        défaut : ~/.meta_ads/meta_token
  META_LINK_BASE        URL de repli si un ad ne fournit ni 'link' ni 'utm' absolu
                        (voir resolve_link). Laisser vide force une erreur explicite
                        plutôt que de deviner une destination.
  META_DEFAULT_CAPTION  caption/display_url de repli
"""
import json, os, re, subprocess, urllib.request, urllib.parse, uuid, time, datetime

API = "v21.0"
ACCOUNT = os.environ.get("META_ACCOUNT_ID", "act_REPLACE_ME")
PAGE_ID = os.environ.get("META_PAGE_ID", "REPLACE_ME")
IG_USER_ID = os.environ.get("META_IG_USER_ID", "")
PIXEL_ID = os.environ.get("META_PIXEL_ID", "")
TOKEN_FILE = os.path.expanduser(os.environ.get("META_TOKEN_FILE", "~/.meta_ads/meta_token"))

# Repli utilisé UNIQUEMENT si un ad ne fournit ni 'link' ni 'utm' en URL absolue.
# Laisser vide (défaut) : resolve_link lève alors une erreur explicite plutôt que
# de deviner une destination. Ne fixer cette valeur que si vous avez une landing
# page par défaut légitime pour tout le compte.
LINK_BASE = os.environ.get("META_LINK_BASE", "")
DEFAULT_CAPTION = os.environ.get("META_DEFAULT_CAPTION", "")
DEFAULT_CTA = os.environ.get("META_DEFAULT_CTA", "LEARN_MORE")

_ABS_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def resolve_link(link=None, utm=None, link_base=LINK_BASE):
    """Résout l'URL de destination d'un créatif. RÈGLE DE PRÉCÉDENCE (figée) :

    1. `link` est une URL absolue (http:// ou https://) => utilisée TELLE QUELLE.
       Aucune concaténation, aucune réécriture, aucun ajout de séparateur. Si `utm`
       est aussi fourni, il est IGNORÉ : l'URL du manifeste est présumée déjà
       complète (elle porte ses propres utm_*). C'est ce qui empêche le défaut
       connu '...?param=x' + 'utm_source=...' => '?param=xutm_source=...'.
    2. `link` absent/None mais `utm` est lui-même une URL absolue => utilisée
       TELLE QUELLE (permet de mettre l'URL complète directement dans le champ `utm`).
    3. Sinon (`utm` = token court, ex. 'a1-mon-angle') => repli `link_base.format(utm=utm)`
       si `link_base` est configuré, sinon erreur explicite.

    Un `link` non absolu (chemin relatif, chaîne vide) est une erreur : on refuse
    plutôt que de deviner, sinon on déploie du budget sur une URL cassée.
    """
    if link is not None and str(link).strip():
        link = str(link).strip()
        if not _ABS_URL_RE.match(link):
            raise ValueError(
                f"resolve_link: 'link' doit être une URL absolue http(s), reçu {link!r}. "
                "Corriger le manifeste (destination.link_url), ne pas deviner.")
        return link
    if utm is not None and _ABS_URL_RE.match(str(utm).strip()):
        return str(utm).strip()
    if not utm:
        raise ValueError("resolve_link: ni 'link' ni 'utm' fournis, impossible de "
                         "construire une destination.")
    if not link_base:
        raise ValueError(f"resolve_link: 'utm'={utm!r} est un token court et aucun "
                         "META_LINK_BASE n'est configuré. Fournir une URL absolue "
                         "dans 'link' ou 'utm', ou configurer META_LINK_BASE.")
    return link_base.format(utm=utm)


def resolve_caption(caption=None):
    """Caption/display_url affiché sous le créatif. Fourni par le manifeste
    (destination.display_caption) sinon repli DEFAULT_CAPTION."""
    if caption is not None and str(caption).strip():
        return str(caption).strip()
    return DEFAULT_CAPTION

SIMPLE_UPLOAD_MAX = 95 * 1024 * 1024  # > ~100Mo => HTTP 413, passer en resumable


def token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


# ---------- HTTP helpers ----------
def _post(path, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"https://graph.facebook.com/{API}/{path}", data=data)
    try:
        return json.load(urllib.request.urlopen(req)), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()

def _get(path, params):
    params = dict(params); params["access_token"] = token()
    url = f"https://graph.facebook.com/{API}/{path}?" + urllib.parse.urlencode(params)
    try:
        return json.load(urllib.request.urlopen(url)), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()

def _multipart(path, fields, file_field=None):
    boundary = "----metaads" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    if file_field:
        # (name, chunk) ou (name, chunk, filename, content_type)
        name, chunk = file_field[0], file_field[1]
        fname = file_field[2] if len(file_field) > 2 else "f"
        ctype = file_field[3] if len(file_field) > 3 else "application/octet-stream"
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; "
                 f"filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        body += chunk + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"https://graph.facebook.com/{API}/{path}", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        return json.load(urllib.request.urlopen(req, timeout=600)), None
    except urllib.error.HTTPError as e:
        return None, e.read().decode()


# ---------- Assets ----------
def upload_image(path):
    """POST /adimages. Retourne image_hash. Filename avec extension + content-type image
    obligatoires (sinon erreur 1487411)."""
    base = os.path.basename(path)
    ext = base.rsplit(".", 1)[-1].lower()
    ctype = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        r, err = _multipart(f"{ACCOUNT}/adimages", {"access_token": token()},
                            ("filename", f.read(), base, ctype))
    if err:
        raise RuntimeError(f"upload_image {path}: {err}")
    return list(r["images"].values())[0]["hash"]

def upload_video(path, title):
    """Upload simple (<95Mo) ou resumable (>=95Mo, sinon HTTP 413). Retourne video_id ready."""
    size = os.path.getsize(path)
    if size < SIMPLE_UPLOAD_MAX:
        with open(path, "rb") as f:
            r, err = _multipart(f"{ACCOUNT}/advideos",
                                {"title": title, "access_token": token()},
                                ("source", f.read(), os.path.basename(path), "video/mp4"))
        if err:
            raise RuntimeError(f"upload_video simple {path}: {err}")
        vid = r["id"]
    else:
        vid = _upload_video_resumable(path, title)
    _wait_video_ready(vid)
    return vid

def _upload_video_resumable(path, title):
    size = os.path.getsize(path); tk = token()
    start, err = _multipart(f"{ACCOUNT}/advideos",
                            {"upload_phase": "start", "file_size": size, "access_token": tk})
    if err: raise RuntimeError(f"resumable start: {err}")
    vid, sess = start["video_id"], start["upload_session_id"]
    so, eo = int(start["start_offset"]), int(start["end_offset"])
    with open(path, "rb") as f:
        while so < eo:
            f.seek(so); chunk = f.read(eo - so)
            r, err = _multipart(f"{ACCOUNT}/advideos",
                                {"upload_phase": "transfer", "upload_session_id": sess,
                                 "start_offset": so, "access_token": tk},
                                ("video_file_chunk", chunk))
            if err: raise RuntimeError(f"resumable transfer @{so}: {err}")
            so, eo = int(r["start_offset"]), int(r["end_offset"])
    _, err = _multipart(f"{ACCOUNT}/advideos",
                        {"upload_phase": "finish", "upload_session_id": sess,
                         "title": title, "access_token": tk})
    if err: raise RuntimeError(f"resumable finish: {err}")
    return vid

def _wait_video_ready(video_id, tries=40, delay=5):
    for _ in range(tries):
        d, err = _get(video_id, {"fields": "status"})
        if not err and d.get("status", {}).get("video_status") == "ready":
            return True
        time.sleep(delay)
    raise RuntimeError(f"video {video_id} pas ready après {tries*delay}s")

def video_thumbnail(path, at_sec=2):
    """Extrait une frame via ffmpeg, l'upload en adimage, retourne image_hash."""
    out = f"/tmp/thumb_{uuid.uuid4().hex}.jpg"
    subprocess.run(["ffmpeg", "-y", "-ss", str(at_sec), "-i", path,
                    "-vframes", "1", "-q:v", "3", out], capture_output=True)
    if not os.path.exists(out):
        raise RuntimeError(f"ffmpeg frame fail: {path}")
    return upload_image(out)


# ---------- Creatives ----------
def make_static_creative(name, image_hash, utm, bodies, titles, descriptions, cta=DEFAULT_CTA,
                         link=None, caption=None, opt_out_visuel=False):
    """Static flexible ad (Advantage+ texte). link_data porte image+lien+CTA,
    asset_feed_spec porte le pool de textes (DEGREES_OF_FREEDOM). Pas de video_data."""
    # Précédence link/caption: voir resolve_link (URL de manifeste = telle quelle).
    link = resolve_link(link, utm)
    cap = resolve_caption(caption)
    oss = {"page_id": PAGE_ID, "link_data": {
        "image_hash": image_hash, "link": link, "caption": cap,
        "call_to_action": {"type": cta}}}
    afs = {"bodies": [{"text": b} for b in bodies],
           "titles": [{"text": t} for t in titles],
           "descriptions": [{"text": d} for d in descriptions],
           "optimization_type": "DEGREES_OF_FREEDOM"}
    r, err = _post(f"{ACCOUNT}/adcreatives", {
        "name": name, "object_story_spec": json.dumps(oss),
        "asset_feed_spec": json.dumps(afs), "access_token": token(),
        **_dof_optout(opt_out_visuel)})
    if err: raise RuntimeError(f"static creative {name}: {err}")
    return r["id"]

# Placements verticaux (9:16), le reste tombe dans la règle défaut (carré).
VERT_PLACEMENTS = {
    "publisher_platforms": ["facebook", "instagram", "messenger"],
    "facebook_positions": ["story", "facebook_reels", "facebook_reels_overlay"],
    "instagram_positions": ["story", "reels"],
    "messenger_positions": ["story"],
}

def make_video_placement_creative(name, vert_id, sq_id, vert_thumb, sq_thumb,
                                  utm, body, title, description, cta=DEFAULT_CTA,
                                  link=None, caption=None, opt_out_visuel=False):
    """Vidéo single avec customization par placement: 9:16 sur Reels/Stories, carré sur Feed.
    RECETTE CRITIQUE (confirmée en production):
    - PAS de video_data dans object_story_spec (sinon videos/rules droppés silencieusement).
    - call_to_actions[] porte le link (règle erreur 2061015 'link required').
    - UN SEUL body/title/desc (multi-body incompatible avec customization, err 1885878).
    - optimization_type=PLACEMENT (sinon err geo 2446501).
    - règle défaut: customization_spec VIDE {} + is_default (err 1885923 sinon).
    - thumbnail_hash par vidéo (pas image_hash)."""
    # Précédence link/caption: voir resolve_link (URL de manifeste = telle quelle).
    link = resolve_link(link, utm)
    cap = resolve_caption(caption)
    cta_val = {"type": cta, "value": {"link": link, "link_caption": cap}}
    oss = {"page_id": PAGE_ID, "instagram_user_id": IG_USER_ID}
    afs = {
        "videos": [
            {"video_id": vert_id, "thumbnail_hash": vert_thumb, "adlabels": [{"name": "vert"}]},
            {"video_id": sq_id,   "thumbnail_hash": sq_thumb,   "adlabels": [{"name": "sq"}]},
        ],
        "bodies": [{"text": body}], "titles": [{"text": title}],
        "descriptions": [{"text": description}],
        "link_urls": [{"website_url": link, "display_url": cap}],
        "call_to_action_types": [cta],
        "call_to_actions": [cta_val],
        "ad_formats": ["SINGLE_VIDEO"],
        "optimization_type": "PLACEMENT",
        "asset_customization_rules": [
            {"customization_spec": VERT_PLACEMENTS, "video_label": {"name": "vert"}, "priority": 1},
            {"customization_spec": {}, "video_label": {"name": "sq"}, "priority": 2, "is_default": True},
        ],
    }
    r, err = _post(f"{ACCOUNT}/adcreatives", {
        "name": name, "object_story_spec": json.dumps(oss),
        "asset_feed_spec": json.dumps(afs), "access_token": token(),
        **_dof_optout(opt_out_visuel)})
    if err: raise RuntimeError(f"video creative {name}: {err}")
    return r["id"]


def make_static_placement_creative(name, vert_hash, feed_hash, utm, body, title, description,
                                   cta=DEFAULT_CTA, link=None, caption=None, opt_out_visuel=False):
    """Static multi-format avec customization par placement: image 9:16 (vert_hash) sur
    Reels/Stories, image 1:1 ou 4:5 (feed_hash) sur Feed et le reste.
    Même recette que la vidéo: PAS de link_data, call_to_actions[] porte le link,
    1 body/title/desc, optimization_type PLACEMENT, règle defaut customization_spec
    vide. Thumbnail = image elle-meme (image_hash)."""
    # Précédence link/caption: voir resolve_link (URL de manifeste = telle quelle).
    link = resolve_link(link, utm)
    cap = resolve_caption(caption)
    cta_val = {"type": cta, "value": {"link": link, "link_caption": cap}}
    oss = {"page_id": PAGE_ID, "instagram_user_id": IG_USER_ID}
    afs = {
        "images": [
            {"hash": vert_hash, "adlabels": [{"name": "vert"}]},
            {"hash": feed_hash, "adlabels": [{"name": "feed"}]},
        ],
        "bodies": [{"text": body}], "titles": [{"text": title}],
        "descriptions": [{"text": description}],
        "link_urls": [{"website_url": link, "display_url": cap}],
        "call_to_action_types": [cta],
        "call_to_actions": [cta_val],
        "ad_formats": ["SINGLE_IMAGE"],
        "optimization_type": "PLACEMENT",
        "asset_customization_rules": [
            {"customization_spec": VERT_PLACEMENTS, "image_label": {"name": "vert"}, "priority": 1},
            {"customization_spec": {}, "image_label": {"name": "feed"}, "priority": 2, "is_default": True},
        ],
    }
    cr, err = _post(f"{ACCOUNT}/adcreatives", {
        "name": name, "object_story_spec": json.dumps(oss),
        "asset_feed_spec": json.dumps(afs), "access_token": token(),
        **_dof_optout(opt_out_visuel)})
    if err:
        raise RuntimeError(f"static placement creative {name}: {err}")
    return cr["id"]


# ---------- Lifecycle: édition de copy, refresh, wind-down promo ----------
# Recettes confirmées en production. Voir meta-campaign-lifecycle.md (doctrine)
# et api/meta-api-errors.md.

# Token de code promo à retirer en wind-down. Adapter à votre convention.
PROMO_RE = re.compile(r"CODE-PROMO-EXEMPLE|code promo", re.IGNORECASE)


def strip_promo_from_text(text, promo_re=PROMO_RE):
    """Retire une mention de code promo AU NIVEAU PHRASE (pas juste le token),
    sinon on laisse des fragments de phrase cassés.
    Découpe par phrases, drop celles qui contiennent le token, rejoint.
    Une description 100% promo devient chaîne vide (l'appelant la drop alors)."""
    if not text:
        return text
    parts = re.split(r'(?<=[.!?])\s+', text)
    kept = [p for p in parts if not promo_re.search(p)]
    return " ".join(kept).strip()


def _clean_recreate_spec(oss, afs, dof, drop_promo=False):
    """Nettoie les 3 champs qui cassent à la RECRÉATION d'une créative clonée
    (confirmé en production). Mute en place et retourne (oss, afs, dof).
    - object_story_spec.video_data: retirer image_url si image_hash présent
      (subcode 1443051 ObjectStorySpecRedundant).
    - degrees_of_freedom_spec.creative_features_spec: retirer standard_enhancements
      ET standard_enhancements_catalog (déprécié à la création, subcode 3858504).
    - asset_feed_spec.promotional_metadata: retirer quand drop_promo
      (wind-down du code promo)."""
    if oss:
        vd = oss.get("video_data")
        if isinstance(vd, dict) and vd.get("image_hash") and "image_url" in vd:
            vd.pop("image_url", None)
        ld = oss.get("link_data")
        if isinstance(ld, dict) and ld.get("image_hash") and "image_url" in ld:
            ld.pop("image_url", None)
    if dof:
        cfs = dof.get("creative_features_spec")
        if isinstance(cfs, dict):
            cfs.pop("standard_enhancements", None)
            cfs.pop("standard_enhancements_catalog", None)
    if afs and drop_promo:
        afs.pop("promotional_metadata", None)
    return oss, afs, dof


def clone_creative_new_copy(creative_id, body_fn=None, drop_promo=False, name=None):
    """Édite la copy d'une ad sans muter la créative (immuable): pull la créative,
    clone object_story_spec + asset_feed_spec + degrees_of_freedom_spec, nettoie
    les 3 champs cassants, applique body_fn aux bodies/descriptions, POST une
    NOUVELLE créative, retourne son id. Réversible (l'ancienne reste intacte).

    body_fn(text) -> text|"" : transforme chaque body/description. "" => drop.
    Si body_fn est None et drop_promo True, applique strip_promo_from_text.
    Brancher ensuite swap_ad_creative(ad_id, new_id) pour pointer l'ad dessus."""
    fields = "name,object_story_spec,asset_feed_spec,degrees_of_freedom_spec"
    cur, err = _get(creative_id, {"fields": fields})
    if err:
        raise RuntimeError(f"clone pull {creative_id}: {err}")
    oss = cur.get("object_story_spec")
    afs = cur.get("asset_feed_spec")
    dof = cur.get("degrees_of_freedom_spec")
    if body_fn is None:
        body_fn = (lambda t: strip_promo_from_text(t)) if drop_promo else (lambda t: t)

    def _apply(items, key):
        out = []
        for it in items or []:
            nt = body_fn(it.get(key, ""))
            if nt:
                d = dict(it); d[key] = nt; out.append(d)
        return out

    if afs:
        if "bodies" in afs:
            afs["bodies"] = _apply(afs["bodies"], "text")
        if "descriptions" in afs:
            afs["descriptions"] = _apply(afs["descriptions"], "text")
        if "titles" in afs:
            afs["titles"] = _apply(afs["titles"], "text")
    if oss:
        ld = oss.get("link_data")
        if isinstance(ld, dict):
            if ld.get("message"):
                ld["message"] = body_fn(ld["message"]) or ld["message"]
            if ld.get("name"):
                ld["name"] = body_fn(ld["name"]) or ld["name"]
            if ld.get("description"):
                ld["description"] = body_fn(ld["description"]) or ""
        vd = oss.get("video_data")
        if isinstance(vd, dict):
            if vd.get("message"):
                vd["message"] = body_fn(vd["message"]) or vd["message"]
            if vd.get("title"):
                vd["title"] = body_fn(vd["title"]) or vd["title"]

    oss, afs, dof = _clean_recreate_spec(oss, afs, dof, drop_promo=drop_promo)
    params = {"name": name or (cur.get("name", "creative") + "-v2"),
              "access_token": token()}
    if oss: params["object_story_spec"] = json.dumps(oss)
    if afs: params["asset_feed_spec"] = json.dumps(afs)
    if dof: params["degrees_of_freedom_spec"] = json.dumps(dof)
    r, err = _post(f"{ACCOUNT}/adcreatives", params)
    if err:
        raise RuntimeError(f"clone_creative_new_copy {creative_id}: {err}")
    return r["id"]


def swap_ad_creative(ad_id, new_creative_id):
    """Pointe une ad existante vers une nouvelle créative (édition de copy réversible).
    PATCH l'ad: POST {ad_id} creative={creative_id:...}. L'ancienne créative reste
    intacte (rollback = swap vers l'ancien id)."""
    r, err = _post(ad_id, {
        "creative": json.dumps({"creative_id": new_creative_id}),
        "access_token": token()})
    if err:
        raise RuntimeError(f"swap_ad_creative {ad_id}->{new_creative_id}: {err}")
    return r


def make_static_simple(name, image_hash, utm, body, title, description, cta=DEFAULT_CTA,
                       link=None, caption=None, opt_out_visuel=False):
    """Static single-image SANS asset_feed_spec (fallback non-DOF).
    make_static_creative (DEGREES_OF_FREEDOM) plante avec 1 seul asset par champ
    (subcode 2446218 Not enough creative assets: DOF exige >1 asset sur au moins
    un champ). Pour un static single-image propre: object_story_spec.link_data avec
    message (body) / name (title) / description / caption / cta. Feed 1080x1350 (4:5)."""
    # Précédence link/caption: voir resolve_link (URL de manifeste = telle quelle).
    link = resolve_link(link, utm)
    cap = resolve_caption(caption)
    oss = {"page_id": PAGE_ID, "link_data": {
        "image_hash": image_hash, "link": link, "caption": cap,
        "message": body, "name": title, "description": description,
        "call_to_action": {"type": cta}}}
    r, err = _post(f"{ACCOUNT}/adcreatives", {
        "name": name, "object_story_spec": json.dumps(oss), "access_token": token(),
        **_dof_optout(opt_out_visuel)})
    if err:
        raise RuntimeError(f"static simple {name}: {err}")
    return r["id"]


# ---------- Lifecycle: kill / backtrack (registre persistant) ----------
# Façon CANONIQUE de couper une ad et de la rouvrir si les conversions
# différées rentrent. Voir meta-campaign-lifecycle.md.
#
# FORMAT DU REGISTRE (figé) : un fichier JSON dict
#   { ad_name: {"ad_id": str|None, "ic_at_kill": float,
#               "killed_at": iso8601, "by": str} }
# Compat ascendante : les vieilles entrées (kills manuels) peuvent ne pas
# avoir "ad_id", l'absence est gérée gracieusement (re-résolu par nom).

KILL_REGISTRY = os.path.expanduser(os.environ.get("META_KILL_REGISTRY", "~/.meta_ads/killed_ads.json"))


def _load_registry(registry_path):
    """Lit le registre JSON. Retourne {} si le fichier est absent."""
    if os.path.exists(registry_path):
        with open(registry_path) as f:
            return json.load(f)
    return {}


def _save_registry(registry_path, reg):
    """Écrit le registre JSON (indent 1, accents préservés)."""
    with open(registry_path, "w") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)


def record_kill(registry_path, ad_name, ad_id, ic_at_kill, by):
    """Coupe une ad et l'inscrit au registre des kills. Idempotent.
    - Pause l'ad (status PAUSED via _post).
    - Inscrit/écrase l'entrée { ad_id, ic_at_kill, killed_at, by } sous ad_name.
    - Crée le fichier de registre s'il est absent.
    Retourne l'entrée écrite. Si déjà au registre, ré-pause (no-op côté Meta)
    et rafraîchit l'entrée : sûr à rejouer."""
    r, err = _post(ad_id, {"status": "PAUSED", "access_token": token()})
    if err:
        raise RuntimeError(f"record_kill pause {ad_name} ({ad_id}): {err}")
    reg = _load_registry(registry_path)
    entry = {"ad_id": ad_id, "ic_at_kill": float(ic_at_kill),
             "killed_at": datetime.datetime.now().isoformat(), "by": by}
    reg[ad_name] = entry
    _save_registry(registry_path, reg)
    return entry


def check_backtrack(registry_path, campaign_id, gained_threshold):
    """Rouvre les ads coupées dont les conversions différées sont rentrées.
    Pour chaque entrée du registre : pull l'IC actuel par ad de la campagne
    (offsite_conversion.fb_pixel_initiate_checkout), et si
    IC_actuel - ic_at_kill >= gained_threshold, réactive l'ad (status ACTIVE)
    et la retire du registre. Idempotent : ne touche que les ads encore au
    registre. Retourne la liste des dicts réactivés
    [{name, ad_id, ic_at_kill, ic_now, gained}].

    Résolution de l'ad_id : utilise l'entrée si présente (nouveau format),
    sinon re-résout par nom via {campaign}/ads (compat vieilles entrées)."""
    reg = _load_registry(registry_path)
    if not reg:
        return []

    # IC actuel par nom d'ad
    r, err = _get(f"{campaign_id}/insights",
                  {"level": "ad", "fields": "ad_name,actions", "limit": 500})
    if err:
        raise RuntimeError(f"check_backtrack insights {campaign_id}: {err}")

    def _ic(acts):
        for a in acts or []:
            if a.get("action_type") == "offsite_conversion.fb_pixel_initiate_checkout":
                return float(a["value"])
        return 0.0
    ic_now = {d["ad_name"]: _ic(d.get("actions")) for d in r.get("data", [])}

    # ids par nom (pour les entrées sans ad_id)
    ra, err = _get(f"{campaign_id}/ads", {"fields": "id,name", "limit": 500})
    if err:
        raise RuntimeError(f"check_backtrack ads {campaign_id}: {err}")
    ids_by_name = {d["name"]: d["id"] for d in ra.get("data", [])}

    reactivated = []
    for name, info in list(reg.items()):
        if name not in ic_now:
            continue
        cur = ic_now[name]
        gained = cur - float(info.get("ic_at_kill", 0))
        if gained < gained_threshold:
            continue
        ad_id = info.get("ad_id") or ids_by_name.get(name)
        if not ad_id:
            continue
        _, err = _post(ad_id, {"status": "ACTIVE", "access_token": token()})
        if err:
            raise RuntimeError(f"check_backtrack reactivate {name} ({ad_id}): {err}")
        reactivated.append({"name": name, "ad_id": ad_id,
                            "ic_at_kill": float(info.get("ic_at_kill", 0)),
                            "ic_now": cur, "gained": gained})
        reg.pop(name, None)
    _save_registry(registry_path, reg)
    return reactivated


# ---------- Règles de seuil, de fenêtre et de plafonnement (rev. 2026-11) ----------
# Fonctions pures (aucun appel réseau) sauf mention. Marque [rev. 2026-11].
SEUIL_ZERO_IC = 2.0        # [rev. 2026-11] kill a 0 IC des 2x cible_cpic dépensés
SEUIL_ECART = 3.0          # [rev. 2026-11] kill des 3x cible_cpic si cout/IC > 1,5x cible
ECART_MAX = 1.5            # [rev. 2026-11] "plus de 50 % au-dessus de la cible"
TOLERANCE_CIBLE = 0.10     # une campagne "tient sa cible" si cout/IC <= cible x 1,10
PART_DOMINANTE = 0.30      # [rev. 2026-11] ad ou ad set a plus de 30 % de la depense

def fenetre_min(date_lancement, cible_cpic, budget_jour):
    """[rev. 2026-11] Fenêtre minimale avant tout kill, en JOURS (float) :
    le plus grand de 3 jours ou du temps pour depenser 10 IC au cout cible
    (10 * cible_cpic / budget_jour). date_lancement est accepté pour la signature
    canonique et la cohérence d'appel (la durée ne depend pas de la date; voir
    fenetre_ecoulee pour le test a une date donnee)."""
    if not budget_jour or budget_jour <= 0:
        return 3.0
    return max(3.0, 10.0 * float(cible_cpic) / float(budget_jour))

def fenetre_ecoulee(date_lancement, cible_cpic, budget_jour, now=None):
    """True si fenetre_min est passee depuis date_lancement (datetime ou ISO)."""
    if isinstance(date_lancement, str):
        date_lancement = datetime.datetime.fromisoformat(date_lancement)
    now = now or datetime.datetime.now(date_lancement.tzinfo)
    jours = (now - date_lancement).total_seconds() / 86400.0
    return jours >= fenetre_min(date_lancement, cible_cpic, budget_jour)

def seuil_kill_relatif(cible_cpic, spend, ic):
    """[rev. 2026-11] Deux paliers sur la depense CUMULEE :
    (1) spend >= 2x cible et 0 IC ; (2) spend >= 3x cible et cout/IC > 1,5x cible.
    Sous 2x cible dépensés : jamais. Retourne (kill: bool, raison: str)."""
    if spend < SEUIL_ZERO_IC * cible_cpic:
        return False, "sous 2x cible_cpic dépensés"
    if ic <= 0:
        return True, f"{spend:.0f}$ >= 2x cible ({SEUIL_ZERO_IC * cible_cpic:.0f}$) et 0 IC"
    cpic = spend / ic
    if spend >= SEUIL_ECART * cible_cpic and cpic > ECART_MAX * cible_cpic:
        return True, (f"{spend:.0f}$ >= 3x cible et cout/IC {cpic:.0f}$ > "
                      f"1,5x cible ({ECART_MAX * cible_cpic:.0f}$)")
    return False, "seuils non atteints"

def campagne_tient_cible(cible_cpic, camp):
    """camp = {"sp":..., "ic":...}. Vrai si IC > 0 et cout/IC <= cible x (1 + TOLERANCE_CIBLE)."""
    return camp["ic"] > 0 and camp["sp"] / camp["ic"] <= cible_cpic * (1 + TOLERANCE_CIBLE)

def palier_plafond(part_actuelle, palier=0.10):
    """[rev. 2026-11] Plafond en part de la depense de campagne, par paliers de
    10 a 20 points sous la part actuelle (palier dans [0.10, 0.20])."""
    palier = min(max(palier, 0.10), 0.20)
    return max(round(part_actuelle - palier, 2), 0.05)

def evaluer_cascade(cible_cpic, camp, adsets, ads, ad_adset, whitelist=(), fenetre_ok=None):
    """[rev. 2026-11] Campagne d'abord, puis ad set, puis ad. Entrées :
    camp {"sp","ic"}; adsets {nom:{"sp","ic"}}; ads {nom:{"sp","ic"}}; ad_adset {ad:adset}.
    Retourne une liste de décisions {niveau, nom, action, raison} ; action = KILL
    (ad), RECO_KILL (ad set : recommandation, jamais exécutée), PLAFOND (reco de
    plafond, jamais un kill) ou TENIR. Si la campagne tient sa cible, toute ad ou ad
    set à plus de 30 % de la dépense (ou no 1 en dépense) est plafonné, pas tué.
    fenetre_ok (optionnel) : {(niveau, nom): bool} ; False = fenetre_min de CET objet pas
    écoulée (ancrée sur son created_time) donc aucun verdict de kill [rev. 2026-11]."""
    out = []
    tient = campagne_tient_cible(cible_cpic, camp)
    k, why = seuil_kill_relatif(cible_cpic, camp["sp"], camp["ic"])
    out.append({"niveau": "campagne", "nom": "campagne", "action": "TENIR",
                "raison": ("tient la cible" if tient else
                           ("rate la cible : " + why if k else "ne tient pas la cible, seuils de kill non atteints"))})
    tot = camp["sp"] or 1.0

    def juger(niveau, nom, d, rang1):
        if fenetre_ok is not None and not fenetre_ok.get((niveau, nom), True):
            return {"niveau": niveau, "nom": nom, "action": "TENIR",
                    "raison": "fenetre_min de cet objet pas écoulée (AUCUN KILL)"}
        kill, raison = seuil_kill_relatif(cible_cpic, d["sp"], d["ic"])
        part = d["sp"] / tot
        if not kill:
            return {"niveau": niveau, "nom": nom, "action": "TENIR", "raison": raison}
        if tient and (part > PART_DOMINANTE or rang1):
            return {"niveau": niveau, "nom": nom, "action": "PLAFOND",
                    "raison": f"campagne tient la cible, part {part:.0%} : plafonner à "
                              f"{palier_plafond(part):.0%} de la dépense, pas de kill ({raison})"}
        return {"niveau": niveau, "nom": nom,
                "action": "RECO_KILL" if niveau == "adset" else "KILL", "raison": raison}

    no1_adset = max(adsets, key=lambda n: adsets[n]["sp"]) if adsets else None
    no1_ad = max(ads, key=lambda n: ads[n]["sp"]) if ads else None
    adsets_tues = set()
    for nom, d in adsets.items():
        dec = juger("adset", nom, d, nom == no1_adset)
        out.append(dec)
        if dec["action"] == "RECO_KILL":
            adsets_tues.add(nom)
    for nom, d in ads.items():
        if nom in whitelist or ad_adset.get(nom) in adsets_tues:
            continue
        out.append(juger("ad", nom, d, nom == no1_ad))
    return out

def make_creative_from_post(name, object_story_id, opt_out_visuel=False, go=False):
    """[rev. 2026-11] Creative sur un post EXISTANT (object_story_id =
    '<page_id>_<post_id>') : garde la preuve sociale. ÉCRITURE : sans go=True, retour
    simulé et AUCUN POST. opt_out_visuel=True ajoute un opt-out explicite des
    enhancements visuels [NON VÉRIFIÉ live] (défaut False : le post garde son contenu)."""
    if not go:
        return {"dry_run": True, "action": "adcreatives", "name": name,
                "object_story_id": object_story_id}
    params = {"name": name, "object_story_id": object_story_id, "access_token": token(),
              **_dof_optout(opt_out_visuel)}
    r, err = _post(f"{ACCOUNT}/adcreatives", params)   # [NON VÉRIFIÉ live] object_story_id
    if err: raise RuntimeError(f"creative from post {name}: {err}")
    return r["id"]

def create_ad_from_post(name, adset_id, object_story_id, status="PAUSED", opt_out_visuel=False, go=False):
    """[rev. 2026-11] Ad à partir d'un post ID existant. PAUSED par défaut.
    Sans go=True : retour simulé, aucun POST."""
    if not go:
        return {"dry_run": True, "action": "ads", "name": name, "adset_id": adset_id,
                "object_story_id": object_story_id, "status": status}
    cid = make_creative_from_post(name, object_story_id, opt_out_visuel, go=True)
    return create_ad(name, adset_id, cid, status)

# [rev. 2026-11] Enhancements qui modifient l'image ou la vidéo. Noms de features
# [NON VÉRIFIÉ live] (Advantage+ creative, creative_features_spec). Texte et CTA restent
# permis. opt_out_visuel=True est disponible mais le défaut reste False tant qu'un tir de
# test n'a pas vérifié ces noms ; d'ici là, vérifier dans Ads Manager après création.
# 'standard_enhancements' (déprécié, subcode 3858504) est déjà retiré par _clean_recreate_spec.
VISUAL_ENHANCEMENT_FEATURES = ("image_brightness_and_contrast", "image_templates",
                               "image_touchups", "image_uncrop", "video_auto_crop")

def refuse_visual_enhancements(dof):
    """Lève ValueError si un enhancement VISUEL est OPT_IN dans un
    degrees_of_freedom_spec ; retourne dof tel quel sinon (vérifie, ne modifie pas)."""
    cfs = ((dof or {}).get("creative_features_spec")) or {}
    for k in VISUAL_ENHANCEMENT_FEATURES:
        if (cfs.get(k) or {}).get("enroll_status") == "OPT_IN":
            raise ValueError(f"enhancement visuel refusé : {k} OPT_IN [rev. 2026-11]")
    return dof

def _dof_optout(opt_out_visuel):
    """[rev. 2026-11] Params à fusionner dans un POST adcreatives : opt-out des
    enhancements VISUELS si opt_out_visuel=True ; {} sinon (défaut)."""
    if not opt_out_visuel:
        return {}
    return {"degrees_of_freedom_spec": json.dumps(refuse_visual_enhancements({
        "creative_features_spec": {k: {"enroll_status": "OPT_OUT"}
                                   for k in VISUAL_ENHANCEMENT_FEATURES}}))}


def set_adset_spend_cap(adset_id, daily_spend_cap_cad=None, daily_min_spend_target_cad=None, go=False):
    """[rev. 2026-11] Spending limits d'ad set sous CBO. Champs
    daily_spend_cap [NON VERIFIE live] et daily_min_spend_target (en cents, confirmé
    en création CBO). Montants en CAD, convertis en cents.
    Sans go=True : retourne les params SANS écrire (aucun POST)."""
    params = {}
    if daily_spend_cap_cad is not None:
        params["daily_spend_cap"] = int(round(daily_spend_cap_cad * 100))
    if daily_min_spend_target_cad is not None:
        params["daily_min_spend_target"] = int(round(daily_min_spend_target_cad * 100))
    if not go:
        return {"dry_run": True, "adset_id": adset_id, "params": params}
    r, err = _post(adset_id, dict(params, access_token=token()))
    if err: raise RuntimeError(f"set_adset_spend_cap {adset_id}: {err}")
    return r


# ---------- Ads ----------
def create_ad(name, adset_id, creative_id, status="PAUSED"):
    """Crée l'ad. DEFAULT PAUSED, passer ACTIVE seulement sur instruction explicite."""
    r, err = _post(f"{ACCOUNT}/ads", {
        "name": name, "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": status, "access_token": token()})
    if err: raise RuntimeError(f"create_ad {name}: {err}")
    return r["id"]

def set_ad_status(ad_id, status):
    r, err = _post(ad_id, {"status": status, "access_token": token()})
    if err: raise RuntimeError(f"set_status {ad_id}: {err}")
    return r

def verify_ad(ad_id):
    d, err = _get(ad_id, {"fields": "name,status,effective_status"})
    if err: raise RuntimeError(f"verify {ad_id}: {err}")
    return d


if __name__ == "__main__":
    # smoke test: valide le token + le compte
    d, err = _get("me", {"fields": "id,name"})
    print("token OK:" if not err else "TOKEN ERR:", d or err)
