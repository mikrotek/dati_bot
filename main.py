import time
import logging
import os
import sys
import asyncio
from flask import Flask
from api.api import api_blueprint
from dotenv import load_dotenv
from api.scraper import Scraper
from api.analytics import generate_report
from api.telegram_bot import main as telegram_main
from api.notifications import send_bulk_emails
from api.database import check_license, add_user, connect_db, create_tables

app = Flask(__name__)
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
    
# ✅ Carica variabili d'ambiente
load_dotenv()

def get_base_dir():
    """Determina il percorso base del programma, compatibile con l'eseguibile .exe."""
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")

def ensure_directories():
    """Crea le directory necessarie per il programma."""
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "analysis"), exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)

def get_scraper_mode():
    """Seleziona il metodo di scraping: API o HTML."""
    print("\n📌 Seleziona il metodo di scraping:")
    print("1️⃣ Amazon API (richiede chiave)")
    print("2️⃣ Scraping HTML")
    
    mode = input("🔍 Inserisci il numero della modalità: ").strip()
    return "api" if mode == "1" else "html" if mode == "2" else None

def get_category():
    """Seleziona la categoria predefinita per lo scraping."""
    category_mapping = {
        "1": "laptop",
        "2": "smartphone",
        "3": "smartwatch",
        "4": "tablet",
        "5": "televisori"
    }
    
    print("\n📌 Seleziona una categoria per il monitoraggio prezzi:")
    for key, value in category_mapping.items():
        print(f"{key}️⃣ {value.capitalize()}")
    
    user_input = input("🔍 Inserisci il numero della categoria: ").strip()
    return category_mapping.get(user_input, None)

def validate_license():
    """Gestisce la verifica e registrazione della licenza."""
    create_tables()
    license_key = input("🔑 Inserisci la chiave di licenza: ").strip()
    
    if not check_license(license_key):
        email = input("📩 Inserisci la tua email per registrare la licenza: ").strip()
        if add_user(email, license_key):
            print("✅ Registrazione completata! Licenza attivata con successo.")
        else:
            print("❌ Errore nella registrazione. Contatta il supporto.")
            sys.exit()

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("🚀 Programma avviato.")
    
    validate_license()
    ensure_directories()
    
    try:
        scraper_mode = get_scraper_mode()
        if not scraper_mode:
            logging.error("❌ Modalità di scraping non valida. Riprova.")
            return

        category = get_category()
        if not category:
            logging.error("❌ Categoria non valida. Riprova.")
            return
        
        scraper = Scraper(category, mode=scraper_mode)
        data = scraper.scrape()
        
        if data and len(data) > 0:
            scraper.save_to_db(data)
            logging.info("✅ Dati raccolti e salvati con successo!")
            
            generate_report()
            send_bulk_emails()
            asyncio.run(telegram_main())
            logging.info("✅ Analisi completata e notifiche inviate!")
            print("\n🎉 ✅ Analisi completata! Report e notifiche generati con successo.")
        else:
            logging.warning("⚠️ Nessun dato raccolto durante lo scraping.")

        scraper.close()
    
    except Exception as e:
        logging.error(f"❌ Errore durante l'esecuzione del programma: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--single-run":
        main()
    else:
        while True:
            main()
            print("\n🔁 Il programma ha completato tutte le operazioni. Premi Ctrl+C per uscire o attendi il prossimo ciclo.")
            time.sleep(86400)  # Esegui ogni 24 ore
