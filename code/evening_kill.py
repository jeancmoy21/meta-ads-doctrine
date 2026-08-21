#!/usr/bin/env python3
"""Exemple de re-check autonome (ex. le soir après une redistribution de budget) :
kill les money-pits révélés depuis une baseline, avec whitelist et journal.
Compare le pull actuel à un snapshot baseline (produit par pull_insights.py).

Voir meta-campaign-lifecycle.md section 2 (kill + backtrack) et
meta_lib.record_kill / meta_lib.check_backtrack, qui encapsulent cette même
logique proprement — ce script montre la version "à la main", conservée ici
comme référence historique de ce que ces helpers remplacent.

Usage: evening_kill.py <campaign_id> <baseline_label> [output_label]
  baseline_label : nom du snapshot de référence (ex. 'samedi_pm')
  output_label   : nom du snapshot produit par ce run (défaut 'evening_check')

Config par variables d'environnement :
  META_KILL_MIN_SPEND       $ brûlés depuis la baseline avant de considérer un kill (défaut 150)
  META_KILL_BACKTRACK_IC    IC gagnés en différé depuis un kill -> on rouvre (défaut 2)
  META_KILL_WHITELIST       noms d'ads à ne jamais toucher, séparés par des virgules
"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m

if len(sys.argv) < 3:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1]
BASE = sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else "evening_check"

SNAPDIR = os.path.expanduser(os.environ.get("META_SNAPSHOT_DIR", "~/.meta_ads/snapshots"))
LOG = os.path.expanduser(os.environ.get("META_JOB_LOG", "~/.meta_ads/evening_kill.log"))
PM = os.path.join(SNAPDIR, f"{BASE}.json")
REG = m.KILL_REGISTRY
MIN_SPEND = float(os.environ.get("META_KILL_MIN_SPEND", "150"))
BACKTRACK_IC = float(os.environ.get("META_KILL_BACKTRACK_IC", "2"))
WHITELIST = {n.strip() for n in os.environ.get("META_KILL_WHITELIST", "").split(",") if n.strip()}


def log(msg):
    line = f"{datetime.datetime.now().isoformat()} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")


log("=== evening re-check start ===")

pm = {r["n"]: r for r in json.load(open(PM))["rows"]}

flds = "ad_name,spend,frequency,actions"
r, err = m._get(f"{CAMPAIGN}/insights", {"level": "ad", "fields": flds, "limit": 200})
if err:
    log(f"ERR insights {err}"); raise SystemExit(1)


def ic(acts):
    for a in acts or []:
        if a["action_type"] == "offsite_conversion.fb_pixel_initiate_checkout":
            return float(a["value"])
    return 0.0


now = {d["ad_name"]: {"sp": float(d.get("spend", 0)), "ic": ic(d.get("actions")),
                      "fr": float(d.get("frequency", 0))} for d in r.get("data", [])}

ra, _ = m._get(f"{CAMPAIGN}/ads", {"fields": "id,name,status,effective_status", "limit": 200})
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
    if gained >= BACKTRACK_IC and ids.get(name):
        rr, e = m._post(ids[name], {"status": "ACTIVE", "access_token": m.token()})
        ok = "OK" if not e else f"ERR {str(e)[:80]}"
        log(f"  REACTIVATE {name[:46]:46} (+{gained:.0f} IC différés) -> {ok}")
        if not e:
            reg.pop(name, None)
json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)

candidates = []
for name, adid in live.items():
    if name in WHITELIST:
        continue
    base = pm.get(name, {"sp": 0, "ic": 0})
    cur = now.get(name)
    if not cur:
        continue
    d_sp = cur["sp"] - base["sp"]
    d_ic = cur["ic"] - base["ic"]
    log(f"  live {name[:46]:46} depuis baseline: +{d_sp:6.0f}$  +{d_ic:.0f}IC  freq={cur['fr']:.2f}")
    if d_sp >= MIN_SPEND and d_ic == 0:
        candidates.append((name, adid, d_sp, cur["fr"]))

killed = []
for name, adid, d_sp, fr in candidates:
    rr, e = m._post(adid, {"status": "PAUSED", "access_token": m.token()})
    ok = "OK" if not e else f"ERR {str(e)[:80]}"
    log(f"  KILL {name[:46]:46} (+{d_sp:.0f}$ depuis baseline, 0 IC) -> {ok}")
    if not e:
        killed.append(name)
        reg[name] = {"ic_at_kill": now.get(name, {}).get("ic", 0),
                     "killed_at": datetime.datetime.now().isoformat(), "by": "evening-check"}
json.dump(reg, open(REG, "w"), ensure_ascii=False, indent=1)

log(f"=== done: {len(killed)} killed / {len(candidates)} candidats ===")

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
