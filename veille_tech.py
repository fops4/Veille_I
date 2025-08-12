import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import schedule
import logging

# --- Configuration ---
# Remplacez cette URL par l'URL du blog que vous souhaitez surveiller
# ATTENTION : Assurez-vous d'avoir le droit de scraper ce site et de respecter son fichier robots.txt
# Pour cet exemple, nous allons utiliser un placeholder. En production, remplacez-le par un VRAI blog.
BLOG_URL = "https://www.forbes.fr/technologie/" # Remplacez par un vrai blog tech !
CSV_FILE = "articles_veille_tech.csv"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 VeilleTechScraper/1.0" # Bonnes pratiques
REQUEST_DELAY = 5 # Délai en secondes entre les requêtes (pour ne pas surcharger le serveur)

# Configuration de la journalisation pour suivre l'activité du script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Fonction de Scraping ---
def scrape_blog():
    logging.info(f"Démarrage du scraping de : {BLOG_URL}")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br"
    }
    
    try:
        response = requests.get(BLOG_URL, headers=headers, timeout=10)
        response.raise_for_status()  # Lève une exception pour les codes d'état HTTP d'erreur (4xx ou 5xx)
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Erreur lors de la requête HTTP vers {BLOG_URL}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    
    # --- LOGIQUE DE SÉLECTION DES ARTICLES ---
    # C'est la partie la plus critique et la plus spécifique à chaque site !
    # Vous devrez adapter ces sélecteurs CSS ou la logique de recherche en fonction de la structure HTML du blog.
    # Utilisez les outils de développement de votre navigateur (Inspecter l'élément) pour trouver les bons sélecteurs.
    
    # Exemple générique : Cherche des balises <article> avec une classe spécifique
    # ou des div contenant des liens d'articles.
    # Ici, on va chercher des éléments qui pourraient représenter un article de blog.
    # C'est un exemple, vous DEVEZ l'adapter au site ciblé.
    
    # Les articles peuvent être dans des balises <article>, ou des <div> avec une classe spécifique
    # ou des <li> dans une liste.
    # On va tenter une approche commune en cherchant des liens qui semblent être des articles.
    
    # Recherchons des éléments qui contiennent un titre (h2, h3) et un lien (a)
    # C'est une approche heuristique, elle peut nécessiter des ajustements.
    
    potential_article_blocks = soup.find_all(['h2', 'h3', 'div', 'article'], class_=lambda x: x and ('post' in x or 'article' in x or 'entry' in x))
    
    if not potential_article_blocks:
        logging.warning(f"Aucun bloc d'article trouvé avec les sélecteurs par défaut sur {BLOG_URL}. Vérifiez la structure HTML.")
        # Tentative d'une approche plus générique si la première échoue
        # Recherche de tous les liens (a) qui pourraient être des articles
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Filtrer les liens qui ressemblent à des articles (contenant 'article', 'post', année, titre...)
            if ('/article/' in href or '/post/' in href or len(href.split('/')) > 3) and not href.startswith(('#', 'mailto:', 'tel:')):
                title = link.get_text(strip=True)
                if title and len(title) > 10: # Titre suffisamment long pour être un article
                    # Tentez de trouver un résumé à proximité (par exemple, un paragraphe suivant)
                    summary_elem = link.find_next_sibling(['p', 'div'])
                    summary = summary_elem.get_text(strip=True) if summary_elem else "Non disponible"
                    
                    # S'assurer que l'URL est absolue
                    if not href.startswith(('http://', 'https://')):
                        href = requests.compat.urljoin(BLOG_URL, href)
                    
                    articles.append({
                        "Titre": title,
                        "Lien": href,
                        "Résumé": summary
                    })
        logging.info(f"Trouvé {len(articles)} articles potentiels via les liens génériques.")

    else:
        for block in potential_article_blocks:
            title_elem = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            link_elem = block.find('a', href=True)
            summary_elem = block.find('p', class_=lambda x: x and ('excerpt' in x or 'summary' in x or 'description' in x))
            
            title = title_elem.get_text(strip=True) if title_elem else "Titre inconnu"
            link = link_elem['href'] if link_elem else "Lien inconnu"
            summary = summary_elem.get_text(strip=True) if summary_elem else "Non disponible"
            
            # S'assurer que l'URL est absolue
            if link and not link.startswith(('http://', 'https://')):
                link = requests.compat.urljoin(BLOG_URL, link)
            
            if title != "Titre inconnu" and link != "Lien inconnu":
                articles.append({
                    "Titre": title,
                    "Lien": link,
                    "Résumé": summary
                })
        logging.info(f"Trouvé {len(articles)} articles via les blocs spécifiques.")

    return articles

# --- Fonction de gestion du CSV ---
def update_csv(new_articles):
    logging.info("Vérification et mise à jour du fichier CSV.")
    
    # Charger les articles existants
    existing_articles_df = pd.DataFrame()
    if os.path.exists(CSV_FILE):
        try:
            existing_articles_df = pd.read_csv(CSV_FILE)
            logging.info(f"Trouvé {len(existing_articles_df)} articles existants dans le CSV.")
        except pd.errors.EmptyDataError:
            logging.warning("Le fichier CSV existe mais est vide.")
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du CSV : {e}")
            existing_articles_df = pd.DataFrame() # Recommencer avec un DataFrame vide

    new_articles_df = pd.DataFrame(new_articles)
    
    if new_articles_df.empty:
        logging.info("Aucun nouvel article à ajouter.")
        return

    # Identifier les nouveaux articles (ceux dont le lien n'est pas déjà dans le CSV)
    # Assurez-vous que la colonne 'Lien' existe dans les deux DataFrames pour la comparaison
    if not existing_articles_df.empty and 'Lien' in existing_articles_df.columns and 'Lien' in new_articles_df.columns:
        merged_df = pd.merge(new_articles_df, existing_articles_df, on='Lien', how='left', indicator=True)
        fresh_articles_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns='_merge')
    else:
        # Si le CSV est vide ou n'a pas la colonne 'Lien', tous les articles sont considérés comme nouveaux
        fresh_articles_df = new_articles_df

    if fresh_articles_df.empty:
        logging.info("Aucun nouvel article à ajouter au CSV.")
    else:
        logging.info(f"Ajout de {len(fresh_articles_df)} nouveaux articles au CSV.")
        # Ajouter les nouveaux articles au fichier CSV
        fresh_articles_df.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False, encoding='utf-8')
        logging.info(f"CSV mis à jour. Nombre total d'articles : {len(pd.read_csv(CSV_FILE)) if os.path.exists(CSV_FILE) else len(fresh_articles_df)}")

# --- Fonction principale de la tâche ---
def job():
    logging.info("Début de la tâche de veille technologique.")
    articles_found = scrape_blog()
    if articles_found:
        update_csv(articles_found)
    else:
        logging.warning("Aucun article n'a été scrapé pour la mise à jour.")
    logging.info("Fin de la tâche de veille technologique.")

# --- Planification ---
if __name__ == "__main__":
    logging.info("Script de veille technologique démarré. Planification de la tâche quotidienne.")
    
    # Exécuter la tâche une première fois au démarrage
    job() 
    
    # Planifier l'exécution de la tâche
    # Par exemple, tous les jours à 10h00
    schedule.every().day.at("10:00").do(job)
    # Ou toutes les 5 minutes pour des tests (pourrait surcharger le site !)
    # schedule.every(5).minutes.do(job) 

    logging.info("Tâche planifiée. Le script va maintenant s'exécuter en boucle pour attendre le prochain déclenchement.")
    while True:
        schedule.run_pending()
        time.sleep(1) # Vérifie toutes les secondes si une tâche est à exécuter