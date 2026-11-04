# Doctrine : Cycle de vie d'une campagne Meta

*Cadre opérationnel pour la GESTION D'UNE CAMPAGNE Meta dans le temps, de la phase de croissance jusqu'à la fermeture du panier. Complète `andromeda-strategy.md` (qui couvre le diagnostic créatif). Lire les deux avant d'agir sur une campagne en cours.*

Andromeda répond à « quel créatif builder ». Cette doctrine répond à « quoi faire de la campagne maintenant, à ce stade du cycle ». Les deux ne se croisent pas : la diversité sémantique reste la loi pour ce qu'on lance ; ici on parle de timing, d'allocation, de kill/réactivation et de wind-down.

**Une campagne par événement à date butoir [rev. 2026-11].** Hors événement, presque jamais de nouvelle campagne de prospection : on ajoute des packs neufs (nouveaux ad sets) à la campagne existante. Structure complète : `andromeda-strategy.md`, « Structure de campagne ».

**Termes canoniques** (mêmes mots dans les agents et les scripts) : `cible_cpic` = coût cible par IC de la campagne, champ obligatoire du manifeste de build ; `fenetre_min` = le plus grand de 3 jours ou du temps nécessaire pour 10 IC au coût cible ; seuil de kill relatif = 2x / 3x (§2) ; plafond par paliers (`andromeda-strategy.md`, SOP plafonnement).

---

## 1. Harvest mode en fin de campagne

À l'approche de la fermeture du panier, on bascule de la croissance à la récolte.

- On concentre le budget sur les **converteurs prouvés**, pas sur l'exploration.
- On **kill les ads qui brûlent** au seuil de kill relatif du §2 (2x / 3x `cible_cpic`, après `fenetre_min`), jamais à un montant fixe. Quand le volume le permet, le même seuil se lit aussi sur l'étage amont (vue de la landing page, lead brut ou IC) pour réagir plus vite [rev. 2026-11]. En harvest seulement, « high CTR + 0 conversion » se tue au seuil au lieu de se réparer (§2).
- On **ne lance pas d'angles neufs spéculatifs** : une nouvelle poche sémantique n'a plus le temps de mûrir avant la deadline, ni de passer `fenetre_min`. On consolide ce qui marche.
- CBO **redistribue automatiquement** le budget des ads coupées vers les gagnantes. Couper une perdante = nourrir une gagnante, sans toucher au budget campagne.
- **À l'échéance : budget agressif et ciblage à fond des clients existants et des engagés**, avec relance des IC par courriel et SMS en parallèle (`email-launch.md`) [rev. 2026-11].

Distinction nette avec Andromeda : en phase de croissance, on diversifie et on tolère l'immaturité. En harvest, on resserre. La SOP plafonnement s'applique en croissance comme en harvest ; en harvest, on ne lance plus de pack neuf qui ne pourra pas finir sa `fenetre_min` avant la fermeture [rev. 2026-11].

---

## 2. Kill + backtrack (seuil relatif, fenêtre minimale, lag d'attribution pixel)

### Seuil de kill relatif [rev. 2026-11]

Deux paliers sur la dépense cumulée de l'ad (ou de l'ad set) depuis son lancement, après `fenetre_min` :
1. dépense ≥ 2 × `cible_cpic` et 0 IC : kill.
2. dépense ≥ 3 × `cible_cpic` et coût réel par IC > 1,5 × `cible_cpic` (c'est-à-dire plus de 50 % au-dessus de la cible) : kill.

Sous 2 × `cible_cpic` dépensés, jamais de kill. **La campagne tient sa cible** quand son coût réel par IC est ≤ 1,10 × `cible_cpic` (constante `TOLERANCE_CIBLE` de `meta_lib.py`, paramètre ajustable). Dans les deux cas, la campagne est jugée d'abord : si la campagne entière tient sa cible, une ad à plus de 30 % de la dépense n'est pas tuée mais plafonnée (`andromeda-strategy.md`, SOP plafonnement). Ordre de jugement : la campagne avant l'ad set, l'ad set avant l'ad. Un kill à montant fixe (ex. 150 $) est à proscrire : à 150 $ dépensés, une ad parfaitement à une cible de 250 $ est à 0 IC 55 % du temps [calcul, loi de Poisson].

### Fenêtre minimale [rev. 2026-11]

Aucun kill avant `fenetre_min` = le plus grand de 3 jours ou du temps nécessaire pour 10 IC au coût cible. **`fenetre_min` s'ancre sur l'objet jugé** : `created_time` de l'ad set pour un ad set, `created_time` de l'ad pour une ad, date de lancement pour la campagne. Un pack neuf dans une campagne qui roule a donc sa propre fenêtre [rev. 2026-11]. Exemples [calcul] : 1 000 $/jour à 100 $ de cible = 3 jours ; 167 $/jour (5 k$/mois) à 150 $ = 9 jours. Jamais de jugement sur un jour, un matin ou un lendemain d'événement. Les lectures quotidiennes de l'étage amont restent permises, sans action. Fenêtres empilées pour lire une tendance : 14 jours, 7, 3, puis la veille, jamais la veille seule.

### Kill switches en cascade [rev. 2026-11]

- Étages : vue de la landing page, lead brut ou IC, achat. Les seuils par étage se tirent des ratios réels du compte, avec la même fenêtre d'attribution pour fixer le seuil et pour juger.
- **Jamais de kill sur CPM, CPC, CTR ou ViewContent** : Meta n'optimise pas l'ad individuelle isolément. Le KPI se juge à la campagne avant l'ad.
- **Dud** : une ad (ou un ad set) qui franchit le seuil de kill relatif sans être l'objet dominant de son niveau. La dépense collée au minimum n'est pas le critère, c'est un indice de lecture (§8). Seuls les duds se coupent quand la campagne tient sa cible.
- **« High CTR + 0 conversion »** = bonne accroche, mauvaise poche ou mauvais relais. En croissance, on répare (body, offre, CTA) avant de jeter ; en harvest, kill au seuil relatif.

### Backtrack

Le pixel Meta retarde les conversions. Un kill peut donc être prématuré si des conversions différées rentrent après coup.

- À chaque kill, **enregistrer l'ad dans un registre** (`killed_ads.json`) avec le nombre de paiements initiés au moment du kill, la `cible_cpic` de la campagne, le multiple de dépense atteint et le coût réel par IC au moment du verdict.
- À chaque re-check, si des conversions différées rentrent (`IC_actuel - IC_au_kill >= seuil`, ex. 2), **RÉACTIVER l'ad**.
- **Métrique de LECTURE = paiement initié** (`offsite_conversion.fb_pixel_initiate_checkout`) croisé avec le CRM, PAS l'achat pixel (`offsite_conversion.fb_pixel_purchase`) qui lag davantage. Elle est distincte de l'événement d'OPTIMISATION de l'ad set (`meta-tracking-doctrine.md`, vérités dures 0 à 2) [rev. 2026-11].

**Façon canonique (ne plus re-coder) :** deux fonctions dans `meta_lib.py` encapsulent kill et backtrack. Toujours passer par elles plutôt que de réécrire la logique inline.
- `record_kill(registry_path, ad_name, ad_id, ic_at_kill, by)` : pause l'ad (PAUSED) et l'inscrit au registre. Idempotent, crée le fichier si absent.
- `check_backtrack(registry_path, campaign_id, gained_threshold)` : pull l'IC actuel par ad, réactive (ACTIVE) toute ad dont `IC_actuel - ic_at_kill >= gained_threshold`, la retire du registre, retourne les réactivées.
- Registre par défaut : `killed_ads.json` (constante `meta_lib.KILL_REGISTRY`, à pointer vers votre propre chemin de données).
- **Format du registre (figé)** : `{ ad_name: {"ad_id", "ic_at_kill", "killed_at", "by"} }`, plus, pour les kills de `evening_kill.py`, `cible_cpic`, `multiple_depense` et `cout_par_ic`. Compat ascendante : les vieilles entrées sans `ad_id` sont re-résolues par nom via `{campaign}/ads`.
- `evening_kill.py` reste le job du soir (logs + snapshots). Il applique le seuil de kill relatif (`2 * cible_cpic`, puis `3 * cible_cpic` à plus de 50 % d'écart), n'agit qu'après `fenetre_min`, juge la campagne d'abord et ne tue jamais la no 1 d'une campagne à la cible [rev. 2026-11]. Le seuil fixe en dollars de l'ancienne version est retiré.

---

## 3. Pivot messaging de fermeture

À la fin, on retourne l'objection « j'ai manqué le bateau » en invitation.

- « Moins de 72h » devient « Dernière chance pour s'inscrire ».
- Quand le programme est commencé : « C'est commencé, mais il n'est pas trop tard pour embarquer ».
- C'est un pivot de MESSAGE sur les ads existantes prouvées (via nouvelle créative, voir section 4), pas un nouvel angle spéculatif.
- **En fermeture, l'offre ou la date est en surimpression sur chaque visuel** : une part de l'audience ne lit ni le primary text ni le headline. La lettre longue signée reste le primary text par défaut [rev. 2026-11].

---

## 4. Refresh visuel = NOUVELLE AD, jamais un swap d'image

Une créative Meta est **immuable**. Changer l'image d'une ad existante crée une nouvelle créative donc un nouveau post.

- On **PERD la preuve sociale** accumulée (likes, commentaires, partages) et l'ad **repart en learning**.
- Donc pour un refresh visuel : **lancer une NOUVELLE ad** et laisser l'ancienne (prouvée) rouler en parallèle. CBO arbitrera.
- **Recréer ou déplacer une ad existante : la relancer par son post ID** pour garder la preuve sociale. Ça ne protège pas toujours [rev. 2026-11].
- **Fréquence, seuils par fenêtre et par segment [rev. 2026-11]** :
  - prospection : 2,2 à 2,5 sur 7 jours = fatigue = candidat refresh (nouvelle ad, pas swap) ;
  - retargeting : alerte à 10 sur 7 jours et à 15 sur 30 jours ; sous ces seuils, la répétition est normale et se gère par la variété ;
  - segment new au-dessus d'environ 5 sur 7 jours : élargir (pack d'intérêt adjacent, `andromeda-strategy.md`) et produire du neuf.

---

## 5. Wind-down du code promo

Quand le code promo expire :

- Retirer **toutes les mentions** du code des textes de **toutes** les ads.
- Retirer le `promotional_metadata` des créatives.
- Couper l'ad promo dédiée s'il y en a une.

**Une offre doit tenir dans l'écart de profit [rev. 2026-11].** Un rabais déplace le seuil de rentabilité ; il doit être battu par un gain de volume de 30 à 40 % et plus pour valoir la peine. Le calcul se fait avant de lancer un code promo.

---

## 6. Cohérence copy / visuel obligatoire

Le texte (body) doit toujours être synchronisé avec le messaging du visuel ET la date réelle.

- Si le visuel dit « Dernière chance / Lundi », le body ne peut PAS dire « Moins de 72h / ferme dimanche ».
- À chaque pivot de fermeture ou wind-down, repasser sur chaque ad pour aligner body, visuel, surimpression (§3) et date.

---

## 7. Automatisation budget (front-load, grille surf, drop)

- Budget **front-loadé** pendant la campagne, **baissé automatiquement** le matin de fermeture. Le front-load est un plancher, le drop de fermeture reste (pauser quand on ne peut plus convertir) [rev. 2026-11].
- Mécanisme suggéré : job planifié local (ex. `launchd` sur Mac, `cron` sur Linux) déclenché le matin voulu.
- **Limite headless** : un job autonome peut AGIR en pur script (via `meta_lib`) mais ne peut généralement pas notifier facilement en headless si votre notification dépend d'un client connecté. Doctrine : **agir en autonome, rapporter en session**.

**Grille surf, lecture du matin [rev. 2026-11].** Grille unique, lue une fois par matin sur le coût réel par IC de la campagne (croisé avec le CRM) contre `cible_cpic`, après `fenetre_min` de la campagne :

| Coût réel par IC | Delta de budget du jour |
|:---|:---|
| > 1,30 × cible | baisse de 10 à 20 % |
| 1,10 à 1,30 × cible | tenir |
| 0,70 à 1,10 × cible | +10 à +20 % |
| 0,50 à 0,70 × cible | +20 à +40 % |
| < 0,50 × cible | +50 à +100 % |

- **Jamais plus d'un palier par jour.** Le front-load et le drop du calendrier restent prioritaires sur la grille les jours où ils s'appliquent.

- **Méthode du delta** : l'écart entre le résultat réel et le résultat à la cible se dépense sans risque ; il sert à choisir où se placer dans la fourchette de la case. Exemple [calcul] : CBO à 1 000 $/jour, 10 IC par jour, cible 150 $ : 10 IC valent 1 500 $ à la cible, donc +500 $ (+50 %) ; mais le coût réel de 100 $ = 0,67 × cible tombe dans la case +20 à +40 %, la hausse est donc plafonnée par la case (+40 %, soit +400 $). Le delta sert à se placer dans la fourchette, jamais à en sortir.
- Chaque rapport `meta-analyse` du matin donne le coût réel par IC, la case de la grille et le delta.
- `budget_drop.py --surf` lit cette grille et exige `--campaign <id>` ; sans `--go`, rien n'est écrit. Le `--go` se lance sur approbation explicite du propriétaire du compte.

---

## 8. Lancement d'un pack : minimums, maximums, duds [rev. 2026-11]

- **Pack neuf** : 4 à 8 ads dans un nouvel ad set ; un seul événement d'optimisation par CBO.
- **Minimum sur chaque nouveau pack : 1x `cible_cpic`**, gardé 7 jours au maximum, puis retiré. **Somme des minimums ≤ 20 % du budget de la campagne** (règle qui règle une grande part des problèmes de dépense mal répartie).
- **Pas de minimum sous environ 200 $/jour de CBO**, ni sur un pack d'intérêt, ni plusieurs packs sous minimum à la fois à petit budget.
- **Maximums en %, minimums en $**. Le maximum en % est l'outil de la SOP plafonnement.
- **Un gagnant dépense au-dessus de son minimum** ; un ad set collé à son minimum avec un coût par IC à 2x la cible après 7 jours est un indice de dud à lire, pas un verdict : le verdict suit la définition du §2.
- **Un minimum protège aussi** une ad très rentable qui dépense peu, ou un contenu à droits limités (témoignage à durée limitée) : minimum une semaine, puis hausse.
- Un pack lancé sans hausser la CBO prend sa dépense aux anciens : prévoir la hausse au lancement.

---

## 9. Coexistence evergreen et événement [rev. 2026-11]

- **Un événement vit dans sa propre campagne CBO**, full funnel, packs lancés d'entrée par offre et par date. L'evergreen continue, réduit de 50 à 90 % pendant l'événement (ex. 500 $/jour devient 100 $ evergreen et 400 $ événement).
- **Pas de « réchauffement » avant l'ouverture** : la créa de l'événement sort le jour où l'offre commence.
- **Le jour 1 d'une ouverture annoncée est faussé par la demande refoulée** : `meta-analyse` l'exclut des moyennes. Un événement draine les segments engaged et existing ; la baisse qui suit n'est pas un bris.
- **Recycler les gagnantes des lancements passés** ; seul l'habillage d'offre change.

---

## 10. Couloirs d'audience [rev. 2026-11]

- **Retargeting fondu dans la prospection par défaut.** Un ad set de remarketing séparé n'est plus le défaut : on le sépare seulement si la part engaged déborde (alerte vers 50 %) ou pour contrôler la dépense en fermeture.
- **En prospection, on n'exclut que les inscrits à l'événement (`registered`) et les acheteurs (`buyers`).** La règle dure « exclusion des inscrits dans chaque ad set » reste entière. Aucune exclusion d'engagement large : elle fait monter la fréquence et vide le milieu du funnel.
- **La relance des IC non payés passe au courriel et au SMS** (`email-launch.md`), pas à un ad set Meta dédié.
- La part par segment (new, engaged, existing) se lit dans chaque rapport (`meta-tracking-doctrine.md`).

---

## 11. Diagnostic d'une chute [rev. 2026-11]

1. **L'offre et la page d'abord, les ads ensuite** : les ads ne sauvent pas une mauvaise offre. Hiérarchie produit, offre, ads, page de destination. `meta-analyse` vérifie la conversion de la landing page avant de recommander du créatif.
2. **Ventilation par ventilation, avant contre après** : campagne, ad set, ad, segment, âge, puis période. La dépense s'est presque toujours déplacée quelque part. Prévoir 45 min à 4 h.
3. **Un changement à la fois** : ne pas toucher la landing page ou le checkout pendant que le créatif change.

---

## Ordre d'intervention en fin de campagne (checklist)

1. Passer en harvest : kill les brûleuses au seuil de kill relatif (2x `cible_cpic` à 0 IC, 3x à plus de 50 % d'écart), après `fenetre_min`, campagne jugée d'abord ; laisser CBO redistribuer.
2. Enregistrer chaque kill dans `killed_ads.json` avec l'IC au moment du kill, `cible_cpic`, le multiple de dépense et le coût par IC.
3. Re-check périodique : réactiver les ads dont l'IC différé a rattrapé le seuil.
4. Pivot messaging de fermeture sur les gagnantes (nouvelle créative), offre ou date en surimpression sur chaque visuel.
5. Wind-down promo le jour de l'expiration (textes + metadata + ad dédiée).
6. Refresh anti-fatigue (prospection : fréquence 2,2 à 2,5 sur 7 jours) = nouvelles ads, anciennes laissées en parallèle.
7. Vérifier la cohérence copy/visuel/date sur chaque ad touchée.
8. Drop budget le matin de fermeture (job planifié), rapporter en session.

Métrique de lecture partout : paiement initié croisé avec le CRM (l'événement d'optimisation est une autre question, `meta-tracking-doctrine.md`).
