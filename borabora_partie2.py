#!/bin/env python3

import sys,time,re
import asyncio
import random

###################################   PARTIE 2  DU PROJET  ################################### 


# ===========================================================================================#
#                               CLASSE  LOGABLE                           
# ===========================================================================================#

class Logable:
    """
    Classe de base pour disposer d'une méthode log().
    """

    def __init__(self, name, verbose, logf=None):
        """
        Constructeur de la classe
        name : est le nom de l'objet : accessoire, employe, etc
        verbose : booléen pour signifier ou non l'affichage des messages
        """
        self.name = name
        self.verbose = verbose
        self.logf = logf  # doit être un objet fichier ouvert en mode 'w'


    def log(self, msg):
        if self.verbose:
            print(f"[{self.name}] : {msg}", file=self.logf, flush=True) # logf est le fichier journal crée dans le main()
          


# ================================================================================================#
#                       Classe Accessoire  avec asyncio.Queue
# ================================================================================================#


class Accessoire(Logable):
    """Classe de base pour les objets partagés (Pic, Bar)."""
    
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
#                         Classes Pic et Bar
# =================================================================#


class Pic(Accessoire):
    """
    Un pic contient les commandes à fabriquer.
    Il peut embrocher un post-it contenant une commande
    (une liste de consommations) par-dessus les post-it
    déjà présents et libérer le premier embroché.
    """
    
    async def embrocher(self, postit):
        await self.queue.put(postit)
        self.log(f" post-it '{postit}' embroché")

    async def liberer(self):
        postit = await self.queue.get()
        self.log(f" post-it '{postit}' libéré")
        return postit


class Bar(Accessoire):
    """
    Un bar peut recevoir des commandes en attente d'être servies (évacuées).
    """
    
    async def recevoir(self, commande):
        await self.put(commande)
        self.log(f" '{commande}' posée")

    async def evacuer(self):
        commande = await self.get()
        self.log(f" '{commande}' évacuée")
        return commande


# =================================================================#
#                           Classe Employe
# =================================================================#

class Employe(Logable):
    """Classe de base modélisant un employé : serveur et bariste."""
    
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
        self.log(' prêt pour le service \n')

        
# =================================================================#
#                   Serveur(s) :  Alice, Charlie
# =================================================================#

class Serveur(Employe):
    """Le serveur prend les commandes et les sert."""

    async def prendre_commande(self, stop_event,lock):
        """
        Prend les commandes des clients et les met sur le pic. Il s'arrête quand il n'y a plus de commande.
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
            await asyncio.sleep(0.3/ self.productivity)  # pause coopérative
            
            # Variation dynamique de la productivité après chaque commande
            self.productivity *= random.uniform(0.95, 1.5) # faire varier la productivité au cours de la simulation
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
            self.log("\t\t\t Fin de service ")


# ================================================================#
#                           Bariste : Bob
# ================================================================#


class Bariste(Employe):
    """Le bariste prépare les commandes déposées sur le pic. Puis les dépose sur le bar."""

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

        # Vérifie si le bar est vide et si tous les serveurs sont occupés
        aider_serveur=False
        
        if serveurs_actifs: # si tous les serveurs sont occupés
            aucun_serveur_dispo = all(not ev.is_set() for ev in serveurs_actifs) # verifie que tous les serveurs sont occupés

            if self.bar.queue.empty() and aucun_serveur_dispo:
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
                # Le bariste dépose la commande sur le bar
                async with bar_lock:
                    await self.bar.recevoir(commande)

                    try:
                        self.pic.queue.task_done()
                    except Exception:
                        pass
                    self.log(f" La commande '{commande}' est déposée sur le bar ")



# ===============================================================================#
#                                 CLASSE  CLIENTS                
# ===============================================================================#

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
        Version asynchrone : attend le moment de la prochaine commande sans declencher le stop_event.
        Retourne une liste (commande) ou None s'il n'y a plus rien.       
        """
        
        while len(self.commandes)  > 0:
            if time.time() > self.commandes[-1][0]: # renvoit la commande au temps precis
                return self.commandes.pop()[1] # suppprime de la liste de commandes
                
            await asyncio.sleep(0.2)
        return None # sinon 


# ===========================================================================================#
#                               Fonctions utiles dans le main                           
# ===========================================================================================#


def usage():
    print(f"usage: {sys.argv[0]} fichier.txt")
    exit(1)

async def spinner_bar(stop_event):
    width = 20
    pos = 0
    direction = 1
    
    print("\n\n[SYSTEM] :  Service en cours \n")
    
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
        print("\n\n[SYSTEM] : Fin de service ! Le bar va fermer. \n")
        await asyncio.sleep(0.3)
        
        for i in range(secs, 0, -1):
            message = f"[SYSTEM] : Fermeture dans {i:02d} secondes..."
            print(message)
            log_file.flush()
            await asyncio.sleep(1)
        

        # Signaler la fermeture officielle du bar
        bar_close_event.set()
        log_file.flush()

    except asyncio.CancelledError:
        print("[SYSTEM] : Fermeture annulée !")
        log_file.write("[SYSTEM] : Fermeture annulée !\n")
        log_file.flush()
        raise  # permet à l'utilisateur de savoir qu'il y a eu annulation

  
# ===========================================================================================#
#                               Main avec async                           
# ===========================================================================================#


async def main(fcommandes):
    logf= "borabora.log" 
    stop_event = asyncio.Event() 
    bar_close_event = asyncio.Event()  #fermeture officielle du bar
    bar_open_event = asyncio.Event() # ouverture officielle du bar
    bar_lock = asyncio.Lock()
    
    lock = asyncio.Lock() # un verrou commun pour tous les serveurs
    active_serveur_event = asyncio.Event()  # True quand le serveur est occupé a servir ou à prendre des commandes
    
    with open(logf, "w", encoding="utf-8", buffering=1) as logf:
        print("\n---\n", file=logf, flush=True)
        
        # Initialisation des instances
        clients = Clients(fcommandes)
        le_pic = Pic(name="le_pic", verbose=True, logf=logf)
        le_bar = Bar(name="le_bar", verbose=True, logf=logf)
        bob = Bariste(le_pic, le_bar, clients, bar_open_event, bar_close_event, active_serveur_event=None, name="Bob", productivity=3.5, verbose=True, logf=logf)
        alice = Serveur(le_pic, le_bar, clients, bar_open_event, bar_close_event,active_serveur_event, name="Alice",productivity=1.9, verbose=True, logf=logf)
        charlie = Serveur(le_pic, le_bar, clients, bar_open_event, bar_close_event,active_serveur_event, name="Charlie",productivity=0.6, verbose=True, logf=logf)

        # Mise en place du personnel
        print("\n[SYSTEM] : Le personnel se prépare pour débuter le service !!!")
        await asyncio.sleep(1.5)

        # Ouverture officielle du bar
        print("\n[SYSTEM] :  Le Borabora ouvre ses portes ! Début de service !!! \n")
        bar_open_event.set()

        # Lancement du spinner 
        tache_spinner = asyncio.create_task(spinner_bar(stop_event))
        tache_flusher = asyncio.create_task(flusher(logf, stop_event))

        
        try:
            # Liste des événements concernant les serveurs
            serveurs_actifs = [alice.active_serveur_event, charlie.active_serveur_event]

            # Lancement des coroutines concurrentes
            await asyncio.gather(
                alice.prendre_commande(stop_event, lock),
                charlie.prendre_commande(stop_event, lock),
                bob.preparer(stop_event, bar_lock, serveurs_actifs),
                alice.servir(stop_event, lock, bar_lock),
                charlie.servir(stop_event, lock, bar_lock)
            )
                
            # Lancement du compte à rebours avant la fermeture
            await fermeture(4, bar_close_event, logf)  # fermeture dans 10 secondes
            
            # fermeture du bar
            print("\n[SYSTEM] :  Le Borabora ferme ses portes!!! \n")
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

if __name__ == "__main__":
    if len(sys.argv) != 2: 
        usage()   # #print(f"Usage: {sys.argv[0]} fichier.txt")
        sys.exit(1)

    fcommandes = sys.argv[1]
    
    asyncio.run(main(fcommandes))
