# Stratégie Meta : Modèle Andromeda

*Cadre opérationnel pour toutes les campagnes Meta. Lire avant chaque brief campagne.*

## Le changement de paradigme

Depuis juillet, l'architecture de recommandation Meta a été remplacée par **Andromeda** (lancée techniquement le 22 avril). Andromeda est le premier filtre du pipeline créatif : elle "élague" des millions de variantes (volume x10 000 dû à l'IA générative) pour n'en transmettre que quelques milliers à Meta Lattice pour l'enchère finale.

**Thèse centrale : le message EST le ciblage.**

Le ciblage large (Broad) est désormais une suggestion. C'est la sémantique du créatif qui dicte la distribution. Un seul mot peut dévier une pub vers une poche d'audience totalement erronée (ex. mentionner "JK Rowling" attire des auteurs, pas des lecteurs).

Directives :
- L'imprécision verbale est un account-killer.
- Chaque mot doit être pesé pour son pouvoir de segmentation.
- Le ciblage manuel est secondaire face à l'intention sémantique du script.

---

## Hook-Swapping vs Diversification de Messagerie

Meta teste une colonne "Creative Similarity" dans le gestionnaire pour flaguer les créatifs trop similaires. Le hook-swapping (changer uniquement l'accroche, garder le même corps) est sanctionné.

| Caractéristique | Hook-Swapping | Diversification de Messagerie |
|:---|:---|:---|
| Méthode | Corps identique, premières secondes varient | Créatifs uniques de bout en bout |
| Logique | Portée de masse | Exploitation de niches |
| Probabilité de succès | Faible | Élevée |
| Longévité | Courte (fatigue accélérée) | Étendue |
| Effort | Faible | Élevé (scripts uniques obligatoires) |

Le volume sans diversité = antibiotique créatif. L'audience développe une résistance immédiate. Effondrement des performances après 48h si les thèmes ne changent pas.

---

## Les deux voies de passage à l'échelle

**Voie 1 : Volume industriel** : 50 itérations/semaine (200/mois). Infrastructure IA/B-roll massive. Épuisant.

**Voie 2 : Diversité de messagerie (recommandée)** : 25 à 30 créatifs uniques/mois.
- Andromeda récompense la diversité sémantique par des CPM préférentiels.
- Accès à des poches d'audience inexploitées, moins chères.
- Stabilité supérieure : pas de dépendance à une accroche miracle.

---

## Cadre des 25-30 créatifs uniques : 3 piliers

1. **Problèmes** : points de douleur spécifiques (perte de temps, stress, coût caché)
2. **Circonstances** : situations de vie (au bureau, en voyage, le matin)
3. **Résultats (Outcomes)** : bénéfices finaux (statut, paix d'esprit, performance)

Ne pas faire 30 versions du même thème. 30 vidéos uniques, chacune sur un angle distinct. Chaque thème est un forage distinct dans le réservoir d'audience.

---

## Avatars : le troisième axe

Un **avatar** est un persona d'audience défini par son identité ou sa circonstance de vie, jamais par la démographie. Le but : identifier des personas et tailorer des ads pour eux. Concept validé en production sur plusieurs comptes, où il a vraiment cartonné.

**Mécanique :**
- On regroupe les ads d'un même avatar dans UN ad set dédié. C'est ce regroupement qui pousse le AI targeting d'Andromeda à faire son ciblage à partir du messaging : tous les bodies de l'ad set parlent le référentiel du même persona, donc l'algorithme fore la même poche.
- Chaque body est écrit dans le référentiel concret de son avatar (l'entrepreneur : « votre téléphone sonne moins l'été » ; l'ouvrier : « votre dos a une date d'expiration »). **Aucun body ne se recycle d'un avatar à l'autre** : c'est de la diversification sémantique, pas du hook-swap.
- L'avatar est orthogonal aux piliers et aux angles : il définit QUI on adresse, le pilier et l'angle définissent QUOI on dit. Un avatar mature couvre plusieurs piliers en son sein.
- Étalon de référence : un manifeste de type `manifests/exemple-avatar-batch.deploy.json` (1 ad set par avatar, 5-6 bodies propres, une LP par avatar quand possible).

**Phasage d'une campagne :** il est légitime de lancer une phase 1 sans ad sets d'avatars (avatars documentés au niveau des ads seulement) et d'ajouter les ad sets par avatar en phase 2+, quand le volume de signal le justifie.

**Langue et géo :** SOIT une géo large avec les variantes de langue correspondantes dans les langues, SOIT une géo resserrée avec AUCUNE restriction de langue. Jamais l'un et l'autre à moitié. Vérifier la locale exacte encodée par Meta (ex. la locale 24 est l'anglais UK, pas générique) : toute valeur de `locales` doit être décodée avant déploiement, jamais recopiée d'un manifeste antérieur.

---

## Mécanique de distribution : Analogie du champ de pétrole

Le terrain = 20 000 acres. Chaque créatif = un forage.
- Certains frappent des poches profondes (audience large, durable).
- Beaucoup frappent des poches superficielles (48h de performance, puis épuisement).
- Sans 25-30 options chargées, impossible de trouver de nouvelles poches quand la première est à sec.

**Le phénomène des "miettes" (pennies) :** Dans un batch de 30 créatifs, 1 à 3 pubs captent 90% du spend. Les 27 autres reçoivent des centimes. Ce n'est pas un échec : c'est le banc de touche. Ces créatifs sont prêts à relayer quand la poche principale s'épuise.

---

## SOP : Cycle de pivot forcé

Appliquer quand le CPA monte et la diffusion des gagnants baisse.

1. **Identifier la fatigue** : hausse CPA + baisse diffusion des créatifs winners.
2. **Dupliquer l'Ad Set** : copie exacte.
3. **Kill the Winners** : désactiver manuellement les 1-3 pubs qui ont consommé le budget précédent.
4. **Forcer l'exploration** : relancer avec les 22-27 créatifs restants. Andromeda fore de nouvelles poches avec ces messages frais.

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
1. 🚩 « La concentration du spend est toxique / un problème. » → NON. Miettes = 1-3 ads captent 90% du spend, c'est NORMAL. Le vrai problème = absence de banc chargé (25-30 créatifs frais), pas la concentration.
2. 🚩 « Protéger / isoler / nourrir le gagnant. » → NON. On kill les winners GAVÉS et on force l'exploration du banc. (Nuance : un winner JEUNE non-gavé, fréquence basse + CPL stable/baissier, on ne le kill pas encore.)
3. 🚩 « Pourquoi ma meilleure ad ne spend pas plus / elle devrait spender plus. » → Pas un bug. Économie marginale + miettes. Le signal = pivoter (banc frais, fréquence-zéro), PAS gaver le gagnant.
4. 🚩 « C'est un enjeu de format / placement / ratio d'aspect. » → Plomberie SECONDAIRE. Labelliser [hors-doctrine]. Jamais un levier central ni une prescription. Ne pas bloquer un lancement pour ça.
5. 🚩 « CPL moyen / ROAS / grille CRO » comme juge principal. → NON. Juger par : diversité sémantique, couverture des angles, miettes, rétention vidéo, fréquence/saturation, cadence de pivot.
6. 🚩 « On re-push le gagnant avec une nouvelle accroche. » (corps identique) → c'est du hook-swap, sanctionné. Vraie diversité = créatif unique de bout en bout.

**Gate positif (toute reco Meta doit répondre) :**
- Quels PILIERS (Problème/Circonstance/Résultat) et ANGLES (Recours sceptique, Conséquence du lendemain, Éveil chirurgical, Autorité inattendue, Désir de normalité) ce batch couvre-t-il ? Quels angles morts ?
- Vraie diversité sémantique ou hook-swap déguisé ?
- État de saturation (fréquence) → faut-il un pivot forcé (dupliquer ad set, kill winners gavés, relancer le banc) ?
- Tout input hors-doctrine (format, CPL moyen, attribution, CPM) est-il explicitement labellisé [secondaire] et exclu des prescriptions ?

**Règle de labellisation :** quand on cite une mécanique hors-doctrine (format, coût marginal, lag d'attribution), la tague `[hors-doctrine / secondaire]`. Elle peut éclairer la lecture, jamais dicter la prescription.
