import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class VeilleMailer:
    def __init__(self, filename="veille.csv"):
        self.filename = filename

    def get_articles_to_email(self):
        """
        Lit le fichier CSV, récupère les articles dont l'état est "traité",
        et met à jour leur état à "envoyé" pour éviter les doublons.
        """
        if not os.path.exists(self.filename):
            print(f"Le fichier '{self.filename}' n'a pas été trouvé.")
            return [], []

        articles_to_email = []
        updated_rows = []
        file_header = []

        with open(self.filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            file_header = next(reader)
            
            for row in reader:
                if len(row) > 4 and row[4] == "traité":
                    article = {
                        "titre": row[0],
                        "date": row[1],
                        "resume": row[5] if len(row) > 5 else "Résumé non disponible.",
                        "lien_video": row[3] if len(row) > 3 and row[3] else "Aucun lien vidéo.",
                    }
                    articles_to_email.append(article)
                    row[4] = "envoyé"
                updated_rows.append(row)
        
        if articles_to_email:
            with open(self.filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(file_header)
                writer.writerows(updated_rows)
            
        return articles_to_email

    def send_email(self, articles):
        """Envoie un e-mail avec le récapitulatif des articles."""
        if not articles:
            print("Aucun article traité n'est prêt à être envoyé par e-mail.")
            return

        email_sender = os.getenv("EMAIL_SENDER")
        email_recipient = os.getenv("EMAIL_RECIPIENT")
        email_password = os.getenv("EMAIL_PASSWORD")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT"))

        date_du_jour = datetime.now().strftime("%d/%m/%Y")
        sujet = f"Synthèse de veille IA du {date_du_jour}"
        
        corps = f"Bonjour,\n\nVoici le résumé des articles de veille traités aujourd'hui :\n\n"
        for article in articles:
            corps += f"--- Titre : {article['titre']} ---\n"
            corps += f"Date : {article['date']}\n"
            corps += f"Résumé : {article['resume']}\n"
            if article['lien_video'] != "Aucun lien vidéo.":
                corps += f"Lien Vidéo : {article['lien_video']}\n"
            corps += "\n\n"
        
        corps += "Bonne lecture !\n\nCordialement,\nVotre robot de veille."

        message = MIMEMultipart()
        message['From'] = email_sender
        message['To'] = email_recipient
        message['Subject'] = sujet
        message.attach(MIMEText(corps, 'plain'))
        
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_sender, email_password)
                server.send_message(message)
            print("E-mail envoyé avec succès !")
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'e-mail : {e}")