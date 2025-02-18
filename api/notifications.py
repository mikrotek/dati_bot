import smtplib
import os
import logging
import psycopg2
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Carica le variabili di ambiente dal file .env
load_dotenv()

# Configurazione database
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Configurazione email
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def connect_db():
    """Connessione al database PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logging.error(f"❌ Errore di connessione al database: {e}")
        return None

def get_user_emails():
    """Recupera le email degli utenti dal database."""
    conn = connect_db()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users WHERE subscribed = TRUE;")
            emails = [row[0] for row in cur.fetchall()]
        conn.close()
        return emails
    except Exception as e:
        logging.error(f"❌ Errore nel recupero delle email: {e}")
        return []

def send_email(receiver_email, subject, html_content):
    """Invia un'email HTML al destinatario."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, receiver_email, msg.as_string())

        logging.info(f"✅ Email inviata con successo a {receiver_email}")
    except Exception as e:
        logging.error(f"❌ Errore durante l'invio dell'email a {receiver_email}: {e}")

def send_bulk_emails():
    """Invia email HTML a tutti gli utenti registrati e iscritti alla newsletter."""
    user_emails = get_user_emails()
    if not user_emails:
        logging.warning("⚠️ Nessun utente iscritto alla newsletter.")
        return

    subject = "📊 Il tuo Report di Monitoraggio Prezzi è pronto!"
    html_body = """
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #333;">📊 Il tuo Report di Monitoraggio Prezzi è Pronto!</h2>
            <p>Ciao,</p>
            <p>Il tuo report di monitoraggio prezzi è stato generato con successo!<br>
               Puoi scaricarlo direttamente dalla tua dashboard.</p>
            <p><a href="https://prezzo-ai-trackermik.vercel.app/index.html" style="display: inline-block;
                padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none;
                border-radius: 5px;">Vai alla Dashboard</a></p>
            <p>Grazie per aver scelto il nostro servizio!<br>
               Cordiali saluti,<br>
               <b>AI-Powered Price Tracker</b></p>
        </body>
    </html>
    """

    for email in user_emails:
        send_email(email, subject, html_body)

if __name__ == "__main__":
    send_bulk_emails()
