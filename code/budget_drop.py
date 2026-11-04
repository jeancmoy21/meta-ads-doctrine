#!/usr/bin/env python3
"""Exemple de job de baisse de budget automatisée (ex. fin de front-load un matin
de fermeture). Pensé pour être lancé par un scheduler local (launchd/cron),
indépendant de toute session Claude, voir meta-campaign-lifecycle.md, section
"Automatisation budget".

Usage: budget_drop.py <campaign_id> <target_daily_budget_cents>
Exemple: budget_drop.py 1234567890 100000   (baisse à 1 000$/jour)

Mode « surf » [rev. 2026-11] : delta de budget du matin selon l'écart entre le coût
réel par IC et `cible_cpic` (voir doctrines/meta-campaign-lifecycle.md §7).
Usage: budget_drop.py --surf <campaign_id> --cible-cpic N --cout-ic X --budget-jour B [--go]
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
    """Retourne (delta_min, delta_max) en fraction du budget (ex. 0.10, 0.20).
    Grille : écart < 10 % = +10 à +20 % ; 10 à 30 % = tenir ; > 30 % = -10 à -20 %."""
    ecart = (cout_ic - cible_cpic) / cible_cpic
    if ecart < 0.10:
        return (0.10, 0.20)
    if ecart <= 0.30:
        return (0.0, 0.0)
    return (-0.20, -0.10)

def _arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None

if "--surf" in sys.argv:
    pos = [a for i, a in enumerate(sys.argv[1:], 1)
           if not a.startswith("--") and sys.argv[i - 1] not in ("--cible-cpic", "--cout-ic", "--budget-jour")]
    try:
        cible, cout, budget = (float(_arg(k)) for k in ("--cible-cpic", "--cout-ic", "--budget-jour"))
        CAMPAIGN = pos[0]
    except (TypeError, ValueError, IndexError):
        sys.exit("ERREUR: --surf exige <campaign_id>, --cible-cpic, --cout-ic et --budget-jour (nombres, $)")
    lo, hi = surf_delta(cible, cout)
    ecart = (cout - cible) / cible
    # Valeur retenue = milieu de la plage (arrondi au dollar).
    nouveau = round(budget * (1 + (lo + hi) / 2))
    print(f"surf: coût/IC {cout:.0f}$ vs cible {cible:.0f}$ (écart {ecart:+.0%}) -> delta {lo:+.0%} à {hi:+.0%}; "
          f"budget {budget:.0f}$ -> {nouveau}$/jour")
    if "--go" not in sys.argv:
        print("  (aucune écriture : ajouter --go pour appliquer, après approbation)")
        raise SystemExit(0)
    r, err = m._post(CAMPAIGN, {"daily_budget": nouveau * 100, "access_token": m.token()})
    log(f"== surf -> {nouveau}$/jour: {'ERR '+str(err)[:160] if err else 'OK'} ==")
    raise SystemExit(1 if err else 0)

if len(sys.argv) != 3:
    print(__doc__); raise SystemExit(2)

CAMPAIGN = sys.argv[1]
TARGET = int(sys.argv[2])  # cents

r, err = m._post(CAMPAIGN, {"daily_budget": TARGET, "access_token": m.token()})
log(f"== budget drop -> {TARGET} cents: {'ERR '+str(err)[:160] if err else 'OK'} ==")
v, _ = m._get(CAMPAIGN, {"fields": "name,daily_budget,status"})
log(f"  verify: {v}")
