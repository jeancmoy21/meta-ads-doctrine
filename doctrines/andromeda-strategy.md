# Stratégie Meta : Modèle Andromeda

*Cadre opérationnel pour toutes les campagnes Meta. Lire avant chaque brief campagne.*

**Vocabulaire.** « IC » désigne ici la conversion de vérité du CRM (ici : initiate checkout validé). C'est la métrique de LECTURE qui juge les ads, distincte de l'événement d'OPTIMISATION d'un ad set (voir `meta-tracking-doctrine.md`). `cible_cpic` est le coût cible par IC de la campagne ; `fenetre_min` est le plus grand de 3 jours ou du temps nécessaire pour obtenir 10 IC au coût cible.

## Le changement de paradigme

Depuis juillet, l'architecture de recommandation Meta a été remplacée par **Andromeda** (lancée techniquement le 22 avril). Andromeda est le premier filtre du pipeline créatif : elle "élague" des millions de variantes (volume multiplié par des milliers dû à l'IA générative) pour n'en transmettre que quelques milliers à Meta Lattice pour l'enchère finale.

**Thèse centrale : le message EST le ciblage.**

Le ciblage large (Broad) est désormais une suggestion. C'est la sémantique du créatif qui dicte la distribution. Un seul mot peut dévier une pub vers une poche d'audience totalement erronée (ex. mentionner "JK Rowling" attire des auteurs, pas des lecteurs).

Directives :
- L'imprécision verbale est un account-killer.
- Chaque mot doit être pesé pour son pouvoir de segmentation.
- Le ciblage manuel est secondaire face à l'intention sémantique du script.
- **Nuance : le pack d'intérêt adjacent [rev. 2026-11].** Broad reste le défaut. Un pack d'intérêt adjacent (un univers un cran à côté de l'offre, jamais un concurrent, un seul intérêt par pack, rempli seulement de gagnantes prouvées) s'ouvre seulement si la fréquence du segment new dépasse environ 5 sur 7 jours ou si la portée plafonne. L'intérêt élargit le bassin du pixel, il ne cible pas. Sur une audience petite (langue ou géographie étroite), le plateau de portée arrive plus tôt [inférence].

---

## Hook-Swapping vs Diversification de Messagerie

Meta teste une colonne "Creative Similarity" dans le gestionnaire pour flaguer les créatifs trop similaires. Le hook-swapping (changer uniquement l'accroche, garder le même corps) est sanctionné quand il porte sur un message non prouvé (voir Hook-swap v2 pour l'exception des messages prouvés).

| Caractéristique | Hook-Swapping | Diversification de Messagerie |
|:---|:---|:---|
| Méthode | Corps identique, premières secondes varient | Créatifs uniques de bout en bout |
| Logique | Portée de masse | Exploitation de niches |
| Probabilité de succès | Faible | Élevée |
| Longévité | Courte (fatigue accélérée) | Étendue |
| Effort | Faible | Élevé (scripts uniques obligatoires) |

Le volume sans diversité = antibiotique créatif. L'audience développe une résistance. Hypothèse de fatigue, pas un verdict : les performances peuvent s'effondrer après environ 48 h si les thèmes ne changent pas. Cette durée se vérifie sur vos propres données et ne justifie jamais un kill avant `fenetre_min` [rev. 2026-11].

---

### Hook-swap v2 (révisé [rev. 2026-11])

On compte les MESSAGES (mécanisme nommé + poche sémantique visée), jamais les ads ni les fichiers. Deux axes : MESSAGE et ASSET (ce que l'oeil voit dans les 3 premières secondes).

| Situation | Compte au banc | Plafond |
|:---|:---|:---|
| Message neuf + asset neuf | 1 | Aucun |
| Message neuf + asset déjà en diffusion | 1 | 3 messages distincts max par asset dans un ad set (fréquence visuelle : 5 ads sur une même vidéo atteignent la fréquence de brûlure au cinquième de la dépense par ad) |
| Même message `nouveau` (non prouvé) + accroche/texte différent (multiplicateur de distribution) | 0 | 2 ads max par message |
| Même message **prouvé** + itération d'un seul bloc (lead-in, hook, body, CTA, porte-parole ou format) | 0 | 3 à 6 itérations, dans un pack `iteration` séparé du pack `nouveau` |
| Même message + même asset | Interdit | Interdit |

**Message prouvé** : au moins 5 % de la dépense de la campagne, à `cible_cpic` ou proche. C'est `meta-analyse` qui le désigne. On itère depuis ce qui dépense le plus ; une itération change un seul bloc à la fois. Les itérations maintiennent (haut taux de réussite, faible potentiel), le neuf débloque (l'inverse) : les deux roulent, en packs séparés. Le plafond de 2 ads reste entier pour tout message non prouvé.

**Laisse asymétrique** : un multiplicateur d'accroche se tue à 2x `cible_cpic` dépensés à 0 IC, une fois `fenetre_min` écoulée (il n'enseigne rien en mourant). Un message neuf garde la laisse standard complète (il enseigne quelque chose sur une poche même en mourant).

**Quota créatif** : max(2 ads par semaine, 1 ad par 10 k$ mensuels) de dépense du compte (repère empirique : au-delà d'un certain volume de dépense, le compte apprend plus par ses ads que par ses audiences, donc le rythme créatif doit suivre la dépense), converti en messages au ratio réel ads par message observé sur le compte. La qualité passe avant le nombre ; les formats et les variantes de headline d'une même idée ne comptent pas. Au lancement d'une campagne, banc = pack neuf de 4 à 8 ads. Un quota fixe de type « 25 à 30 messages par mois » n'a pas de sens en soi : il correspond à un niveau de dépense mensuelle précis (de l'ordre de plusieurs dizaines de milliers de dollars par mois selon la règle ci-dessus [calcul]). Compte pour 1 : un mécanisme jamais diffusé, peu importe le support (un static à angle neuf = une vidéo à angle neuf). Compte pour 0 : accroche différente sur un message au banc, reformulation du même mécanisme, changement de headline seul, nouveau visuel portant un mécanisme déjà diffusé (utile contre la fatigue visuelle, n'ajoute pas de poche).

---

## Les deux voies de passage à l'échelle (révisé [rev. 2026-11])

**Voie 1 : Volume industriel** : 50 itérations/semaine (200/mois). Hors portée et contre-productive sous un budget moyen : empiler des packs sans hausser le budget met le compte en learning limited (ex. lancer des dizaines d'ads par semaine sans hausser le budget dilue la dépense par ad sous le seuil d'apprentissage).

**Voie 2 : Diversité de messagerie dans le quota (recommandée)** : le volume suit le quota créatif ci-dessus, chaque unité porte un message distinct.
- Accès à des poches d'audience inexploitées, moins chères.
- Stabilité supérieure : pas de dépendance à une accroche miracle.

Repères [exemple chiffré, 4,33 semaines par mois, 1 à 3 ads par message] : 5 à 20 k$/mois = plancher de 2 ads par semaine, environ 9 ads par mois, soit 3 à 9 messages ; 40 k$/mois = 4 ads par semaine, environ 17 ads, soit 6 à 17 messages. Une campagne à date butoir concentre ce volume au lancement (banc de 4 à 8 ads).

---

## Cadre des messages : 3 piliers et l'étage objection

1. **Problèmes** : points de douleur spécifiques (perte de temps, stress, coût caché). La douleur est un outil ponctuel, jamais le défaut : au plus un angle douleur par batch, décidé explicitement ; douleur évidente et statistique anxiogène toujours interdites [rev. 2026-11].
2. **Circonstances** : situations de vie (au bureau, en voyage, le matin)
3. **Résultats (Outcomes)** : bénéfices finaux (statut, paix d'esprit, performance)

Ne pas faire N versions du même thème : chaque message du quota porte un angle distinct. Chaque thème est un forage distinct dans le réservoir d'audience. Le gain est l'angle par défaut ; l'empilement d'obstacles concrets et reconnaissables est permis dans le corps.

**Étage objection [rev. 2026-11]** : le créatif vise tout en haut (avatar, problème, solution) ou tout en bas (objections retournées), jamais le milieu. Chaque message porte l'étiquette `haut` ou `bas`.

**Le funnel se définit par la conversion demandée, pas par la température de l'audience [rev. 2026-11].** Tout achat est bas de funnel ; un lead est haut de funnel. Statics = format par défaut des offres d'achat ; vidéo = format par défaut du lead gen. Un défaut, pas un interdit : le drapeau 4 du gate reste entier.

---

## Avatars : le troisième axe (révisé [rev. 2026-11])

Un **avatar** est un persona d'audience défini par son identité ou sa circonstance de vie, jamais par la démographie. Le but : identifier des personas et tailorer des ads pour eux. Concept validé en production sur plusieurs comptes, où il a vraiment cartonné.

**Mécanique :**
- On regroupe les ads d'un même avatar dans UN ad set dédié. C'est ce regroupement qui pousse le AI targeting d'Andromeda à faire son ciblage à partir du messaging : tous les bodies de l'ad set parlent le référentiel du même persona, donc l'algorithme fore la même poche.
- Chaque body est écrit dans le référentiel concret de son avatar (l'entrepreneur : « votre téléphone sonne moins l'été » ; l'ouvrier : « votre dos a une date d'expiration »). **Aucun body ne se recycle d'un avatar à l'autre** : c'est de la diversification sémantique, pas du hook-swap.
- L'avatar est orthogonal aux piliers et aux angles : il définit QUI on adresse, le pilier et l'angle définissent QUOI on dit. Un avatar mature couvre plusieurs piliers en son sein.
- Étalon de référence de la mécanique : un manifeste de type `manifests/exemple-avatar-batch.deploy.json` (1 ad set par avatar, 5-6 bodies propres, une LP par avatar quand possible). Lancer plusieurs avatars ensemble n'est plus le défaut (règle ci-dessous).

**Nombre d'avatars [rev. 2026-11] :** 1 ou 2 avatars simultanés, peu importe le budget. L'avatar gagnant est creusé (nouveaux problèmes du même avatar) avant d'en ouvrir un autre. Lancement échelonné : un pack d'avatar neuf à la fois. Mécanisme : chaque ad set neuf doit recevoir assez de budget pour apprendre. Contrainte [exemple chiffré, cible de 100 $ par IC, minimum de 1x la cible par ad set neuf, minimums ≤ 20 % du budget] : à 500 $/jour, 4 avatars lancés ensemble demanderaient 400 $ de minimums, soit 80 % du budget.

**Phasage d'une campagne :** il est légitime de lancer une phase 1 sans ad sets d'avatars (avatars documentés au niveau des ads seulement) et d'ajouter les ad sets par avatar en phase 2+, quand le volume de signal le justifie.

**Langue et géo :** SOIT une géo large avec les variantes de langue correspondantes dans les langues, SOIT une géo resserrée avec AUCUNE restriction de langue. Jamais l'un et l'autre à moitié. Vérifier la locale exacte encodée par Meta (ex. la locale 24 est l'anglais UK, pas générique) : toute valeur de `locales` doit être décodée avant déploiement, jamais recopiée d'un manifeste antérieur. **Dérogation ponctuelle [rev. 2026-11]** : un pack de test avec une géo resserrée ET une restriction de langue peut rouler côte à côte avec un pack sans restriction, mêmes gagnantes, coût par IC comparé sur `fenetre_min`, sur approbation du propriétaire du compte et marqué comme test dans le manifeste. La règle ci-dessus reste le défaut.

---

## Structure de campagne [rev. 2026-11]

- **Une campagne par événement à date butoir ; sinon presque jamais de nouvelle campagne de prospection** : on ajoute des packs neufs (nouveaux ad sets) à la campagne existante.
- **Chaque lot créatif va dans un pack neuf : un NOUVEL ad set de la campagne, de 4 à 8 ads** (souvent 4 à 6). Jamais d'ajout dans un ad set existant, jamais de déplacement d'une ad, jamais de duplication d'ad set.
- **Packs `nouveau` et `iteration` séparés** (Hook-swap v2).
- **Un seul événement d'optimisation par CBO** : règle et choix de l'événement dans `meta-tracking-doctrine.md`.
- **Minimums et maximums d'ad set** : `meta-campaign-lifecycle.md`, section « Lancement d'un pack ».
- **Ignorer les recommandations automatiques de Meta** (consolidation, score d'opportunité, fusion de packs) : une consolidation en troisième semaine a produit un effondrement jamais résorbé.
- **Advantage+ creative** : refus de tout ce qui modifie l'image ou la vidéo, règle dans `meta-tracking-doctrine.md`.

---

## Mécanique de distribution : Analogie du champ de pétrole

Le terrain = 20 000 acres. Chaque créatif = un forage.
- Certains frappent des poches profondes (audience large, durable).
- Beaucoup frappent des poches superficielles (performance courte, puis épuisement ; durée à vérifier, voir l'hypothèse de fatigue plus haut).
- Sans banc chargé au quota créatif (packs neufs de 4 à 8 ads), impossible de trouver de nouvelles poches quand la première est à sec.

**Le phénomène des "miettes" (pennies) :** dans une campagne, 1 à 3 ads captent l'essentiel de la dépense (90 % observé). Les autres reçoivent des centimes. Ce n'est pas un échec : c'est le banc de touche, prêt à relayer quand la poche principale s'épuise. **L'ad dominante fait souvent le haut de funnel pour les autres** : la couper redistribue tout son budget d'un coup vers des ads qui récoltent le bas, avec un pic de 3 à 7 jours puis un assèchement. D'où la SOP plafonnement ci-dessous [rev. 2026-11].

---

## SOP : plafonnement [rev. 2026-11]

Remplace l'ancien « cycle de pivot forcé » (dupliquer l'ad set, désactiver les gagnantes). Appliquer quand le coût par IC monte et que l'ad ou l'ad set dominant fatigue ou rate sa cible, une fois `fenetre_min` écoulée.

1. **Juger la campagne d'abord** : coût par IC de la campagne (croisé avec le CRM) contre `cible_cpic`. Si la campagne est à la cible, on ne tue jamais l'ad ou l'ad set no 1, ni aucune ad à plus de 30 % de la dépense : on la plafonne ; seuls les duds se coupent (seuil de kill relatif en deux paliers, `meta-campaign-lifecycle.md` §2).
2. **Identifier la fatigue de la dominante** : son coût par IC au-dessus de `cible_cpic`, diffusion qui baisse, fréquence au-dessus des seuils de `meta-campaign-lifecycle.md` §4.
3. **Plafonner** : plafond (spending limit) en % sur l'ad ou l'ad set dominant, par paliers de 10 à 20 points (ex. 70 % de la dépense ramené à 50 % ou 60 %), ou `adset_spend_cap`. Jamais une pause. Relire après `fenetre_min` avant le palier suivant. Le plafond ne déplace que l'écart (CBO à 1 000 $/jour, dominante à 70 % : une pause redistribue 700 $/jour d'un coup, un plafond à 50 % en redistribue 200 $ [calcul]).
4. **Alimenter le banc** : les nouvelles ads vont dans un nouvel ad set de la même campagne (pack neuf de 4 à 8 ads, minimums de `meta-campaign-lifecycle.md`). Jamais de duplication d'ad set.
5. **Kill de la no 1 seulement si la campagne entière rate sa cible** après plafonnement, au seuil de kill relatif et après `fenetre_min`.

---

## Règle sémantique : vérification obligatoire avant tout script

Pour chaque script Meta : vérifier que chaque mot cible la bonne poche.
- Qui est l'audience que ce mot va attirer ?
- Est-ce cohérent avec le funnel ?
- Y a-t-il un terme ambigu qui pourrait dévier la distribution ?

---

## GATE ANTI-DÉRIVE : à passer AVANT toute analyse ou reco Meta

But : empêcher la dérive vers la perf/CRO classique. Toute reco Meta doit passer ce gate. Si une phrase déclenche un 🚩, STOP et reformule par la doctrine.

**Détecteur de dérive (erreurs récurrentes courantes) :**
1. 🚩 « La concentration du spend est toxique / un problème. » → NON. Miettes = 1-3 ads captent 90% du spend, c'est NORMAL. Le vrai problème = absence de banc chargé au quota créatif (packs neufs de 4 à 8 ads), pas la concentration.
2. 🚩 « Il faut tuer le gagnant / couper la dominante parce qu'elle est gavée. » → NON. On plafonne sa part en % par paliers de 10 à 20 points (SOP plafonnement) ; on ne coupe que les duds ; la no 1 ne se coupe que si la campagne entière rate sa cible après plafonnement.
3. 🚩 « Pourquoi ma meilleure ad ne spend pas plus » ou « on juge ce matin, sur la journée d'hier ». → Pas un bug, et pas un jugement. Économie marginale + miettes : le signal = un pack neuf dans un nouvel ad set, pas gaver ni tuer. Aucun kill avant `fenetre_min` (le plus grand de 3 jours ou du temps nécessaire pour 10 IC au coût cible) ; les lectures quotidiennes restent permises, sans action.
4. 🚩 « C'est un enjeu de format / placement / ratio d'aspect. » → Plomberie SECONDAIRE. Labelliser [hors-doctrine]. Jamais un levier central ni une prescription. Ne pas bloquer un lancement pour ça. Seule règle de format retenue : le défaut suit la conversion demandée (achat = statics par défaut, lead = vidéo par défaut, voir « Cadre des messages »).
5. 🚩 « ROAS Ads Manager, CPL moyen, CPM, CPC, CTR ou ViewContent » comme juge. → NON. Le seul juge de kill et de budget est le coût par IC croisé avec le CRM contre `cible_cpic`, la campagne jugée avant l'ad set, l'ad set avant l'ad. La part par segment (new, engaged, existing) et la colonne incrémentale se lisent dans chaque rapport, sans décider. Juges créatifs inchangés : diversité sémantique, couverture des angles, miettes, rétention vidéo, fréquence/saturation.
6. 🚩 « On re-push le même MESSAGE avec une nouvelle accroche. » (corps identique) → hook-swap, sanctionné sur un message non prouvé au-delà de 2 ads. Message prouvé (au moins 5 % de la dépense, à la cible ou proche) : 3 à 6 itérations d'un bloc à la fois, en pack `iteration` séparé, comptées 0 au banc. Vraie diversité = créatif unique de bout en bout, c'est à dire un nouveau message.
7. 🚩 « Le banc est chargé, on a 16 ads actives. » → NON, on compte les messages, pas les ads. Voir « Hook-swap v2 » ci-dessus.

**Gate positif (toute reco Meta doit répondre) :**
- Quels PILIERS (Problème/Circonstance/Résultat), quel étage (`haut` ou `bas`) et quels ANGLES (Recours sceptique, Conséquence du lendemain, Éveil chirurgical, Autorité inattendue, Désir de normalité) ce batch couvre-t-il ? Quels angles morts ?
- Vraie diversité sémantique ou hook-swap déguisé ? Les packs `nouveau` et `iteration` sont-ils séparés ?
- Le banc respecte-t-il le quota créatif max(2 ads par semaine, 1 ad par 10 k$ mensuels) ?
- État de saturation (fréquence) et coût par IC contre `cible_cpic` après `fenetre_min` → faut-il un plafonnement (SOP) ou un pack neuf ?
- Tout input hors-doctrine (format, placement, CPM, CTR, coût marginal) est-il explicitement labellisé [secondaire] et exclu des prescriptions ?

**Règle de labellisation :** quand on cite une mécanique hors-doctrine (format, coût marginal, lag d'attribution), on la tague `[hors-doctrine / secondaire]`. Elle peut éclairer la lecture, jamais dicter la prescription. Les segments d'audience et la colonne incrémentale ne sont plus hors-doctrine : lecture obligatoire, jamais juge seul [rev. 2026-11].
