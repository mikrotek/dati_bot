import time
import logging
import os
import sys
import asyncio
from dotenv import load_dotenv
from src.scraper import Scraper
from src.analytics import generate_report
from src.telegram_bot import main as telegram_main
from src.notifications import send_bulk_emails
from src.database import check_license, add_user, connect_db, create_tables

# ✅ Carica variabili d'ambiente
load_dotenv()

def get_base_dir():
    """Determina il percorso base del programma, compatibile con l'eseguibile .exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")

def ensure_directories():
    """Crea le directory necessarie per il programma."""
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "analysis"), exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

def get_category():
    """Chiede all'utente di selezionare una categoria predefinita per lo scraping."""
    category_mapping = {
        "1": "laptop",
        "2": "smartphone",
        "3": "smartwatch",
        "4": "tablet",
        "5": "televisori"
    }

    print("\n📌 Seleziona una categoria per il monitoraggio prezzi:")
    print("1️⃣ Laptop\n2️⃣ Smartphone\n3️⃣ Smartwatch\n4️⃣ Tablet\n5️⃣ Televisori")

    user_input = input("🔍 Inserisci il numero della categoria: ").strip()

    if user_input in category_mapping:
        return category_mapping[user_input]
    else:
        logging.error("❌ Categoria non valida. Riprova.")
        return None

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("🚀 Programma avviato.")

    # ✅ Creazione e aggiornamento delle tabelle nel database
    create_tables()

    # ✅ Verifica della chiave di licenza
    try:
        license_key = input("🔑 Inserisci la chiave di licenza: ").strip()
    except Exception as e:
        logging.error(f"⚠️ Errore nella lettura della chiave di licenza: {e}")
        sys.exit()

    if not check_license(license_key):
        try:
            email = input("📩 Inserisci la tua email per registrare la licenza: ").strip()
        except Exception as e:
            logging.error(f"⚠️ Errore nella lettura dell'email: {e}")
            sys.exit()

        if add_user(email, license_key):
            print("✅ Registrazione completata! Licenza attivata con successo.")
        else:
            print("❌ Errore nella registrazione. Contatta il supporto.")
            sys.exit()

    ensure_directories()

    try:
        # ✅ Seleziona la categoria da monitorare
        category = get_category()
        if not category:
            return

        scraper = Scraper(category)
        data = scraper.scrape()

        # ✅ Salvataggio diretto dei dati nel database
        if data and len(data) > 0:
            scraper.save_to_db(data)
            logging.info("✅ Dati raccolti e salvati con successo!")

            # ✅ Generazione report, notifiche email e Telegram
            generate_report()
            send_bulk_emails()  # 📧 INVIA EMAIL
            asyncio.run(telegram_main())  # 📢 INVIA TELEGRAM
            logging.info("✅ Analisi completata e notifiche inviate!")
            print("\n🎉 ✅ Analisi completata! Report e notifiche generati con successo.")
        else:
            logging.warning("⚠️ Nessun dato raccolto durante lo scraping.")

        scraper.close()

    except Exception as e:
        logging.error(f"❌ Errore durante l'esecuzione del programma: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--single-run":
        main()  # Esegui una sola volta
    else:
        while True:
            main()
            print("\n🔁 Il programma ha completato tutte le operazioni. Premi Ctrl+C per uscire o attendi il prossimo ciclo.")
            time.sleep(86400)  # Esegui ogni 24 ore
