#!/usr/bin/env python3
"""Exemple de re-check autonome (ex. le soir après une redistribution de budget) :
backtrack des ads coupées à tort, puis kill selon le seuil relatif à `cible_cpic`
(cascade campagne > ad set > ad), après `fenetre_min`, avec whitelist et journal.
Compare le pull actuel à un snapshot baseline (produit par pull_insights.py).

Voir doctrines/meta-campaign-lifecycle.md section 2 (kill + backtrack) et
meta_lib.record_kill / meta_lib.check_backtrack, qui encapsulent la logique de
registre. Ce script montre la version "à la main", conservée comme référence.

Usage: evening_kill.py [options] <campaign_id> <baseline_label> [output_label]
  baseline_label : nom du snapshot de référence (ex. 'samedi_pm')
  output_label   : nom du snapshot produit par ce run (défaut 'evening_check')

Options (retirées de argv avant les positionnels) [rev. 2026-11] :
  --dry-run                 aucune écriture (ni Graph API, ni registre, ni log disque)
  --fixture <json>          aucun appel API (implique --dry-run), chemin obligatoire ; voir tests/fixture_evening_kill.json
  --cible-cpic N            coût cible par IC (prime sur l'environnement)
  --date-lancement ISO      date de lancement de la campagne (prime sur l'environnement)
  --budget-jour N           budget quotidien de la campagne en $ (sinon lu sur la campagne)

Config par variables d'environnement :
  META_KILL_CIBLE_CPIC      coût cible par IC (OBLIGATOIRE si pas de --cible-cpic)
  META_KILL_DATE_LANCEMENT  date de lancement ISO (OBLIGATOIRE si pas de --date-lancement)
  META_KILL_BUDGET_JOUR     budget quotidien en $ (optionnel)
  META_KILL_BACKTRACK_IC    IC gagnés en différé depuis un kill -> on rouvre (défaut 2)
  META_KILL_WHITELIST       noms d'ads à ne jamais toucher, séparés par des virgules

Aucune valeur par défaut silencieuse pour la cible et la date : absent = arrêt clair.
"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m


def _flag(name, has_value=True):
    if name not in sys.argv:
        return None if has_value else False
    i = sys.argv.index(name)
    if not has_value:
        sys.argv.pop(i); return True
    if i + 1 >= len(sys.argv) or sys.argv[i + 1].startswith("--"):
        sys.exit(f"ERREUR: {name} exige une valeur (ex. {name} chemin_ou_valeur)")
    v = sys.argv[i + 1]; del sys.argv[i:i + 2]; return v

DRY = _flag("--dry-run", False)
FIXTURE = _flag("--fixture")
F_CIBLE, F_DATE, F_BUDGET = _flag("--cible-cpic"), _flag("--date-lancement"), _flag("--budget-jour")
if FIXTURE:
    DRY = True
    FX = json.load(open(FIXTURE))

if len(sys.argv) < 3 and not FIXTURE:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1] if len(sys.argv) > 1 else "fixture"
BASE = sys.argv[2] if len(sys.argv) > 2 else "baseline"
OUT = sys.argv[3] if len(sys.argv) > 3 else "evening_check"

SNAPDIR = os.path.expanduser(os.environ.get("META_SNAPSHOT_DIR", "~/.meta_ads/snapshots"))
LOG = os.path.expanduser(os.environ.get("META_JOB_LOG", "~/.meta_ads/evening_kill.log"))
PM = os.path.join(SNAPDIR, f"{BASE}.json")
REG = m.KILL_REGISTRY
BACKTRACK_IC = float(os.environ.get("META_KILL_BACKTRACK_IC", "2"))
WHITELIST = {n.strip() for n in os.environ.get("META_KILL_WHITELIST", "").split(",") if n.strip()}


def log(msg):
    line = f"{datetime.datetime.now().isoformat()} {msg}"
    print(line)
    if not DRY:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f: f.write(line + "\n")


# [rev. 2026-11] cible_cpic et date_lancement OBLIGATOIRES (flags, environnement ou fixture).
_cfg = dict(FX.get("config", {})) if FIXTURE else {}
CIBLE_CPIC = F_CIBLE or os.environ.get("META_KILL_CIBLE_CPIC") or _cfg.get("cible_cpic")
DATE_LANCEMENT = F_DATE or os.environ.get("META_KILL_DATE_LANCEMENT") or _cfg.get("date_lancement")
if not CIBLE_CPIC or not DATE_LANCEMENT:
    sys.exit("ERREUR: cible_cpic et date_lancement obligatoires (--cible-cpic/--date-lancement "
             "ou META_KILL_CIBLE_CPIC/META_KILL_DATE_LANCEMENT). Aucun kill sans cible [rev. 2026-11].")
CIBLE_CPIC = float(CIBLE_CPIC)
DATE_LANCEMENT = m.en_aware(DATE_LANCEMENT)   # sans offset = fuseau META_TZ (défaut UTC)
NOW = m.en_aware(FX["now"]) if FIXTURE and FX.get("now") else datetime.datetime.now(DATE_LANCEMENT.tzinfo)

log("=== evening re-check start ===")

pm = {r["n"]: r for r in (FX["baseline"] if FIXTURE else json.load(open(PM))["rows"])}

flds = "ad_name,adset_name,spend,frequency,actions"
if FIXTURE:
    r, err = {"data": FX["insights"]}, None
else:
    r, err = m._get(f"{CAMPAIGN}/insights",
                    {"level": "ad", "fields": flds,
                     # fenêtre calculée : date_lancement -> aujourd'hui (vie complète)
                     "time_range": json.dumps({"since": DATE_LANCEMENT.date().isoformat(),
                                               "until": datetime.date.today().isoformat()}),
                     "limit": 200})
if err:
    log(f"ERR insights {err}"); raise SystemExit(1)


def ic(acts):
    for a in acts or []:
        if a["action_type"] == "offsite_conversion.fb_pixel_initiate_checkout":
            return float(a["value"])
    return 0.0


now = {d["ad_name"]: {"sp": float(d.get("spend", 0)), "ic": ic(d.get("actions")),
                      "fr": float(d.get("frequency", 0))} for d in r.get("data", [])}

if FIXTURE:
    ra = {"data": FX["ads"]}
else:
    ra, _ = m._get(f"{CAMPAIGN}/ads", {"fields": "id,name,status,effective_status,created_time,adset{name,created_time}", "limit": 200})
ids = {d["name"]: d["id"] for d in ra.get("data", [])}
live = {d["name"]: d["id"] for d in ra.get("data", [])
        if d.get("effective_status") == "ACTIVE"}

# --- PASS 1 : BACKTRACK. Rouvre les ads coupées si conversions différées rentrées ---
reg = json.load(open(REG)) if os.path.exists(REG) else {}
for name, info in list(reg.items()):
    cur = now.get(name)
    if not cur:
        continue
    gained = cur["ic"] - info.get("ic_at_kill", 0)
    log(f"  [backtrack] {name[:46]:46} IC kill={info.get('ic_at_kill',0)} -> now={cur['ic']:.0f} (+{gained:.0f})")
    if gained >= BACKTRACK_IC and ids.get(name) and DRY:
        log(f"  [dry-run] REACTIVATE {name[:46]} (+{gained:.0f} IC différés)")
    elif gained >= BACKTRACK_IC and ids.get(name):
        rr, e = m._post(ids[name], {"status": "ACTIVE", "access_token": m.token()})
        ok = "OK" if not e else f"ERR {str(e)[:80]}"
        log(f"  REACTIVATE {name[:46]:46} (+{gained:.0f} IC différés) -> {ok}")
        if not e:
            reg.pop(name, None)
if not DRY:
    os.makedirs(os.path.dirname(REG) or ".", exist_ok=True)
    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)

# --- PASS 2 : fenêtre minimale, puis cascade campagne > ad set > ad [rev. 2026-11] ---
# Dépense CUMULÉE (seuil relatif à cible_cpic) ; plafond au lieu de kill pour une ad
# dominante quand la campagne tient sa cible.
if FIXTURE:
    budget_jour = float(F_BUDGET or os.environ.get("META_KILL_BUDGET_JOUR") or _cfg.get("budget_jour") or FX.get("budget_jour", 0))
else:
    budget_jour = float(F_BUDGET or os.environ.get("META_KILL_BUDGET_JOUR") or 0)
    if not budget_jour:
        _c, _ = m._get(CAMPAIGN, {"fields": "daily_budget"})
        budget_jour = float((_c or {}).get("daily_budget", 0)) / 100.0
fen = m.fenetre_min(DATE_LANCEMENT, CIBLE_CPIC, budget_jour)
jours = (NOW - DATE_LANCEMENT).total_seconds() / 86400.0
log(f"  fenetre_min={fen:.2f} j (budget {budget_jour:.0f}$/j, cible {CIBLE_CPIC:.0f}$/IC); écoulé={jours:.2f} j")

adset_of = {d["ad_name"]: d.get("adset_name") for d in r.get("data", [])}
adsets_cum = {}
for n, v in now.items():
    a = adsets_cum.setdefault(adset_of.get(n) or "?", {"sp": 0.0, "ic": 0.0})
    a["sp"] += v["sp"]; a["ic"] += v["ic"]
camp_cum = {"sp": sum(v["sp"] for v in now.values()), "ic": sum(v["ic"] for v in now.values())}

candidates = []
# [rev. 2026-11] fenetre_min ancrée sur l'objet jugé : created_time de l'ad pour une ad, de
# l'ad set pour un ad set, date_lancement pour la campagne. Un pack neuf dans une campagne
# qui roule a sa propre fenêtre.
def _t(x):
    return m.en_aware(x) if x else None
ad_created = {d["name"]: _t(d.get("created_time")) for d in ra.get("data", [])}
adset_created = {}
for d in ra.get("data", []):
    aset = d.get("adset") or {}
    if aset.get("name") and aset.get("created_time"):
        adset_created[aset["name"]] = _t(aset["created_time"])
if FIXTURE:
    adset_created.update({k: _t(v) for k, v in FX.get("adsets_created", {}).items()})
def _ok(created):
    return created is None or (NOW - created).total_seconds() / 86400.0 >= fen
fenetre_ok = {("ad", n): _ok(ad_created.get(n)) for n in now}
fenetre_ok.update({("adset", n): _ok(adset_created.get(n)) for n in adsets_cum})
for (niv, n), ok_ in fenetre_ok.items():
    if not ok_:
        log(f"  fenetre_min pas écoulée pour {niv} {n[:46]} (créé {(ad_created if niv == 'ad' else adset_created).get(n)})")
if jours < fen:
    log(f"  AUCUN KILL : fenetre_min pas écoulée ({jours:.2f} j < {fen:.2f} j) [rev. 2026-11]")
    decisions = []
else:
    decisions = m.evaluer_cascade(CIBLE_CPIC, camp_cum, adsets_cum,
                                  {n: v for n, v in now.items() if n in live},
                                  adset_of, WHITELIST, fenetre_ok)
for d in decisions:
    log(f"  [{d['niveau']}] {d['nom'][:46]:46} {d['action']}: {d['raison']}")
    if d["niveau"] == "ad" and d["action"] == "KILL":
        candidates.append((d["nom"], live[d["nom"]], now[d["nom"]]["sp"], now[d["nom"]]["fr"]))

killed = []
for name, adid, d_sp, fr in candidates:
    if DRY:
        log(f"  [dry-run] KILL {name[:46]:46} (cumul {d_sp:.0f}$) -> aucune écriture")
        continue
    rr, e = m._post(adid, {"status": "PAUSED", "access_token": m.token()})
    ok = "OK" if not e else f"ERR {str(e)[:80]}"
    log(f"  KILL {name[:46]:46} (cumul {d_sp:.0f}$, seuil relatif) -> {ok}")
    if not e:
        killed.append(name)
        # le registre garde le verdict : cible, multiple de dépense, coût par IC.
        _ic = now.get(name, {}).get("ic", 0)
        reg[name] = {"ad_id": adid, "ic_at_kill": _ic,
                     "killed_at": datetime.datetime.now().isoformat(), "by": "evening-check",
                     "cible_cpic": CIBLE_CPIC, "multiple_depense": round(d_sp / CIBLE_CPIC, 2),
                     "cout_par_ic": round(d_sp / _ic, 2) if _ic else None}
if not DRY:
    json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)

log(f"=== done: {len(killed)} killed / {len(candidates)} candidats ===")

if DRY:
    raise SystemExit(0)   # [dry-run] ni snapshot ni écriture


def g(acts, t):
    for a in acts or []:
        if a["action_type"] == t: return float(a["value"])
    return 0.0
rows = []
for d in r.get("data", []):
    sp = float(d.get("spend", 0))
    if sp < 1: continue
    acts = d.get("actions", [])
    rows.append({"n": d["ad_name"], "sp": round(sp),
                 "ic": round(g(acts, "offsite_conversion.fb_pixel_initiate_checkout")),
                 "pur": round(g(acts, "offsite_conversion.fb_pixel_purchase")),
                 "fr": round(float(d.get("frequency", 0)), 2)})
rows.sort(key=lambda x: -x["sp"])
snap = {"label": OUT, "pulled_at": datetime.datetime.now().isoformat(),
        "tot_spend": sum(x["sp"] for x in rows), "tot_ic": sum(x["ic"] for x in rows),
        "tot_pur": sum(x["pur"] for x in rows), "rows": rows}
os.makedirs(SNAPDIR, exist_ok=True)
json.dump(snap, open(os.path.join(SNAPDIR, f"{OUT}.json"), "w"), ensure_ascii=False, indent=1)
log(f"  snapshot {OUT} sauvegardé (tot {snap['tot_spend']}$, {snap['tot_ic']} IC)")
