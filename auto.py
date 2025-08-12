import csv
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class ArticleScraper:
    def __init__(self, base_url, date_limite):
        self.base_url = base_url
        self.date_limite = date_limite
        self.articles_data = []
        self.existing_titles = set()

    def _get_page_content(self, url):
        """Récupère le contenu HTML d'une URL donnée."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération de la page {url}: {e}")
            return None

    def _get_article_details(self, article_url):
        """Récupère le contenu détaillé et les liens vidéo d'un article."""
        html_content = self._get_page_content(article_url)
        if not html_content:
            return "Erreur de récupération", None
        
        soup_article = BeautifulSoup(html_content, 'html.parser')
        
        content_containers = soup_article.find_all('div', itemprop="articleBody")
        if len(content_containers) > 1:
            full_content_container = content_containers[1]
            contenu = full_content_container.text.strip()
        else:
            contenu = "Contenu non trouvé"
        
        video_link = None
        iframe_tag = soup_article.find('iframe')
        if iframe_tag and 'src' in iframe_tag.attrs:
            video_link = iframe_tag['src']
        
        return contenu, video_link

    def _load_existing_articles(self, filename="veille.csv"):
        """Charge les articles existants pour éviter les doublons."""
        if os.path.exists(filename):
            with open(filename, 'r', newline='', encoding='utf-8') as fichier_csv:
                reader = csv.reader(fichier_csv)
                header = next(reader, None)
                if header:
                    for row in reader:
                        if row:
                            self.existing_titles.add(row[0])
            print(f"Fichier '{filename}' existant trouvé. {len(self.existing_titles)} articles chargés.")

    def scrape_articles(self):
        """Boucle principale pour la pagination et le scraping des articles."""
        self._load_existing_articles()
        
        scraping_complete = False
        page_num = 1
        while not scraping_complete:
            url = f"{self.base_url}{page_num}/"
            print(f"Scraping de la page : {url}")
            
            html_content = self._get_page_content(url)
            if not html_content:
                break
                
            soup = BeautifulSoup(html_content, 'html.parser')
            articles_html = soup.find_all('article', class_='bg-white rounded-lg shadow-md overflow-hidden mb-8')

            if not articles_html:
                print("Aucun article trouvé sur cette page. Fin du scraping.")
                break

            for article in articles_html:
                try:
                    title_link_tag = article.find('h2').find('a')
                    titre = title_link_tag.text.strip()
                    article_link = title_link_tag['href']
                    
                    if titre in self.existing_titles:
                        print(f"Article '{titre}' déjà présent. Fin du scraping des nouvelles pages.")
                        scraping_complete = True
                        break

                    date_element = article.find('div', class_='flex justify-between items-center text-sm text-gray-500').find('span')
                    date_str = date_element.text.strip()
                    date_article = datetime.strptime(date_str, "%d/%m/%Y")
                    
                    if date_article >= self.date_limite:
                        if article_link.startswith('http'):
                            full_article_url = article_link
                        else:
                            full_article_url = "https://www.actuia.com" + article_link
                            
                        contenu, video_link = self._get_article_details(full_article_url)
                        self.articles_data.append([titre, date_str, contenu, video_link, "non traité", ''])
                    else:
                        scraping_complete = True
                        break
                except (AttributeError, ValueError, KeyError):
                    print(f"Un article a été ignoré sur la page {page_num} à cause d'une structure invalide.")
                    continue
            
            if not scraping_complete:
                page_num += 1

    def save_to_csv(self):
        """Met à jour le fichier CSV avec les nouvelles données scrapées."""
        filename = "veille.csv"
        file_exists = os.path.exists(filename)
        
        with open(filename, 'a' if file_exists else 'w', newline='', encoding='utf-8') as fichier_csv:
            writer = csv.writer(fichier_csv)
            
            if not file_exists:
                writer.writerow(['Titre', 'Date', 'Contenu', 'Lien Video', 'Etat', 'Résumé'])
            
            writer.writerows(self.articles_data)
        
        print(f"Le scraping est terminé. {len(self.articles_data)} nouveaux articles ont été ajoutés à {filename}")