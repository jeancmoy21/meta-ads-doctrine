# Doctrine tracking Meta

Lecture pré-requise pour tout agent qui touche au tracking, aux conversions, à l'attribution ou à l'optimisation Meta.

## Les vérités dures

0. **Métrique de LECTURE et événement d'OPTIMISATION sont deux choses distinctes [rev. 2026-11].** Les points 1 et 2 fixent ce qu'on LIT pour juger (croisé avec le CRM). L'événement d'optimisation de chaque ad set suit la règle « Événement d'optimisation » ci-dessous.
1. **Métrique de vérité (lecture) pour les leads = un événement custom déclenché à la confirmation réelle** (ex. `LeadFormSubmit` sur la page de remerciement), validé 1:1 contre votre CRM. Ne jamais se fier à un event "page merci" générique gonflé par le trafic organique ou les rafraîchissements : croiser Meta avec votre CRM (vérité toutes sources) avant de rapporter un CPL/CPA final.
2. **Métrique de vérité (lecture) pour les achats = `offsite_conversion.fb_pixel_initiate_checkout`** (paiement initié) plutôt que l'achat pixel pur, qui lag et sous-compte significativement selon la fenêtre d'attribution. Si votre plateforme de paiement peut envoyer les achats en server-side (CAPI) avec la vraie valeur, ça corrige ce problème.
   - **Le Purchase standard du pixel peut être gonflé par une plateforme de cours** : si la plateforme de cours re-tire un Purchase avec la valeur du cours à l'arrivée de l'étudiant, le même paiement compte deux fois. Toute règle Purchase personnalisée doit alors exclure cette source (par identifiant de contenu ou par URL), et le ROAS achat d'Ads Manager n'est pas fiable tant que le doublon existe.
3. **La CAPI native de votre CRM (si elle existe) peut être dangereuse comme signal d'optimisation** si elle ne transmet que l'email (pas de fbc/fbp, EMQ faible) et déduplique mal avec le pixel navigateur. Vérifiez toujours l'EMQ et la déduplication avant de pointer un ad set sur un signal serveur.
4. **Événements payants = objectif de campagne Ventes (`OUTCOME_SALES`)**, jamais trafic/vues, quand l'objectif réel est la conversion.

## Événement d'optimisation [rev. 2026-11]

- **Règle.** L'événement d'optimisation est l'événement le plus profond qui garde au moins 10 conversions par semaine : l'achat pour les campagnes payantes, le lead qualifié pour les gratuites, partout, tout de suite. On ne renvoie à Meta que les conversions qualifiées. Mécanisme : Meta trouve les gens qui déclenchent l'événement choisi au plus bas coût ; un proxy (IC, lead brut) trouve des gens qui font le proxy, pas des acheteurs.
- **Contraintes techniques, pas des choix.**
  1. Changer d'événement exige un NOUVEL ad set : le `promoted_object` d'un ad set existant est immuable, même PAUSED (subcode 3260011).
  2. Une conversion achat propre (pas gonflée par un doublon, prouvée par un tir de test : `GET <conv>/stats?aggregation=count`) est un préalable à l'optimisation sur l'achat.
  3. Une question qualifiante au formulaire (section « Qualification des leads ») est le préalable du lead qualifié.
  Tant que le préalable manque, l'ad set reste sur IC ou lead brut et le manifeste le dit en clair.
- **Un seul événement d'optimisation par campagne CBO** : Meta va au plus facile si on mélange.
- **Si l'événement profond ne produit rien**, remonter d'une étape puis redescendre ; jamais un événement qui arrive plus d'une semaine après le clic.
- Volume [exemple chiffré, coût par achat de 65 à 250 $] : 10 achats par semaine demandent 650 à 2 500 $/semaine, soit 2,8 à 10,8 k$/mois.

## Cible de coût [rev. 2026-11]

`cible_cpic` (coût cible par IC de la campagne) est un champ obligatoire du manifeste de build. Elle se dérive d'un seuil de rentabilité combiné : cible = seuil x (1 + marge voulue) (ex. 1,3 x 1,3 ≈ 1,7). Pour un événement, le seuil inclut la valeur des produits vendus ensuite, pas seulement le billet d'entrée. Une offre d'entrée qui sert d'ascension peut rouler au seuil de rentabilité : seul le volume compte.

## Segments d'audience et incrémental [rev. 2026-11]

- **Segments réglés dans le compte** (réglages d'annonceur, non rétroactifs, donc à faire tout de suite) : existing = acheteurs récents (ex. 180 jours) + liste CRM des inscrits ; engaged = visiteurs de la landing page (30 jours), IC (90 jours), leads du CRM ; new = le reste. Réglage manuel unique par le propriétaire du compte.
- **Lecture dans chaque rapport `meta-analyse`** : part de la dépense et des IC par segment (new, engaged, existing) et colonne d'attribution incrémentale. Pour un billet élevé, environ 25 % d'engaged est normal ; alerte vers 50 %.
- **Les décisions restent sur le coût par IC croisé avec le CRM.** L'incrémental éclaire, il ne décide pas (l'optimisation incrémentale se réserve aux gros comptes). Disponibilité de l'incrémental sur IC et lead brut : [NON VÉRIFIÉ].

## Qualification des leads [rev. 2026-11]

- **Question disqualifiante tôt au formulaire ; les disqualifiés ne déclenchent ni le pixel ni la CAPI** (les leads non qualifiés ne doivent pas être pixelés). Implémentation : le poller CAPI filtre sur la propriété de qualification du CRM.
- **Éviter les Instant Forms** : la landing page donne des leads plus qualifiés. Un lead form demande une dérogation explicite du propriétaire du compte.
- **Renvoyer les ventes conclues hors ligne** (courriel, téléphone, nom, code postal) à la CAPI : chantier de seconde phase.

## Architecture de tracking leads (patron générique)

- **Pixel navigateur** : init sur toutes les pages du funnel.
- L'événement de vérité (ex. `LeadFormSubmit`) devrait idéalement se déclencher depuis la page de confirmation post-soumission, pas depuis le formulaire lui-même si le formulaire est un iframe cross-origin qui n'expose aucune valeur soumise côté client.
- **Server-side (CAPI)** : un poller ou webhook qui lit les soumissions confirmées côté CRM/backend et envoie l'événement en Conversions API (email hashé SHA-256, `fbc` reconstruit du cookie de clic si disponible).
- **Déduplication** : générer un event_id déterministe (ex. préfixe + `sha256(email normalisé)`) calculé indépendamment côté navigateur ET côté serveur. Fenêtre de dédup Meta = 48h. Effet voulu : une resoumission du même email sous 48h ne compte qu'une fois.
- Si vous utilisez une gateway serveur tierce (ex. Stape ou équivalent) qui relaie les events navigateur en server-side, assurez-vous qu'elle relaie l'eventID du pixel plutôt que d'en générer un nouveau, sinon double comptage.

## Règles pour toute évolution du tracking

- **Jamais de nouvel event serveur sans clé de dédup partagée avec le pixel** si le pixel émet le même event_name : c'est le mécanisme exact d'un double comptage classique.
- **Un fire pixel sans eventID explicite reçoit un id auto-généré** qui ne dédupliquera jamais avec un id serveur calculé. Vérifier par capture réseau (`facebook.com/tr`, paramètre `eid`) avant toute mise en prod.
- **Ne pas se fier à l'onglet Test Events** du Events Manager (affichage historiquement peu fiable). Valider par capture réseau + logs serveur + panneaux Couverture/Déduplication à J+1.
- **Rollout d'un nouveau form/LP** : ajouter le pattern à l'allowlist du poller, déployer le script de la page de confirmation correspondante, retirer tout fire legacy sur la LP, tester avec une soumission réelle et capture réseau.
- **Piège UTM et post ID [rev. 2026-11].** Une intégration qui réécrit les UTM peut réinitialiser tous les post ID, donc la preuve sociale et l'historique des ads (perte de ROAS observée à dépense égale). Avant et après tout changement d'URL ou d'UTM, `meta-deploy` compare l'identifiant de post des ads touchées [champ NON VÉRIFIÉ].
- **Advantage+ creative [rev. 2026-11].** Refuser tout ce qui modifie l'image ou la vidéo ; texte et CTA acceptés ; « test new enhancements » décoché. Le refus des enhancements visuels est disponible dans les fonctions `make_*_creative` de `meta_lib.py` par `opt_out_visuel=True` ; le défaut reste `opt_out_visuel=False`, parce que les noms de features d'enhancement ne sont pas vérifiés [NON VÉRIFIÉ live]. Il devient le défaut seulement après un tir de test qui vérifie ces noms. D'ici là, `meta-deploy` vérifie dans Ads Manager que les enhancements visuels sont décochés sur chaque ad créée. La création par post ID (`make_creative_from_post`, `create_ad_from_post`) passe par `meta_lib`, derrière la gate `go=True` comme toute écriture. Aucun contrôle de `validate_manifest.py` sur ce point à ce jour.
- **Multi-advertiser ads et related media désactivés en prospection [rev. 2026-11]** : rien ne diffuse hors de ce qu'on a choisi [champ NON VÉRIFIÉ].
- **Pièges API** (encodage JSON, `test_event_code`, rate limits) : voir `api/meta-api-errors.md`, section Conversions API.
