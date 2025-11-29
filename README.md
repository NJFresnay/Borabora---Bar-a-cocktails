# Borabora – Simulation du fonctionnement d’un bar à cocktails

De l'ouverture à la fermerture.

---

## Contexte

Ce projet **Borabora** simule le **fonctionnement d’un bar à cocktails** à travers les activités coordonnées de ses employés : un ou plusieurs **serveurs** et un **bariste**.
L’objectif est de modéliser de manière réaliste le service d’un bar, en exploitant la **programmation asynchrone** (`asyncio`), afin d'optimiser la coopérations entre les tâches concurrentes.

Chaque action ( de la prise de commande à la livraison) est **journalisée** dans un fichier `borabora.log`, permettant de suivre le déroulement complet du service.

---

## Objectifs du projet

- **Simuler** les activités d’un bar à cocktails : prise de commandes, préparation et service.
- **Modéliser** les interactions entre le(s) serveur(s) et le bariste via des files FIFO (`asyncio.Queue`).
- **Introduire la concurrence** entre les tâches grâce à `async/await` et `asyncio.gather()`.
- **Gérer les accès partagés** au pic et au bar via des verrous (`asyncio.Lock`).
- Tracer les activités en temps réel dans un **journal de logs** (`borabora.log`)
- **Modéliser la productivité** variable des employés pour simuler la fatigue.
- **Étendre** le modèle à plusieurs serveurs et à un bariste capable d’aider au service.

L'ensemble est implémenté en **Python** avec **programmation orientée objet**, combiné à l'**héritage**, la **coopération asynchronisme** (`asyncio`) et la **journalisation concurrente**.

---

## Concepts Python illustrés

- Programmation orientée objet (héritage, polymorphisme).
- Programmation asynchrone (`asyncio`).

- Utilisation des files d'attente asynchrones (`asyncio.Queue()`) pour la gestion non bloquante des files de commandes.

- Synchronisation via `asyncio.Event()` pour l'ouverture et la fermeture. De même que l'état des serveurs.

- Verrous (`asyncio.Lock()`) pour éviter les accès simultanés au bar et au pic.

- Logging en temps-réel et affichage simultané dans le terminal.

- facteur de **productivité dynamique** simulant la fatigue ou le regain d'énergie des employés. Simulation multi-agents coopératifs.

---

## Structure du projet

| Fichier                  | Rôle                              |
| ------------------------ | --------------------------------- |
| `borabora_partie1.py`    | Version séquentielle  |
| `borabora_partie2.py`    | Version asynchrone et extensions  |
| `lundi.txt`, `mardi.txt` | Fichiers de commandes clients     |
| `borabora.log`           | Journal d’exécution               |
| `README.md`              | Documentation du projet           |

---

## Fonctionnement général du bar

Le bar est animé par **trois acteurs principaux** : le serveur, le bariste et les clients.

### Serveur

- Prend les commandes des clients via la classe `Clients`.
- Embroche les commandes sur le *pic* sous forme de post-it.
- Récupère les commandes prêtes sur le *bar*.
- Sert les cocktails aux clients.
- Utilise des `Lock` pour éviter la prise de plusieurs commandes simultanées.

### Bariste

- Récupère les post-its sur le *pic*.
- Prépare les cocktails cet les dépose sur le *bar*.
- Peut **servir directement** lorsque les serveurs sont tous occupés et le bar est vide.

### Clients

- Génèrent les commandes à préparer, avec un délai(`temporisation`) entre deux commandes.
- Ces commandes alimentent indirectement le *pic* via le *serveur*.

---

### Accessoires

Les **Accessoires** assurent les interactions entre le *serveur* et le *bariste*.

| Accessoire | Rôle                               | Méthodes principales       |
| ---------- | ---------------------------------- | -------------------------- |
| `Pic`      | File des commandes à préparer     | `embrocher()`, `liberer()` |
| `Bar`      | File des commandes prêtes à servir | `recevoir()`, `evacuer()`  |

Ils sont modélisés:

- d'abord comme des **listes FIFO** (partie 1)
- puis comme des **queues asynchrones** (`asyncio.Queue()`) pour la concurrence.

---

## Schéma récapitulatif

![recap] (image.png)

---

## Modélisation objet

### Les classes principales

1. La classe **Accessoire(Logable)**

    C'est la classe commune à `Bic` et `Bar`. Elle encapsule une `asyncio.Queue()` pour gérer les files d’attente et dispose d'un logging intégré.

        ```python
        class Accessoire(Logable):
            def __init__(self, name, verbose=True, logf=None):
                super().__init__(name, verbose, logf)
                self.queue = asyncio.Queue()
                ...
        ```

2. La classe **Employe(Logable)**

    C'est la classe de base pour le `Serveur` et le `Bariste`. Cette dernière gère :
        -  les référencees partagées entre employés (**pic**, **bar** et les **clients**);
        - Les évènements globaux : bar_open_event, bar_close_event, active_serveur_event(pour savoir si un serveur est occupé ou pas)
        - Le paramètre de productivité (`productivity`) simulant la fatigue ou le regain d'énergie

3. La classe **Serveur(Employe)**

    Qui disposent de deux principales coroutines :

    - `prendre_commande()`:
        - Attend l'ouverture officielle du bar (**bar_open_event**)
        - Lit les commandes des clients (**clients.commande()**)
        - Les notes sur les posts-it et les embroche sur le pic
        - Utilise un `asyncio.Lock()` pour éviter la prise simultanée de commandes par plusieurs serveurs.

    - `servir()`:
        - Récupère les commandes prêtes au bar
        - Sert chaque consommation en respectant une temporisation dépendant de la productivité
        - Active/désactive un `active_serveur_event` pour informer le bariste de sa dsiponibilité

4. La classe **Bariste(Employe)**
    Qui contient une méthode principale `preparer()`:

    - Il récupère un post-it sur le pic en commençant par celui du bas
    - Prépare les cocktails de chaque commande un par un
    - Les dépose au bar
    - Peut **aider les serveurs** en servant directement les boissons seulement si le bar est vide et que touts les serveurs sont occupés(**aucun_serveur_dispo**)

            ```python
            aucun_serveur_libre = all(not ev.is_set() for ev in serveurs_actifs)
            ```

> Remarque: Si tous les serveurs sont occupés, alors Bob peut servir directement la commande qu'il vient de préparer.

---

## Explication du travail

Le projet est divisé en deux fichiers à exécuter. `borabora_partie1.py` concerne le début jusqu'à la transformation des listes en queues. Et, de la coopération jusqu'aux extensions est concerné par  `borabora_partie2.py`.

### Partie 1 :  Version séquentielle avec des `List`

Les tâches réalisées sont:

- Modélisation des classes de base (Logable, Accessoire, Pic, Bar, Employe).

- Lecture des commandes depuis un fichier texte (via Clients).

- Exécution séquentielle des actions : prise de commande, puis la préparation, puis le service.

- Introduction du logging pour tracer l'activité du bar.

- Exemple d'extrait de fichier de commandes `mardi.txt` :

        ```python
        0 planteur,piña colada,coco punch,mojito,daiquiri,ti-punch
        4 bloody mary,moscow mule,caïpiroska,blue lagoon,french love,greyhound,cosmopolitan
        2 tequila sunrise,margarita,cucaracha
        ```

---

### Partie 2 : Passage à l'asynchronisme

Nous introduisons la **concurrence** dans l’exécution des différentes tâches.

#### Etape 1 :  transformations en coroutines

Les principales fonctions qui ont été transformées en coroutines (avec **async def**) sont:

1. `Serveur.prendre_commande()`
2. `Serveur.servir()`
3. `Bariste.preparer()`

Puis lancées en parallèle via `asyncio.gather()`:

    ```python
    # Lancement des coroutines concurrentes
    await asyncio.gather(
        alice.prendre_commande(),
        bob.preparer(),
        alice.servir()
    )
    ```

> Remarque: Jusqu'ici tout fonctionnait bien mais on s'est rendu compte que notre programme n'exécutait plus toutes les tâches. Effectivement, les listes ne sont pas adaptées aux environnements asynchrones. Nous allons les transformer en queue ou file d'attente.

---

#### Etape 2 : Passage aux files asynchrones ou Queue

Transformation des `list` en queues `asyncio.Queue()` dans les classes Bar et Pic. Cela permet un accès sécurisé et concurrentiel.

    ```python
    self.queue = asyncio.Queue()
    ```

 A ce stade du projet, nous avons constaté deux problèmes majeurs. D'une part, lorsque le programme est terminé, l'ecriture dans le fichier log continue et il ne se ferme jamais.
 D'autre part, les acteurs n'effectuaient plus toutes leurs tâches entièrement (comme le montre l'extrait ci-dessous), et ce avant que le programme ne se termine.

    ```python
    [Bob] prêt pour le service
    [Alice] prêt pour le service
    [Alice] prêt pour prendre une nouvelle commande...
    [Alice] j'ai la commande '['planteur', 'piña colada', 'coco punch', 'mojito', 'daiquiri', 'ti-punch']'
    [Alice] j'écris sur le post-it '['planteur', 'piña colada', 'coco punch', 'mojito', 'daiquiri', 'ti-punch']'
    [Bob] je commence la fabrication de '['planteur', 'piña colada', 'coco punch', 'mojito', 'daiquiri', 'ti-punch']'
    [Bob] je prépare 'planteur'
    [Bob] je prépare 'piña colada'
    [Bob] je prépare 'coco punch'
    [Bob] je prépare 'mojito'
    [Bob] je prépare 'daiquiri'
    [Bob] je prépare 'ti-punch'
    [Bob] la commande ['planteur', 'piña colada', 'coco punch', 'mojito', 'daiquiri', 'ti-punch'] est prête
    [Alice] prêt pour prendre une nouvelle commande...
    [Alice] j'ai la commande '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']'
    [Alice] j'écris sur le post-it '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']'
    [Alice] prêt pour prendre une nouvelle commande...
    [Alice] j'ai la commande '['coca', ' fanta', ' diabolo violette']'
    [Alice] j'écris sur le post-it '['coca', ' fanta', ' diabolo violette']'
    [Alice] prêt pour prendre une nouvelle commande...
    [Alice] j'ai la commande '['tequila sunrise', 'margarita', 'cucaracha']'
    [Alice] j'écris sur le post-it '['tequila sunrise', 'margarita', 'cucaracha']'
    [Alice] prêt pour prendre une nouvelle commande...
    [Alice] j'ai la commande '['blue lagoon', 'margarita', 'cucaracha', ' moscow mule', 'caïpiroska']'
    [Alice] j'écris sur le post-it '['blue lagoon', 'margarita', 'cucaracha', ' moscow mule', 'caïpiroska']'
    ```

Ici **Alice** récupère bien toutes les commandes, par contre elle ne les sert jamais. Et **Bob** lui ne prépare que la première commande. Les tâches ne coopèrent pas.
Il est nécessaire que toutes les coroutines puissent s’arrêter avant la fermerture du journal sinon `asyncio.run(main())` ne finira jamais. Une solution est d’introduire un flag running : ici `stop_event`. Afin d"envoyer un signal au système pour fermer le journal.
"""

---

#### Etape 3 : Coopération entre les tâches

Pour rendre les tâches coopérantes, nous devons redonner la main régulièrement à la boucle d’évènements. Ceci passe par l'insertion des `await asyncio.sleep()` où c'est nécessaire.

#### Etape 4 : Prévention du burn-out des employés

Le constat qui a été fait ici est que le serveur ne réalisait pas entièrement une tâche qu'il passait déjà à une autre. Les taches étaient interrrompues. Pour éviter le burn-out des employés, nous avons insérer des verrous (`asyncio.Lock()`):

- `lock` : un verrou commun à tous les serveurs pour la prise de commande (s'assurer de prendre entièrement une commande).
- `bar_lock` : un verrou partagé entre les serveurs et le bariste pour l'accès au bar.

---

## Partie 3 : Extensions

### Extension 1 : Ajout d'un serveur

Introduction d'un second serveur `Charlie` qui travaille en parallèle avec `Alice`.

### Extension 2 : Ajout d'un facteur  de productivité

Chaque employé possède une productivité variable (`productivity`), qui modélise ainsi la fatigue ou le regain d'énergie aléatoirement:

    ```python
    await asyncio.sleep(0.2 / self.productivity)
    self.productivity = max(self.productivity * random.uniform(0.95, 1.5), 0.1)
    ```

### Extension 3: Bariste entreprenant

Le bariste `Bob` pourra aider pour le service des commandes seulement si : le bar est vide et que tous les serveurs sont occupés.

    ```python
    aucun_serveur_dispo = all(not ev.is_set() for ev in serveurs_actifs)
    if bar_vide and aucun_serveur_dispo:
        self.log("j'apporte mon aide : je sers DIRECTEMENT la commande ")
    ```

Rendant ainsi le bariste capable de s'adapter à la charge de travail. Nous avons procédons à des ajustements dans les classes `Serveur` et `Bariste`.

Dans `Bariste`  nous avons ajouté:

- une liste d'évènements `serveurs_actifs` qui se remplit dès qu'un serveur est occupé à prendre une commande ou à servir.
- Une variable `aider_serveur` qui est un signal destiné à Bob pour servir directement une commande.

Dans `Serveur` un évènement `active_serveur_event` pour signaler la non disponibilité d'un serveur.

---

#### Fonctionnalités utilitaires

Pour enrichir la simulation du bar à cocktails et la rendre plus réaliste, trois coroutines asynchrones ont été ajoutées.
Elles ne participent pas directement à la logique du serveur et du bariste, mais améliorent l’expérience visuelle, la robustesse du logging et la gestion ouverture/fermeture du bar.

1. **spinner_bar()** : animation dans la console qui permet de visualiser en temps réel que le programme est actif.
Il s'agit d'un curseur qui se déplace de gauche à droite sur une ligne droite puis rebondit. Elle s'utilise comme suit :

        ```python
        stop_event = asyncio.Event()
        spinner_task = asyncio.create_task(spinner_bar(stop_event)) # pour déclencher l'animation
        ...
        stop_event.set()  # pour arrêter l’animation
        await spinner_task

        ```

2. **flusher()** assure le nettoyage régulier du fichier `borabora.log` sur le disque même lorsque plusieurs tâches écrivent en parallèle. les coroutines appelle cette fonction toutes les 200 ms (`await asyncio.sleep(0.2)`) via `logf.flush()`. On peut alors suivre les logs en direct depuis un autre terminal et, lorsque le service se termine ( déclenché par `stop_event.set()`), le dernier flush est effectué proprement.
Elle s'utilise comme suit :

        ```python
            flush_task = asyncio.create_task(flusher(logf, stop_event))
            ...
            stop_event.set()
            await flush_task
        ```

3. **fermeture()** :
    - Affiche un message d'annonce de fermerture dnas le terminal uniquement (**[SYSTEM] : Fin de service !**).
    - Puis lance un compte à rebours sur **sec** secondes.
    - A la fin de ce compte à rebours :
        - le `bar_close_event` est activé (signalant la fin du service aux autres coroutines). L'ouverture officielle dubar est signalé par (`bar_open_event`).
        - le fichier de log est nettoyé une dernière fois.
    - En cas d'annulation `CancelledError` la fermeture est proprement interrompue et un message s'ajoute dans le log.

    Elle s'utilise comme suit :

        ```python
        bar_close_event = asyncio.Event()
        close_task = asyncio.create_task(fermeture(10, bar_close_event, logf))
        ...
        await close_task
        ```

---

## Lancement de la simulation

Avant l'exécution, assurez-vous d"avoir dans un même dossier:

- `borabora_partie1.py` : code de la partie 1 du projet.
- `borabora_partie1.py` : code des parties 2 et 3 du projet.
- Des libraires nécessaires : `sys`, `re`, `time`, `random` et `asyncio`.
- Fichiers de commandes : `lundi.txt` et `mardi.txt`.

Procédez ensuite à l'exécution  :

    ```python
    python3 borabora_partie2.py mardi.txt
    ```

Le programme crée automatiquement le journal `borabora.log` qui retrace toutes les étapes. Vous pouvez visualiser les logs en direct dans un terminal ouvert en parallèle:

- Sous linux:

        ```python
        tail -f borabora.log
        ```

- Sous windows:

        ```python
        Get-Content borabora.log -Wait
        ```
