#!/usr/bin/env python3
"""Exemple de job de baisse de budget automatisée (ex. fin de front-load un matin
de fermeture). Pensé pour être lancé par un scheduler local (launchd/cron),
indépendant de toute session Claude, voir meta-campaign-lifecycle.md, section
"Automatisation budget".

Usage: budget_drop.py <campaign_id> <target_daily_budget_cents>
Exemple: budget_drop.py 1234567890 100000   (baisse à 1 000$/jour)

Mode « surf » [rev. 2026-11] : grille unique, lue sur le coût réel par IC contre `cible_cpic`,
un palier par jour (voir doctrines/meta-campaign-lifecycle.md §7) :
  ratio > 1,30 : baisse de 10 à 20 % ; 1,10 à 1,30 inclus : tenir ; 0,70 à < 1,10 : +10 à +20 % ;
  0,50 à < 0,70 : +20 à +40 % ; < 0,50 : +50 à +100 %.
Usage: budget_drop.py --surf --campaign <id> --cible-cpic N --cout-ic X --budget-jour B [--go]
Sans --go : affiche le delta et n'écrit RIEN. Le mode historique (sans --surf) est inchangé."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_lib as m

LOG = os.path.expanduser(os.environ.get("META_JOB_LOG", "~/.meta_ads/budget_drop.log"))

def log(msg):
    line = f"{datetime.datetime.now().isoformat()} {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f: f.write(line + "\n")

def surf_delta(cible_cpic, cout_ic):
    """Retourne (delta_min, delta_max) en fraction du budget (ex. 0.10, 0.20)."""
    ratio = cout_ic / cible_cpic
    if ratio > 1.30:
        return (-0.20, -0.10)
    if ratio >= 1.10:
        return (0.0, 0.0)
    if ratio >= 0.70:
        return (0.10, 0.20)
    if ratio >= 0.50:
        return (0.20, 0.40)
    return (0.50, 1.00)

def _arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else None

if "--surf" in sys.argv:
    camp = _arg("--campaign")
    if not camp or camp.startswith("--"):
        sys.exit("ERREUR: --surf exige --campaign <id> (aucun id en dur)")
    try:
        cible, cout, budget = (float(_arg(k)) for k in ("--cible-cpic", "--cout-ic", "--budget-jour"))
    except (TypeError, ValueError):
        sys.exit("ERREUR: --surf exige --cible-cpic, --cout-ic et --budget-jour (nombres, $)")
    lo, hi = surf_delta(cible, cout)
    ratio = cout / cible
    # Valeur retenue = milieu de la plage (arrondi au dollar).
    nouveau = round(budget * (1 + (lo + hi) / 2))
    print(f"surf: campagne {camp}, coût/IC {cout:.0f}$ vs cible {cible:.0f}$ (ratio {ratio:.2f}) -> "
          f"delta {lo:+.0%} à {hi:+.0%}; budget {budget:.0f}$ -> {nouveau}$/jour")
    if "--go" not in sys.argv:
        print("  (aucune écriture : ajouter --go pour appliquer, après approbation)")
        raise SystemExit(0)
    r, err = m._post(camp, {"daily_budget": nouveau * 100, "access_token": m.token()})
    log(f"== surf {camp} -> {nouveau}$/jour: {'ERR '+str(err)[:160] if err else 'OK'} ==")
    raise SystemExit(1 if err else 0)

if len(sys.argv) != 3:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1]
TARGET = int(sys.argv[2])  # cents

r, err = m._post(CAMPAIGN, {"daily_budget": TARGET, "access_token": m.token()})
log(f"== budget drop -> {TARGET} cents: {'ERR '+str(err)[:160] if err else 'OK'} ==")
v, _ = m._get(CAMPAIGN, {"fields": "name,daily_budget,status"})
log(f"  verify: {v}")
