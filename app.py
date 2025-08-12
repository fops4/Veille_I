from datetime import datetime, timedelta
import sys
from auto import ArticleScraper
from auto1 import VeilleProcessor
from auto2 import VeilleMailer

def main():
    """
    Fonction principale pour orchestrer l'ensemble du processus de veille.
    """
    print("🤖 Début du processus de veille automatisée.")

    # --- Étape 1 : Scraping des articles ---
    print("\n--- Lancement du scraping des nouveaux articles ---")
    
    # Définition de la date limite : la date du jour moins une semaine
    date_limite = datetime.now() - timedelta(weeks=1)
    base_url_to_scrape = "https://www.actuia.com/actualite/page/"
    
    print(f"Date limite de scraping : {date_limite.strftime('%d/%m/%Y')}")

    scraper = ArticleScraper(base_url_to_scrape, date_limite)
    scraper.scrape_articles()
    scraper.save_to_csv()
    
    # --- Étape 2 : Traitement des articles avec Groq ---
    print("\n--- Lancement du traitement des articles avec Groq ---")
    processor = VeilleProcessor()
    processor.process_articles()
    
    # --- Étape 3 : Envoi de l'e-mail de synthèse ---
    print("\n--- Lancement de l'envoi de l'e-mail ---")
    mailer = VeilleMailer()
    articles_to_send = mailer.get_articles_to_email()
    mailer.send_email(articles_to_send)

    print("\n🎉 Fin du processus de veille. La chaîne est terminée.")

if __name__ == "__main__":
    main()