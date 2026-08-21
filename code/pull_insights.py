#!/usr/bin/env python3
"""Pull insights par ad d'une campagne depuis une date de départ.
Sort un tableau texte + dump JSON. Sauvegarde un snapshot horodaté dans
un dossier de snapshots (défaut ~/.meta_ads/snapshots/).

Usage: pull_insights.py <campaign_id> <since:YYYY-MM-DD> <until:YYYY-MM-DD> [label]
  label ex: 'samedi', 'dimanche' -> nom du fichier snapshot"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m

if len(sys.argv) < 4:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1]
SINCE = sys.argv[2]
UNTIL = sys.argv[3]
label = sys.argv[4] if len(sys.argv) > 4 else "snapshot"

SNAPDIR = os.path.expanduser(os.environ.get("META_SNAPSHOT_DIR", "~/.meta_ads/snapshots"))
os.makedirs(SNAPDIR, exist_ok=True)

flds = "ad_name,impressions,reach,frequency,spend,cpm,actions,inline_link_clicks,ctr"
r, err = m._get(f"{CAMPAIGN}/insights",
                {"level": "ad", "fields": flds,
                 "time_range": json.dumps({"since": SINCE, "until": UNTIL}), "limit": 200})
if err:
    print("ERR", err); raise SystemExit(1)

def g(acts, t):
    for a in acts or []:
        if a["action_type"] == t: return float(a["value"])
    return 0.0

rows = []
for d in r.get("data", []):
    sp = float(d.get("spend", 0))
    if sp < 1: continue
    acts = d.get("actions", [])
    ic = g(acts, "offsite_conversion.fb_pixel_initiate_checkout")
    pur = g(acts, "offsite_conversion.fb_pixel_purchase")
    rows.append({
        "n": d["ad_name"], "sp": round(sp), "imp": int(d["impressions"]),
        "fr": round(float(d.get("frequency", 0)), 2), "cpm": round(float(d.get("cpm", 0))),
        "ctr": round(float(d.get("ctr", 0)), 1), "clk": int(d.get("inline_link_clicks", 0)),
        "ic": round(ic), "pur": round(pur), "cpic": round(sp / ic) if ic else 0,
    })
rows.sort(key=lambda x: -x["sp"])
tot_sp = sum(x["sp"] for x in rows); tot_ic = sum(x["ic"] for x in rows); tot_pur = sum(x["pur"] for x in rows)

snap = {"label": label, "pulled_at": datetime.datetime.now().isoformat(),
        "tot_spend": tot_sp, "tot_ic": tot_ic, "tot_pur": tot_pur, "rows": rows}
path = os.path.join(SNAPDIR, f"{label}.json")
with open(path, "w") as f: json.dump(snap, f, ensure_ascii=False, indent=1)

print(f"TOTAL spend={tot_sp}$  init_checkout={tot_ic}  purchase={tot_pur}  CPIC={round(tot_sp/tot_ic) if tot_ic else 0}$")
print(f'{"AD":46}{"sp":>6}{"%":>4}{"fr":>5}{"cpm":>5}{"ctr":>5}{"clk":>5}{"IC":>4}{"pur":>4}{"CPIC":>6}')
for x in rows:
    print(f'{x["n"][:46]:46}{x["sp"]:>6}{round(100*x["sp"]/tot_sp):>4}{x["fr"]:>5}{x["cpm"]:>5}{x["ctr"]:>5}{x["clk"]:>5}{x["ic"]:>4}{x["pur"]:>4}{x["cpic"]:>6}')
print(f"\nSnapshot sauvegardé: {path}")
