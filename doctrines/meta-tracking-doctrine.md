# Doctrine tracking Meta

Lecture pré-requise pour tout agent qui touche au tracking, aux conversions, à l'attribution ou à l'optimisation Meta.

## Les vérités dures

1. **Métrique de vérité pour les leads = un événement custom déclenché à la confirmation réelle** (ex. `LeadFormSubmit` sur la page de remerciement), validé 1:1 contre votre CRM. Ne jamais se fier à un event "page merci" générique gonflé par le trafic organique ou les rafraîchissements : croiser Meta avec votre CRM (vérité toutes sources) avant de rapporter un CPL/CPA final.
2. **Métrique de vérité pour les achats = `offsite_conversion.fb_pixel_initiate_checkout`** (paiement initié) plutôt que l'achat pixel pur, qui lag et sous-compte significativement selon la fenêtre d'attribution. Si votre plateforme de paiement peut envoyer les achats en server-side (CAPI) avec la vraie valeur, ça corrige ce problème.
3. **La CAPI native de votre CRM (si elle existe) peut être dangereuse comme signal d'optimisation** si elle ne transmet que l'email (pas de fbc/fbp, EMQ faible) et déduplique mal avec le pixel navigateur. Vérifiez toujours l'EMQ et la déduplication avant de pointer un ad set sur un signal serveur.
4. **Événements payants = objectif de campagne Ventes (`OUTCOME_SALES`)**, jamais trafic/vues, quand l'objectif réel est la conversion.

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
- **Pièges API** (encodage JSON, `test_event_code`, rate limits) : voir `api/meta-api-errors.md`, section Conversions API.
