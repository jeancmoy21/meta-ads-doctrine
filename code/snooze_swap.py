#!/usr/bin/env python3
"""Exemple de countdown automatisé : édition de texte EN PLACE sur une seule ad
dédiée ("snooze ad"), plutôt que de multiplier les ads de compte à rebours.
On garde le même ad_id (un seul point de churn), et on swap la créative pour le
texte du jour. Les autres ads ne sont jamais touchées, leur learning reste intact.

Pensé pour être lancé par un scheduler local (launchd/cron), indépendant de
toute session Claude. Usage: snooze_swap.py <phase_key>
DRYRUN=1 -> build la créative et l'affiche, sans swap.

Config : éditez PHASES ci-dessous avec vos propres textes/timing, ou chargez-les
depuis un fichier JSON externe si vous préférez ne pas les committer dans le repo."""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m

SNOOZE_AD = os.environ.get("META_SNOOZE_AD_ID", "REPLACE_ME")
IMG_HASH = os.environ.get("META_SNOOZE_IMAGE_HASH", "REPLACE_ME")
LOG = os.path.expanduser(os.environ.get("META_JOB_LOG", "~/.meta_ads/snooze_swap.log"))
TITLES = ["On débute lundi", "Dernière chance"]
DESC = ["Exemple de description phase 1", "Exemple de description phase 2"]

def log(msg):
    line = f"{datetime.datetime.now().isoformat()} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def body(head, debut_line):
    return (f"{head}\n\n"
    "Exemple de corps de texte, à remplacer par votre propre copy.\n\n"
    f"{debut_line}\n\n"
    "Signature de la marque ici.")

# Remplacez les textes ci-dessous par les vôtres. 'utm' peut être un token court
# (repose sur META_LINK_BASE, voir meta_lib.resolve_link) ou une URL absolue complète.
PHASES = {
 "48h": {"utm": "batch-snooze48h", "budget": None,
   "body": body("MOINS DE 48H", "Exemple de ligne d'urgence phase 48h.")},
 "24h": {"utm": "batch-snooze24h", "budget": None,
   "body": body("MOINS DE 24H", "Exemple de ligne d'urgence phase 24h.")},
}

if len(sys.argv) != 2 or sys.argv[1] not in PHASES:
    print(__doc__)
    print(f"Phases disponibles: {', '.join(PHASES)}")
    raise SystemExit(2)

phase = sys.argv[1]
p = PHASES[phase]
dry = os.environ.get("DRYRUN") == "1"
log(f"== {phase} {'(DRYRUN)' if dry else ''} ==")
name = f"snooze-{phase}_inplace_{datetime.date.today().isoformat()}"
cid = m.make_static_creative(name, IMG_HASH, p["utm"], [p["body"]], TITLES, DESC)
log(f"  creative built {cid}")
if dry:
    log("  DRYRUN: pas de swap, pas de budget"); sys.exit(0)
r, err = m._post(SNOOZE_AD, {"creative": json.dumps({"creative_id": cid}), "access_token": m.token()})
log(f"  swap sur {SNOOZE_AD}: {'ERR '+str(err)[:160] if err else 'OK (ad reste ACTIVE, re-review)'}")
if p["budget"]:
    r2, e2 = m._post(m.ACCOUNT, {"daily_budget": p["budget"], "access_token": m.token()})
    log(f"  budget -> {p['budget']}: {'ERR '+str(e2)[:160] if e2 else 'ok'}")
log(f"== done {phase} ==")
