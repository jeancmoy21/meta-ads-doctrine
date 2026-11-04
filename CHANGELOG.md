# Changelog

Les règles amendées portent la marque `[rev. 2026-11]` dans les doctrines, les agents et le code.

## 2026-11

Révision inspirée de la formation « The Facebook Ads Blueprint » de Sam Piliero (Skool), 2026, confrontée à la doctrine existante. Tout le contenu est reformulé ; aucun matériel de la formation n'est reproduit.

### Doctrine

- Seuil de kill relatif : 2x `cible_cpic` à 0 IC, 3x à plus de 50 % d'écart ; campagne jugée avant l'ad set, l'ad set avant l'ad. Remplace le seuil fixe en dollars.
- Fenêtre minimale `fenetre_min` (le plus grand de 3 jours ou du temps pour 10 IC au coût cible) avant tout kill ; le 48 h devient une hypothèse de fatigue.
- SOP plafonnement (plafond de dépense par paliers de 10 à 20 points sur l'ad ou l'ad set dominant) remplace le cycle de pivot forcé ; kill de la no 1 seulement si la campagne entière rate sa cible.
- Jamais de duplication d'ad set : les nouvelles ads vont dans un nouvel ad set de la même campagne (pack neuf de 4 à 8 ads).
- Quota créatif max(2 ads par semaine, 1 ad par 10 k$ mensuels) remplace le quota fixe de messages par mois ; retrait des CPM préférentiels.
- Hook-swap v2 : message prouvé (au moins 5 % de la dépense, à la cible ou proche) a droit à 3 à 6 itérations dans un pack `iteration` séparé ; plafond de 2 ads gardé pour un message `nouveau`.
- 1 ou 2 avatars simultanés partout, lancement échelonné ; le gagnant est creusé avant d'en ouvrir un autre.
- Funnel défini par la conversion demandée (achat = bas, lead = haut) ; statics par défaut en achat, vidéo par défaut en lead gen.
- Étage objection : chaque message vise le haut ou le bas du funnel, jamais le milieu.
- Pack d'intérêt adjacent seulement si la fréquence du segment new dépasse environ 5 sur 7 jours ou si la portée plafonne.
- Dérogation ponctuelle : pack de test géo resserrée avec restriction de langue, côte à côte avec le défaut.
- Douleur = outil ponctuel (un angle par batch au plus), gain par défaut.
- Fréquence par fenêtre et par segment : prospection 2,2 à 2,5 sur 7 jours ; retargeting 10 sur 7 jours et 15 sur 30 jours.
- Retargeting fondu dans la prospection par défaut ; en prospection, on n'exclut que les inscrits et les acheteurs.
- Grille surf et méthode du delta pour la lecture du matin ; `budget_drop.py` gagne un mode « surf » sans écriture par défaut.
- Lancement d'un pack : minimum 1x `cible_cpic` sur 7 jours, somme des minimums ≤ 20 % du budget, maximums en %, minimums en $.
- Coexistence evergreen et événement : campagne dédiée à l'événement, evergreen réduit de 50 à 90 %.
- Diagnostic d'une chute : offre et page d'abord, ventilation avant contre après, un changement à la fois.
- Surimpression de l'offre ou de la date sur chaque visuel en fermeture.
- Métrique de LECTURE (IC croisé avec le CRM) distincte de l'événement d'OPTIMISATION (l'événement le plus profond à 10 conversions par semaine ou plus).
- `cible_cpic` obligatoire au manifeste, dérivée d'un seuil de rentabilité combiné.
- Segments d'audience (new, engaged, existing) et colonne incrémentale en lecture obligatoire, sans décision.
- Qualification des leads : question disqualifiante tôt, disqualifiés non pixelés, pas d'Instant Forms par défaut.
- Piège UTM et post ID, refus des enhancements visuels Advantage+, multi-advertiser désactivé en prospection.
- Nouvelle doctrine `doctrines/email-launch.md` : flows de courriel et SMS autour d'un lancement.

### Agents

- `meta-analyse` : seuil relatif, `fenetre_min`, duds, fréquence par fenêtre, segments, surf du matin.
- `meta-creation` : type de pack, `cible_cpic`, avatars, événement d'optimisation, retargeting fondu.
- `meta-deploy` : plafond d'ad set, ad depuis un post ID, enhancements visuels refusés, pas de duplication d'ad set.

### Code

- `meta_lib.py` : `fenetre_min`, `fenetre_ecoulee`, `seuil_kill_relatif`, `campagne_tient_cible`, `palier_plafond`, `evaluer_cascade`, `make_creative_from_post`, `create_ad_from_post`, `refuse_visual_enhancements`, `set_adset_spend_cap`.
- `validate_manifest.py` : `cible_cpic` obligatoire, pack de 4 à 8 ads, somme des minimums, un seul événement d'optimisation par CBO, avatars, rôles d'exclusion, plafonds par message et par asset.
- `evening_kill.py` : seuil relatif et cascade à la place du seuil fixe ; options `--dry-run`, `--fixture`.
- `budget_drop.py` : mode `--surf`.
- `code/tests/` : tests des règles de seuil, de fenêtre et de cascade.
