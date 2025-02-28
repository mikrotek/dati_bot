import logging
import sys
import time
import requests
import asyncio
import os
from dotenv import load_dotenv

# ✅ Carica le variabili di ambiente
load_dotenv()

# ✅ Moduli personalizzati
from api.database import Database
from api.notifications import send_bulk_emails
from api.telegram_bot import start_telegram_bot
from api.reports import generate_report
from api.scraper_html_api import get_complete_product_data
from api.scraper_api import get_affiliate_link  # IMPORT DIRETTO

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Verifica licenza
def validate_license(key):
    """🔐 Verifica la chiave di licenza con il server."""
    try:
        response = requests.get(f"http://127.0.0.1:5000/api/validate_license?key={key}", timeout=10)
        if response.status_code == 200 and response.json().get("valid"):
            return True
        else:
            logging.warning("❌ Chiave di licenza non valida.")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠️ Errore di connessione al server delle licenze: {e}")
        return None

# ✅ Funzione principale per eseguire le operazioni del sistema
def execute_main_tasks():
    """🔧 Esegue le operazioni principali senza scraping diretto."""
    try:
        db = Database()

        # ✅ Generazione report
        logging.info("📊 Generazione report in corso...")
        generate_report()

        # ✅ Invio notifiche email
        logging.info("📩 Invio email agli utenti...")
        send_bulk_emails()

        # ✅ Avvio Bot Telegram
        logging.info("🤖 Avvio bot Telegram...")
        asyncio.run(start_telegram_bot())

        # ✅ Aggiornamento dati prodotti (Scraping + API Amazon)
        logging.info("🛒 Aggiornamento prodotti in corso...")
        categories = ["monitor", "tv", "laptop", "smartphone"]  # Aggiungi altre categorie se necessario
        for category in categories:
            get_complete_product_data(category, search_type="search")

        # ✅ Aggiornamento link affiliati tramite API Amazon
        logging.info("🔗 Aggiornamento link affiliati...")
        asins = db.get_all_asins()
        for asin in asins:
            link = get_affiliate_link(asin)
            if link and link != "N/A":
                db.update_affiliate_link(asin, link)

        logging.info("✅ Tutte le operazioni sono state completate con successo!")
        print("🎉 Programma completato con successo!")

    except Exception as e:
        logging.error(f"❌ Errore critico: {e}")
        sys.exit(1)

# ✅ Main loop
def main():
    """🔑 Verifica la licenza e avvia il programma."""
    logging.info("🚀 Programma avviato. In attesa di esecuzione...")

    # ✅ Verifica licenza all'avvio
    license_key = input("🔑 Inserisci la chiave di licenza: ").strip()
    if not validate_license(license_key):
        print("❌ Licenza non valida o errore di connessione.")
        sys.exit()

    execute_main_tasks()

# ✅ Esecuzione del programma
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--single-run":
        main()
    else:
        while True:
            main()
            logging.info("🔄 Attesa 24 ore prima della prossima esecuzione.")
            time.sleep(86400)
