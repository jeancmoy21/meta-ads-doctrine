#!/usr/bin/env python3
"""Exemple de job de baisse de budget automatisée (ex. fin de front-load un matin
de fermeture). Pensé pour être lancé par un scheduler local (launchd/cron),
indépendant de toute session Claude — voir meta-campaign-lifecycle.md, section
"Automatisation budget".

Usage: budget_drop.py <campaign_id> <target_daily_budget_cents>
Exemple: budget_drop.py 1234567890 100000   (baisse à 1 000$/jour)"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m

if len(sys.argv) != 3:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1]
TARGET = int(sys.argv[2])  # cents
LOG = os.path.expanduser(os.environ.get("META_JOB_LOG", "~/.meta_ads/budget_drop.log"))

def log(msg):
    line = f"{datetime.datetime.now().isoformat()} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

r, err = m._post(CAMPAIGN, {"daily_budget": TARGET, "access_token": m.token()})
log(f"== budget drop -> {TARGET} cents: {'ERR '+str(err)[:160] if err else 'OK'} ==")
v, _ = m._get(CAMPAIGN, {"fields": "name,daily_budget,status"})
log(f"  verify: {v}")
