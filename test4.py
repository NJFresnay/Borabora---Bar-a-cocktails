#!/bin/env python3

import sys,time,re
import asyncio
import random

###################################   PARTIE 1  DU PROJET  ################################### 

# ===========================================================================================#
#                                   ÉTAPE 1                                                 #
# ===========================================================================================#


# ===========================================================================================#
#                               CLASSE  LOGABLE                           #
# ===========================================================================================#

class Logable:
    """
    Classe de base pour disposer d'une méthode log().
    verbose=False : les messages d'affichage ne sont pas enregistrés.
    """

    def __init__(self, name, verbose, logf=None):
        """
        Constructeur de la classe
        name : est le no, de l'objet accessoire, employe etc
        verbose : booléen pour signifier ou non l'affichage des messages
        """
        self.name = name
        self.verbose = verbose
        self.logf = logf  # doit être un objet fichier ouvert en mode 'w' ou 'a'


    def log(self, msg):
        if self.verbose:
            print(f"[{self.name}] : {msg}", file=self.logf, flush=True) # logf est le fichier journal du main()
           #self.logf.flush() # pour vider immédiatement le buffer


# =====================================================================================#
#               Classe ACCESSOIRE (sequentielle)
# =====================================================================================#


#class Accessoire(list, Logable):
#    """Classe de base pour les objets partagés (Pic, Bar)."""
#    
#    def __init__(self, name, verbose=False):
#        list.__init__(self)
#        Logable.__init__(self, name, verbose)
        
# =================================================================#
#         Classe ACCESSOIRE  avec asyncio.Queue
# =================================================================#

class Accessoire(Logable):
    def __init__(self, name="Accessoire", verbose=True, logf=None):
        super().__init__(name, verbose, logf)
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)
        self.log(f"'{item}' ajouté à la file ({self.queue.qsize()} en attente)")

    async def get(self):
        item = await self.queue.get()
        self.log(f"'{item}' a été retiré de la file ({self.queue.qsize()} restants)")
        return item

# =================================================================#
#        Classes Pic et Bar
# =================================================================#

class Pic(Accessoire):
    """Support des commandes à réaliser"""
    
    async def embrocher(self, postit):
        #self.append(postit)
        await self.put(postit)
        self.log(f" post-it '{postit}' embroché ")

    async def liberer(self):
#        if len(self) > 0:
            #postit = self.pop()
        postit = await self.get()
        self.log(f" post-it '{postit}' libéré ")
        return postit
#        else:
#            return None


class Bar(Accessoire):
    """Bar reçoit et évacue les commandes préparées."""
    
    async def recevoir(self, commande):
        #self.append(commande)
        await self.put(commande)
        self.log(f" '{commande}' posée sur le bar ")

    async def evacuer(self):
#        if len(self) > 0:
            #commande = self.pop()
        commande = await self.get()
        self.log(f" '{commande}' évacuée")
        return commande
#        else:
#            return None


# =================================================================#
#                         Classe Employe
# =================================================================#

class Employe(Logable):
    """Classe de base pour le serveur et le bariste."""
    
    def __init__(self,pic,bar,clients, bar_open_event, bar_close_event, active_serveur_event,name="Employe", verbose=False, logf=None, productivity=1.0):
        Logable.__init__(self,name, verbose, logf)
        self.pic = pic
        self.bar = bar
        self.name=name
        self.verbose= verbose
        self.clients = clients
        self.bar_open_event = bar_open_event
        self.bar_close_event = bar_close_event
        self.active_serveur_event = active_serveur_event
        self.productivity = productivity # facteur pour jauger la productivité de l"employé
        self.step = 0
        self.log('prêt pour le service \n')



        
# =================================================================#
#                   Serveur(s) :  Alice, Charlie
# =================================================================#

class Serveur(Employe):
    """Le serveur prend les commandes et les sert."""

    async def prendre_commande(self, stop_event,lock):
        """
        Prend les commandes des clients et les met sur le pic.
        S'arrête quand il n'y a plus de commande.
        """
        
        await self.bar_open_event.wait() # on attend l'ouverture officielle du bar
    
        while True:
            async with lock: # Le verrou garantit que le serveur ne prend qu'une commande à la fois
                commande = await self.clients.commande()

                if commande is None: # s'il n'y a plus de commande, envoie le signal de fin
                    self.log("\t Plus de commandes à prendre, je me repose.\n")
                    stop_event.set() # Ici on signale que plus aucune commande ne sera ajoutée
                    break  # quitte la boucle proprement

                # Prise de commande
                self.log(" prêt(e) pour prendre une nouvelle commande ...")
                self.log(f" j'ai la commande '{commande}'")
                self.log(f" j'écris sur le post-it '{commande}'")
                await self.pic.embrocher(commande)

            # On relâche le verrou avant de passer à la commande suivante
            await asyncio.sleep(0.3/ self.productivity)  # pause coopérative et réaliste
            
            # Variation dynamique de la productivité après chaque commande
            self.productivity *= random.uniform(0.95, 1.5) # faire varier energie au cours de la simulation pour simuler la fatigue ou un coup de boost
            self.productivity = max(0.1, self.productivity)  # elle ne doit pas etre nulle, jamais inférieur à 0.1

            if self.bar_close_event.is_set(): # si le bar est officiellement fermé, on stoppe la prise de commande
                break

    async def servir(self, stop_event, lock, bar_lock):
            """ Sert les commandes depuis le bar jusqu’à ce qu’il n’y ait plus rien à faire. """
            
            while True:
                try:
                    self.active_serveur_event.set()  #  serveur disponible et en action
                    
                    async with lock, bar_lock:
                        commande = await asyncio.wait_for(self.bar.evacuer(), timeout=0.2) # On attend une commande du bar, avec timeout pour vérifier stop_event
                    self.active_serveur_event.clear()  # serveur à nouveau disponible

                    self.log(f"\t j'apporte la commande '{commande}'")
                    for conso in commande:
                        self.log(f" je sers '{conso}'")
                        await asyncio.sleep(0.4 / self.productivity)
                        self.productivity = max(0.1, self.productivity * random.uniform(0.95, 1.2))

                except asyncio.TimeoutError:
                    if stop_event.is_set() and self.bar.queue.empty():
                        break
                await asyncio.sleep(0.1)
            self.log("\t\t Fin de service \t\t")


# ================================================================#
#                           Bariste : Bob
# ================================================================#
 
class Bariste(Employe):
    """Le bariste prépare les commandes déposées sur le pic."""

    async def preparer(self, stop_event, bar_lock, serveurs_actifs=None):
        """Prépare les commandes et les dépose sur le bar pour les serveurs.
           Peut aider à servir si le bar est vide et aucun serveur n'est actif.
        """
        while not stop_event.is_set() or not self.pic.queue.empty():
            if self.pic.queue.empty():
                await asyncio.sleep(0.2)
                continue

            # Récupération d’une commande du pic
            try:
                commande = await asyncio.wait_for(self.pic.liberer(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            await self.preparation(commande, bar_lock, serveurs_actifs)
            await asyncio.sleep(0.05)  # passe la main à d'autres tâches

        self.log("Plus aucune commande à préparer")

    async def preparation(self, commande, bar_lock, serveurs_actifs=None):
        """Prépare la commande normalement et la dépose sur le bar. 
        Il aide, uniquement si les serveurs sont occupés, que le pic est vide et qu'il y'a une commande à apporter"""
        
        self.log(f" je commence la fabrication de '{commande}'")

        for conso in commande:
            self.log(f" je prépare '{conso}'")
            await asyncio.sleep(0.2 / self.productivity)
            self.productivity = max(self.productivity * random.uniform(0.95, 1.05), 0.1)

        # verifie si le bar est vide et si tous les serveurs sont occupés
        aider_serveur=False
        
        if serveurs_actifs: # si tous les serveurs sont occupés
            bar_vide = self.bar.queue.empty()
            aucun_serveur_dispo = all(not ev.is_set() for ev in serveurs_actifs) # verifie que tous les serveurs sont occupés

            if bar_vide and aucun_serveur_dispo:
                aider_serveur =True

            if aider_serveur:
                self.log(f" j'apporte mon aide : je sers DIRECTEMENT la commande '{commande}'")
                for conso in commande:
                    self.log(f" \tje sers DIRECTEMENT '{conso}'")
                    await asyncio.sleep(0.8 / self.productivity)
                    self.productivity = max(self.productivity * random.uniform(0.95, 1.5), 0.1)
                try:
                    self.pic.queue.task_done()
                except Exception:
                    pass
            else:
                # deposer la commande sur le bar
                async with bar_lock:
                    await self.bar.recevoir(commande)

                    try:
                        self.pic.queue.task_done()
                    except Exception:
                        pass
                    self.log(f" La commande '{commande}' est déposée sur le bar ")



# ================================================#
#                  CLASSE  CLIENTS                #
# ================================================#

class Clients:
    def __init__(self, fname):
        commandes = [] # liste de listes de commandes
        start = time.time()
        fmt = re.compile(r"(\d+)\s+(.*)")
        with open(fname, "r", encoding="utf-8") as f:
            for line in f:
                found = fmt.search(line)
                if found:
                    when = int(found.group(1))
                    what = found.group(2)
                    commandes.append((start + when, what.split(",")))
        self.commandes = commandes[::-1]  # inversion de la pile

    async def commande(self):
        """
        Attend le moment de la prochaine commande sans declencher le stop_event.
        Retourne une liste (commande) ou None s'il n'y a plus rien.       
        """
        
        #if len(self.commandes) > 0:
        while len(self.commandes)  > 0:
        #    while True:
            if time.time() > self.commandes[-1][0]: # renvoit la commande au temps precis
                return self.commandes.pop()[1] # suppprime de la liste de commandes
                
#                else: 
#                    time.sleep(0.1) # pour eviter une boucle CPU
#       else:
#            return None
            await asyncio.sleep(0.2)
        return None # sinon 



###################################    PARTIE 2 DU PROJET    #######################


# ========================
# ETAPE 1 de la PARTIE 2 :  Rendre les tâches coopérantes avec async/await
# ========================

"""
Cette partie est le coeur du sujet.
Il s’agit de réaliser la même chose en introduisant de la concurtrence dans l’exécution des différentes tâches, 
de façon à minimiser le temps passé à ne rien faire.

Il s’agit ici d’identifier les tâches de haut niveau qui auraient intérêt à progresser harmonieusement en même temps.

Les trois taches à transformer en co-routines sont : 

1) Serveur.prendre_commande()

2) Bariste.preparer()

3) Serveur.servir()
"""


"""
Au stade la partie 2 à l'etape 1, on remarque que le fichier journal ne se ferme ja,ais bien que toutes  les commandes aient été traitées
Pour y remédier, afin que le fichier se ferme vraiment, il faut que tes coroutines puissent s’arrêter un jour, 
sinon asyncio.run(main()) ne finira jamais.

Une solution simple est d’introduire un flag running : ici 'stop_event'.
"""


# ========================
# ETAPE 2 de la PARTIE 2: Remplacer la classe list par asyncio.Queue
# ========================


# ========================
# ETAPE 3 de la PARTIE 2 :  Rendre les tâches coopérantes. En ajoutant des await asyncio.sleep(0) 
# a des endroits stratégiques où la coroutine pourrait bloquer ou boucler trop vite
# ========================


# ========================
#  ETAPE 4 de la PARTIE 2 :  A ce stade, les tâches coopèrent, mais coopèrent un peu trop.
# Certaines sont à peine entammées que le programme passe a autre chose deja. D'ou les affichages intercoupés
# Ex: 
#[Bob] :  je commence la fabrication de '['planteur', 'piña colada', 'coco punch', 'mojito', 'daiquiri', 'ti-punch']'
#[Bob] :  je prépare 'planteur'
#[Bob] :  je prépare 'piña colada'
#[Alice] :  prêt(e) pour prendre une nouvelle commande...
#[Alice] :  j'ai la commande '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']'
#[Alice] :  j'écris sur le post-it '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']'
#[le_pic] : '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']' ajouté à la file (1 en attente)
#[le_pic] :  post-it '['bloody mary', 'moscow mule', 'caïpiroska', 'blue lagoon', 'french love', 'greyhound', 'cosmopolitan']' embroché
#[Bob] :  je prépare 'coco punch'
#[Bob] :  je prépare 'mojito'  

# Alice n’est pas multi-tâche. Pour éviter le burn-out, elle devrait terminer une tâche avant d’en commencer une autre.

#Modifier le code de façon à ménager la santé du personnel. On va rajouter des verrous dans la classe Serveur
# ========================



###################################    PARTIE 3 DU PROJET    #######################



# ========================
#         Extension 1 : Le bar est réputé, les finances sont bonnes, recruter est possible. Ajouter 1 second serveur au bar.
# ========================



# ========================
#         Extension 2 : 
# 
# Dans la réalité, tout le monde ne travaille pas au même rythme. Tenir compte du dynamisme du personnel, 
#  en introduisant une information de productivité (en pratique, ce sera une temporisation propre dans les attentes) pour chaque personne
# L’idée est d’introduire un rythme propre à chaque employé, pour que les actions de chacun (prise de commande, préparation, service) soient plus réalistes et différentes
# ========================



# ========================
#         Extension 3 : Les consommateurs sont toujours plus nombreux. Le bariste souhaite aider le
# ou les serveurs lorsque cela est possible. Pour cela, il va servir de temps en temps, lorsque le pic est vide, les consommations qu’il 
# prépare (directement, sans passer par des post-it).
# Ajouter cette nouvelle tâche au bariste.
# ========================





# ========================
# MAIN PRINCIPAL
# ========================

def usage():
    print(f"usage: {sys.argv[0]} fichier")
    exit(1)

async def spinner_bar(stop_event):
    width = 20
    pos = 0
    direction = 1
    
    print("\n Service en cours \n")
    
    while not stop_event.is_set():
        
        bar = ["-"] * width
        bar[pos] = "#"
        print(f"{ ' '.join(bar)} ", end="\r", flush=True)
        
        pos += direction
        if pos == width - 1 or pos == 0:
            direction *= -1
        await asyncio.sleep(0.05)
        

async def flusher(logf, stop_event):
    while not stop_event.is_set():
        logf.flush()
        await asyncio.sleep(0.2)
    logf.flush()

          
          
async def fermeture(secs, bar_close_event, log_file):
    """
    Fonction de fermeture du bar.
    Affiche un compte à rebours et écrit dans le log.
    Gère proprement l'annulation.
    """
    try:
        for i in range(secs, 0, -1):
            message = f"[SYSTEM] : Fermeture dans {i:02d} secondes..."
            print(message)
           # log_file.write(message + "\n")
            log_file.flush()
            await asyncio.sleep(1)

        # Signaler la fermeture
        bar_close_event.set()
        print("[SYSTEM] : Bar fermé !")
        #log_file.write("\n[SYSTEM] : Bar fermé !\n")
        log_file.flush()

    except asyncio.CancelledError:
        print("[SYSTEM] : Fermeture annulée !")
        log_file.write("[SYSTEM] : Fermeture annulée !\n")
        log_file.flush()
        raise  # permet à l'appelant de savoir qu'il y a eu annulation


    
#async def main():
#    await asyncio.gather(
#        alice.prendre_commande(stop_event),
#        bob.preparer(stop_event),
#        alice.servir(stop_event)
#    )
    
    
    
# ========================
#                                            MAIN ASYNC
# ========================

async def main(fcommandes):
    logf= "borabora.log" 
    stop_event = asyncio.Event() 
    bar_close_event = asyncio.Event()  #fermeture officielle du bar
    bar_open_event = asyncio.Event() # ouverture officielle du bar
    bar_lock = asyncio.Lock()
    
    lock = asyncio.Lock() # un verrou commun pour tous les serveurs
    active_serveur_event = asyncio.Event()  # True quand le serveur est entrain de servir

    # Ouverture du fichier lo
    
    with open(logf, "w", encoding="utf-8", buffering=1) as logf:
        
        # Initialisation des instances
        clients = Clients(fcommandes)
        le_pic = Pic(name="le_pic", verbose=True, logf=logf)
        le_bar = Bar(name="le_bar", verbose=True, logf=logf)
        bob = Bariste(le_pic, le_bar, clients, bar_open_event, bar_close_event, active_serveur_event=None, name="Bob", productivity=3.5, verbose=True, logf=logf)
        alice = Serveur(le_pic, le_bar, clients, bar_open_event, bar_close_event,active_serveur_event, name="Alice",productivity=1.8, verbose=True, logf=logf)
        charlie = Serveur(le_pic, le_bar, clients, bar_open_event, bar_close_event,active_serveur_event, name="Charlie",productivity=0.6, verbose=True, logf=logf)

        # Mise en place
        print("\n [SYSTEM] : Le personnel se prépare pour débuter le service !!!")
        await asyncio.sleep(1.5)

        # Ouverture officielle du bar
        print("\n [SYSTEM] :  Le Borabora ouvre ses portes ! Début de service !!! \n")
        bar_open_event.set()

        # Lancement du spinner 
        tache_spinner = asyncio.create_task(spinner_bar(stop_event))
        tache_flusher = asyncio.create_task(flusher(logf, stop_event))

        
        try:
            # Liste des événements concernant les serveurs
            serveurs_actifs = [alice.active_serveur_event, charlie.active_serveur_event]

            await asyncio.gather(
                alice.prendre_commande(stop_event, lock),
                charlie.prendre_commande(stop_event, lock),
                bob.preparer(stop_event, bar_lock, serveurs_actifs),
                alice.servir(stop_event, lock, bar_lock),
                charlie.servir(stop_event, lock, bar_lock)
            )
                
                
            # Lancement des coroutines concurrentes
                
            # Le service dure un certain temps (simulation)
            #await asyncio.sleep(15)
                
            # --- Animation de fermeture
            #await animation_fermeture()
                
            # --- Lancement du compte à rebours avant fermeture
            await fermeture(4, bar_close_event, logf)  # fermeture dans 10 secondes
            
            # fermeture du bar
            print("\n\n [SYSTEM] :  Le Borabora ferme ses portes. Fin de service !!! \n")
            bar_close_event.set() # signal de fermeture du bar
            
            stop_event.set() # signal de fin de service
            await tache_spinner
            
        finally :
            stop_event.set() 
            tache_spinner.cancel()
            try:
                await tache_spinner
                await tache_flusher
            except asyncio.CancelledError:
                pass
                 
    print("\nFermeture du fichier journal.\n")

#if __name__ == "__main__":
#    if len(sys.argv) != 2:
#        usage()
#    fcommandes = sys.argv[1]
#    
#    logf = "borabora.log"
#    
#    # Event global pour signaler la fin
#    stop_event = asyncio.Event()
    
#    les_clients = Clients(fcommandes)
 #   le_pic = Pic(name="le_pic", logf=logf,  verbose=True)
#    le_bar = Bar(name="le_bar",logf=logf,  verbose=True)
#    bob = Bariste(le_pic, le_bar, les_clients, name="Bob", verbose=True)
#    alice = Serveur(le_pic, le_bar, les_clients, name="Alice", verbose=True)
    
    
#    with open(logf, "w", encoding="utf-8") as logf:
#        asyncio.run(main())
#        #finally:
#    print("Fermeture du bar")  # ici logf sera automatiquement fermé





# ========================================================================#
#
# ========================================================================#
if __name__ == "__main__":
    if len(sys.argv) != 2: 
        usage()   # #print(f"Usage: {sys.argv[0]} fic.txt")
        sys.exit(1)

    fcommandes = sys.argv[1]
    asyncio.run(main(fcommandes))
