import os
import logging
import psycopg2
import asyncio
from dotenv import load_dotenv
from telegram import Bot

# Carica il file .env
load_dotenv()

# Configurazione Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurazione Database
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Link Dashboard per Report
DASHBOARD_LINK = "https://miodominio.com/dashboard"

# Inizializza il bot
bot = Bot(token=TELEGRAM_TOKEN)

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

def count_discounted_offers():
    """Conta le offerte con sconto."""
    conn = connect_db()
    if not conn:
        return 0

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM product_prices WHERE discount > 0;")
            count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logging.error(f"❌ Errore nel conteggio offerte: {e}")
        return 0

async def send_offers_notification():
    """Invia un messaggio con il link alle offerte."""
    offer_count = count_discounted_offers()

    if offer_count == 0:
        message = "⚠️ Al momento non ci sono offerte disponibili."
    else:
        message = f"🔥 {offer_count} prodotti in sconto su Amazon!\n🔗 [Vedi le offerte](https://www.amazon.it/s?k=laptop)"

    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, disable_web_page_preview=True, parse_mode="Markdown")
        logging.info("✅ Notifica offerte inviata con successo!")
    except Exception as e:
        logging.error(f"❌ Errore nell'invio del messaggio Telegram: {e}")

async def send_report_notification():
    """Invia un messaggio con il link al report sulla dashboard."""
    message = f"📊 Il tuo report prezzi è pronto!\n🔎 [Scaricalo qui]({DASHBOARD_LINK})"

    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, disable_web_page_preview=True, parse_mode="Markdown")
        logging.info("✅ Notifica report inviata con successo!")
    except Exception as e:
        logging.error(f"❌ Errore nell'invio del report Telegram: {e}")

async def main():
    """Esegue entrambe le notifiche insieme."""
    await asyncio.gather(
        send_offers_notification(),
        send_report_notification()
    )

if __name__ == "__main__":
    asyncio.run(main())  # Esegui entrambe le funzioni async nello stesso event loop
