# Doctrine : Cycle de vie d'une campagne Meta

*Cadre opérationnel pour la GESTION D'UNE CAMPAGNE Meta dans le temps, de la phase de croissance jusqu'à la fermeture du panier. Complète `andromeda-strategy.md` (qui couvre le diagnostic créatif). Lire les deux avant d'agir sur une campagne en cours.*

Andromeda répond à « quel créatif builder ». Cette doctrine répond à « quoi faire de la campagne maintenant, à ce stade du cycle ». Les deux ne se croisent pas : la diversité sémantique reste la loi pour ce qu'on lance ; ici on parle de timing, d'allocation, de kill/réactivation et de wind-down.

---

## 1. Harvest mode en fin de campagne

À l'approche de la fermeture du panier, on bascule de la croissance à la récolte.

- On concentre le budget sur les **converteurs prouvés**, pas sur l'exploration.
- On **kill les ads qui brûlent** : seuil = >=150$ dépensés depuis la dernière baseline avec **0 paiement initié** (`initiate_checkout`).
- On **ne lance pas d'angles neufs spéculatifs** : une nouvelle poche sémantique n'a plus le temps de mûrir avant la deadline. On consolide ce qui marche.
- CBO **redistribue automatiquement** le budget des ads coupées vers les gagnantes. Couper une perdante = nourrir une gagnante, sans toucher au budget campagne.

Distinction nette avec Andromeda : en phase de croissance, on diversifie et on tolère l'immaturité. En harvest, on resserre. Le pivot forcé (kill winners gavés) reste valide en croissance, PAS en harvest où la fenêtre est trop courte.

---

## 2. Kill + backtrack (lag d'attribution pixel)

Le pixel Meta retarde les conversions. Un kill peut donc être prématuré si des conversions différées rentrent après coup.

- À chaque kill, **enregistrer l'ad dans un registre** (`killed_ads.json`) avec le nombre de paiements initiés au moment du kill.
- À chaque re-check, si des conversions différées rentrent (`IC_actuel - IC_au_kill >= seuil`, ex. 2), **RÉACTIVER l'ad**.
- **Métrique de vérité = paiement initié** (`offsite_conversion.fb_pixel_initiate_checkout`), PAS achat (`offsite_conversion.fb_pixel_purchase`) qui lag davantage.
- Signal de kill propre : **high CTR + 0 conversion** = bonne accroche, mauvaise poche sémantique (l'ad attire du monde qui ne convertira jamais).

**Façon canonique (ne plus re-coder) :** deux fonctions dans `meta_lib.py` encapsulent kill et backtrack. Toujours passer par elles plutôt que de réécrire la logique inline.
- `record_kill(registry_path, ad_name, ad_id, ic_at_kill, by)` : pause l'ad (PAUSED) et l'inscrit au registre. Idempotent, crée le fichier si absent.
- `check_backtrack(registry_path, campaign_id, gained_threshold)` : pull l'IC actuel par ad, réactive (ACTIVE) toute ad dont `IC_actuel - ic_at_kill >= gained_threshold`, la retire du registre, retourne les réactivées.
- Registre par défaut : `killed_ads.json` (constante `meta_lib.KILL_REGISTRY`, à pointer vers votre propre chemin de données).
- **Format du registre (figé)** : `{ ad_name: {"ad_id", "ic_at_kill", "killed_at", "by"} }`. Compat ascendante : les vieilles entrées sans `ad_id` sont re-résolues par nom via `{campaign}/ads`.
- `evening_kill.py` reste le job du soir (logs + snapshots) ; il pourrait s'appuyer sur ces helpers, mais sa logique inline est conservée telle quelle.

---

## 3. Pivot messaging de fermeture

À la fin, on retourne l'objection « j'ai manqué le bateau » en invitation.

- « Moins de 72h » devient « Dernière chance pour s'inscrire ».
- Quand le programme est commencé : « C'est commencé, mais il n'est pas trop tard pour embarquer ».
- C'est un pivot de MESSAGE sur les ads existantes prouvées (via nouvelle créative, voir section 2), pas un nouvel angle spéculatif.

---

## 4. Refresh visuel = NOUVELLE AD, jamais un swap d'image

Une créative Meta est **immuable**. Changer l'image d'une ad existante crée une nouvelle créative donc un nouveau post.

- On **PERD la preuve sociale** accumulée (likes, commentaires, partages) et l'ad **repart en learning**.
- Donc pour un refresh visuel : **lancer une NOUVELLE ad** et laisser l'ancienne (prouvée) rouler en parallèle. CBO arbitrera.
- Surveiller la **fréquence** : >2.2-2.5 sur les statics = fatigue = candidat refresh (nouvelle ad, pas swap).

---

## 5. Wind-down du code promo

Quand le code promo expire :

- Retirer **toutes les mentions** du code des textes de **toutes** les ads.
- Retirer le `promotional_metadata` des créatives.
- Couper l'ad promo dédiée s'il y en a une.

---

## 6. Cohérence copy / visuel obligatoire

Le texte (body) doit toujours être synchronisé avec le messaging du visuel ET la date réelle.

- Si le visuel dit « Dernière chance / Lundi », le body ne peut PAS dire « Moins de 72h / ferme dimanche ».
- À chaque pivot de fermeture ou wind-down, repasser sur chaque ad pour aligner body, visuel et date.

---

## 7. Automatisation budget (front-load puis drop)

- Budget **front-loadé** pendant la campagne, **baissé automatiquement** le matin de fermeture.
- Mécanisme suggéré : job planifié local (ex. `launchd` sur Mac, `cron` sur Linux) déclenché le matin voulu.
- **Limite headless** : un job autonome peut AGIR en pur script (via `meta_lib`) mais ne peut généralement pas notifier facilement en headless si votre notification dépend d'un client connecté. Doctrine : **agir en autonome, rapporter en session**.

---

## Ordre d'intervention en fin de campagne (checklist)

1. Passer en harvest : kill les brûleuses (>=150$, 0 IC), laisser CBO redistribuer.
2. Enregistrer chaque kill dans `killed_ads.json` avec l'IC au moment du kill.
3. Re-check périodique : réactiver les ads dont l'IC différé a rattrapé le seuil.
4. Pivot messaging de fermeture sur les gagnantes (nouvelle créative).
5. Wind-down promo le jour de l'expiration (textes + metadata + ad dédiée).
6. Refresh anti-fatigue (fréquence >2.2-2.5) = nouvelles ads, anciennes laissées en parallèle.
7. Vérifier la cohérence copy/visuel/date sur chaque ad touchée.
8. Drop budget le matin de fermeture (job planifié), rapporter en session.

Métrique de vérité partout : paiement initié.
