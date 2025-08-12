import csv
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class VeilleProcessor:
    def __init__(self, filename="veille.csv"):
        self.filename = filename
        self.groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def summarize_text_with_groq(self, text):
        """Génère un résumé de texte en utilisant l'API de Groq."""
        try:
            chat_completion = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": f"Résume le texte suivant en français, en 3 ou 4 phrases maximum, en insistant sur les points clés :\n\n{text}",
                    }
                ],
                model="llama3-8b-8192",
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Erreur lors de la génération du résumé avec Groq : {e}")
            return "Résumé non disponible."

    def process_articles(self):
        """Lit, traite, et met à jour le fichier CSV."""
        if not os.path.exists(self.filename):
            print(f"Le fichier {self.filename} n'existe pas. Assurez-vous d'abord de lancer le scraping.")
            return

        articles_to_process = []
        updated_articles = []
        
        with open(self.filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            
            if "Résumé" not in header:
                header.append("Résumé")
            
            for row in reader:
                row.extend([''] * (len(header) - len(row)))
                article_data = dict(zip(header, row))
                
                if article_data.get("Etat") == "non traité":
                    articles_to_process.append(article_data)
                updated_articles.append(article_data)

        if not articles_to_process:
            print("Aucun article avec l'état 'non traité' n'a été trouvé.")
            return

        print(f"{len(articles_to_process)} articles à traiter trouvés...")
        
        for article in articles_to_process:
            print(f"Traitement de l'article : '{article['Titre']}'")
            resume = self.summarize_text_with_groq(article['Contenu'])
            
            article['Etat'] = "traité"
            article['Résumé'] = resume
        
        with open(self.filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            writer.writerows(updated_articles)

        print(f"Traitement terminé. {len(articles_to_process)} articles ont été mis à jour dans '{self.filename}'.")