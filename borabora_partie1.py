#!/usr/bin/env python3

import sys
import time
import re
import asyncio

###################################   PARTIE 1  DU PROJET  ################################### 

# ===========================================================================================#
#                   ÉTAPE 1 —  LES CLASSES DE BASE                                                #
# ===========================================================================================#

##############################            Classe Logable

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
            print(f"[{self.name}] {msg}", file=self.logf, flush=True)

##############################            Classe Accessoire

class Accessoire(Logable):
    """Classe de base pour les objets partagés (Pic, Bar)."""
    
    def __init__(self, name="Accessoire", verbose=False, logf=None):
        Logable.__init__(self, name, verbose, logf)
        self.queue = asyncio.Queue()
        
    async def put(self, item):
        await self.queue.put(item)
        self.log(f"'{item}' ajouté à la file ({self.queue.qsize()} en attente)")

    async def get(self):
        item = await self.queue.get()
        self.log(f"'{item}' a été retiré de la file ({self.queue.qsize()} restants)")
        return item

##############################                Classe Pic

class Pic(Accessoire):
    """
    Un pic contient les commandes à fabriquer.
    Il peut embrocher un post-it contenant une commande
    (une liste de consommations) par-dessus les post-it
    déjà présents et libérer le premier embroché.
    """

    async def embrocher(self, postit):
        await self.put(postit)
        self.log(f"post-it '{postit}' embroché, {self.queue.qsize()} post-it(s) à traiter")

    async def liberer(self):
        postit = await self.get()
        self.log(f"post-it '{postit}' libéré, {self.queue.qsize()} post-it(s) à traiter")
        return postit

##############################                Classe  Bar

class Bar(Accessoire):
    """
    Un bar peut recevoir des commandes en attente d'être servies (évacuées).
    """

    async def recevoir(self, commande):
        await self.put(commande)
        self.log(f"'{commande}' posée, {self.queue.qsize()} commande(s) à servir")

    async def evacuer(self):
        commande = await self.get()
        self.log(f"'{commande}' évacuée, {self.queue.qsize()} commande(s) à servir")
        return commande

#############################               Classe Employe

class Employe(Logable):
    """
    Classe de base modélisant un employé
    """
    def __init__(self, pic, bar, clients, name, verbose, logf=None):
        Logable.__init__(self, name, verbose, logf)
        self.pic = pic
        self.bar = bar
        self.clients = clients
        self.step = 0
        self.log("prêt pour le service")

##############################               Classe SERVEUR

class Serveur(Employe):
    """Le serveur prend les commandes et les sert."""

    async def prendre_commande(self):
        while True:
            commande = await self.clients.commande()
            if commande is None:
                break
            self.log("prêt pour prendre une nouvelle commande...")
            self.log(f"j'ai la commande '{commande}'")
            self.log(f"j'écris sur le post-it '{commande}'")
            await self.pic.embrocher(commande)

    async def servir(self):
        while self.bar.queue.qsize() > 0:
            commande = await self.bar.evacuer()
            if commande:
                self.log(f"j'apporte la commande '{commande}'")
                for conso in commande:
                    self.log(f"je sers '{conso}'")
                    await asyncio.sleep(0.5)

##############################               Classe BARISTE

class Bariste(Employe):
    """Le bariste prépare les commandes déposées sur le pic.  Puis les dépose sur le bar."""

    async def preparer(self):
        while self.pic.queue.qsize() > 0:
            commande = await self.pic.liberer()
            if commande:
                self.log(f"je commence la fabrication de '{commande}'")
                for conso in commande:
                    self.log(f"je prépare '{conso}'")
                    await asyncio.sleep(0.5)
                self.log(f"la commande {commande} est prête")
                await self.bar.recevoir(commande)

#############################              Classe  CLIENTS

class Clients:
    
    def __init__(self, fname):
        commandes = []  # liste de tuples (timestamp, liste de boissons)
        start = time.time()
        fmt = re.compile(r"(\d+)\s+(.*)")
        with open(fname, "r", encoding="utf-8") as f:
            for line in f:
                found = fmt.search(line)
                if found:
                    when = int(found.group(1))
                    what = found.group(2)
                    commandes.append((start + when, what.split(",")))
        self.commandes = commandes[::-1]

    async def commande(self):
        while len(self.commandes) > 0:
            if time.time() > self.commandes[-1][0]:
                return self.commandes.pop()[1]
            await asyncio.sleep(0.2)  # Éviter la boucle CPU
        return None

############################       Main principal

def usage():
    print(f"usage: {sys.argv[0]} fichier_commandes")
    sys.exit(1)

async def main():
    if len(sys.argv) != 2:
        usage()

    fcommandes = sys.argv[1]
    
    logf_name = "borabora.log"
    
    print(f"\nEcriture en cours dans {logf_name}...\n")
    with open(logf_name, "w", encoding="utf-8") as logf:
        print("\n---\n", file=logf, flush=True)

        # Initialisation des instances
        le_pic = Pic(name="le_pic", verbose=False, logf=logf)
        le_bar = Bar(name="le_bar", verbose=False, logf=logf)
        les_clients = Clients(fcommandes)
        bob = Bariste(le_pic, le_bar, les_clients, name="Bob", verbose=True, logf=logf)
        alice = Serveur(le_pic, le_bar, les_clients, name="Alice", verbose=True, logf=logf)
        
        await asyncio.gather(
            alice.prendre_commande(),
            bob.preparer(),
            alice.servir()    
        )

    print(f"\n\t Fichier de log \"{logf_name}\" fermé.\n")

if __name__ == "__main__":
    asyncio.run(main())
