# Doctrine : courriel et SMS autour d'un lancement

*Complète `meta-campaign-lifecycle.md` : Meta va chercher le froid, le courriel et le SMS récoltent le chaud. À lire avant toute séquence de lancement.*

Principe : chaque IC non payé n'est relancé, par défaut, que par Meta, au prix d'une impression. Une architecture de flows par workflow, avec une cadence tenue, récolte ce chaud à moindre coût. Cette doctrine décrit les flows d'un lancement et les principes qui s'appliquent à chaque envoi.

---

## Principes (s'appliquent à chaque envoi)

1. **Approbation humaine avant tout envoi.** Aucun envoi de masse sans courriel de test et approbation explicite de la personne responsable, donnée dans le fil de la demande.
2. **Le CRM est la source des listes.** L'entrée dans une séquence est une propriété ou un événement du CRM, l'inscription se fait par workflow, jamais par import de liste statique. Le contact quitte la séquence dès l'achat (propriété synchronisée depuis la plateforme de paiement).
3. **Un workflow nommé par flow** : déclencheur, délai et sortie sont écrits dans le brief avant la copy.
4. **Urgence vraie seulement.** Une date de fin ou une prolongation n'existe que si elle est vraie et décidée par la personne responsable. Aucune fausse rareté, aucun faux « retour en stock », aucun texte caché pour déjouer les filtres.
5. **Claims crédibles, aucun rendement promis.** Statistique permise seulement si sourcée (source dans le courriel ou en note de bas) ; la statistique anxiogène reste interdite.
6. **Dates, prix et code identiques à ceux des ads** de la même phase.
7. **Consentement conforme à la loi applicable** (ex. loi canadienne anti-pourriel) : aucune case précochée pour le courriel ou le SMS ; vérifier toute capture de consentement avant la mise en ligne.
8. **Le ton et la longueur suivent la voix de la marque.** Une lettre longue signée peut battre un format court ; on la garde si elle gagne à l'achat, on teste plutôt que de supposer.

---

## Les flows d'un lancement

### 1. Post-inscription (événement gratuit vers l'offre payante)

- Premier courriel à la seconde de l'inscription (confirmation, accès, date, heure du direct).
- Puis 3 à 5 courriels espacés de 1 à 2 jours.
- Après 5 jours sans achat, la conversion devient difficile : la séquence se termine ou bascule vers la relance de lancement suivante.
- Sortie : dès l'achat, le contact quitte la séquence.

### 2. Paiement commencé non complété (IC sans achat)

C'est la métrique de vérité de lecture : chaque IC non payé a sa séquence. Quatre courriels :
1. Rappel simple : le panier, le lien, la date de l'événement.
2. Texte personnel du fondateur et preuve (témoignage nominatif réel).
3. L'offre (prix, code s'il existe, date de fin vraie).
4. Dernière chance, en texte simple, avec un PS.

En complément, avec approbation : textos ou appels aux IC non payés. Un remarketing Meta allégé ne se teste qu'une fois cette séquence en marche (`meta-campaign-lifecycle.md`, §10).

### 3. Après l'achat (vente des produits suivants)

- Les 7 jours après un achat sont la fenêtre la plus chaude.
- Merci en texte du fondateur, l'offre suivante en PS. Un taux de commande de 2 à 3 % sur ce merci est un repère courant.

### 4. Capture et consentement

- Le taux de capture de la page est un levier : un test aux deux semaines, sans toucher aux courriels.
- Courriel et SMS ne se demandent jamais sur la même étape.
- Une micro-question avant le courriel (avatar ou intention) augmente la capture et alimente la qualification.

### 5. Calendrier de lancement

Aligné sur les phases Meta (`meta-campaign-lifecycle.md`) :
- dates clés fixées d'abord (ouverture, fermeture du panier, début de l'événement) ;
- satellites : 1 ou 2 teasers, l'ouverture, 1 ou 2 rappels, la dernière chance ;
- entre les satellites, 3 ou 4 envois par semaine ;
- le message de fermeture suit le pivot de `meta-campaign-lifecycle.md` §3 (« Dernière chance pour s'inscrire »), avec la même date que les ads.

### 6. Direct plutôt qu'evergreen

Le webinaire en direct vend généralement mieux que l'evergreen ; un evergreen se regroupe en événement tous les 2 à 4 jours. Les rappels du direct font partie de chaque séquence.

---

## À tester, sans règle encore

- Objet testé au revenu, pas au taux d'ouverture.
- Délivrabilité : ouverture au-dessus de 45 %, plaintes sous 0,01 %.
- Bouton au-dessus du pli ; nom d'expéditeur humain.
- Reconquête des anciens participants en 3 courriels.

---

## Avant livraison (checklist)

1. [ ] Voix, langue et typographie de la marque respectées ; relecture orthographique faite.
2. [ ] Workflow nommé (déclencheur, délai, sortie) ; aucune liste statique.
3. [ ] Dates, prix et code identiques aux ads de la même phase.
4. [ ] Aucune urgence fausse, aucun rendement promis, statistique sourcée ou absente.
5. [ ] Courriel de test envoyé, approbation obtenue dans le fil avant tout envoi.
