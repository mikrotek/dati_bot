import logging
import argparse
import os
import psutil
import csv
from flask import Flask

# ✅ Gestione import con try-except per evitare crash
try:
    from api.api import api_blueprint
    from api.database import connect_db, create_tables, add_user, get_all_users
    from api.scraper import run_scraper
    from api.reports import generate_report
    from api.telegram_bot import start_telegram_bot, send_telegram_message
    from api.notifications import send_bulk_emails
except ImportError as e:
    logging.error(f"❌ Errore negli import: {e}")
    exit(1)

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Creazione dell'app Flask
app = Flask(__name__)

# ✅ Registrazione delle API
app.register_blueprint(api_blueprint)

def is_scraper_running():
    """Verifica se lo scraper è già in esecuzione per evitare conflitti."""
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if 'python' in process.info['name'] and 'scraper.py' in process.cmdline():
            return True
    return False

def save_data_to_csv():
    """Salva i dati raccolti nel database in un file CSV per analisi future."""
    conn = connect_db()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM product_prices")
        data = cur.fetchall()
        conn.close()
        filename = "data/price_data.csv"
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([desc[0] for desc in cur.description])
            writer.writerows(data)
        logger.info(f"✅ Dati salvati in {filename}")
    else:
        logger.error("❌ Errore nella connessione al database, impossibile salvare CSV.")

def initialize():
    """
    🚀 Inizializza il sistema:
    - Crea le tabelle se non esistono
    - Avvia il bot di Telegram
    - Lancia il processo di scraping se non già attivo
    - Genera report periodici
    - Invia notifiche agli utenti
    """
    logger.info("🔄 Inizializzazione del sistema...")
    
    # ✅ Connessione e creazione tabelle database
    conn = connect_db()
    if conn:
        create_tables()
        conn.close()
        logger.info("✅ Database inizializzato correttamente.")
    else:
        logger.error("❌ Errore nella connessione al database!")

    # ✅ Verifica se lo scraper è già attivo prima di avviarlo
    if not is_scraper_running():
        logger.info("🔍 Avvio dello scraping...")
        run_scraper()
    else:
        logger.info("✅ Lo scraper è già in esecuzione, salto avvio.")

    # ✅ Salvataggio dati in CSV
    save_data_to_csv()

    # ✅ Generazione di un report all'avvio
    logger.info("📊 Generazione report iniziale...")
    report_file = generate_report()
    if report_file:
        logger.info(f"✅ Report salvato in {report_file}")
    else:
        logger.warning("⚠️ Nessun report generato!")

    # ✅ Invio notifiche agli utenti
    users = get_all_users()
    if users:
        for user in users:
            send_telegram_message(user[1], "📢 Nuovi dati disponibili! Controlla il report.")
            send_bulk_emails(user[1], "📢 Nuovo Report Disponibile!", "Trovi i nuovi dati nel sistema.")
        logger.info("✅ Notifiche inviate agli utenti.")
    else:
        logger.warning("⚠️ Nessun utente registrato per ricevere notifiche.")

    # ✅ Avvio del bot Telegram
    logger.info("🤖 Avvio del bot Telegram...")
    start_telegram_bot()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--single-run", action="store_true", help="Esegui lo scraper una sola volta e poi esci")
    args = parser.parse_args()

    if args.single_run:
        logger.info("🔄 Esecuzione in modalità 'single-run'...")
        run_scraper()
        save_data_to_csv()
        logger.info("📊 Generazione report dopo lo scraping...")
        generate_report()
    else:
        # ✅ Avvio inizializzazione
        initialize()
        # ✅ Avvio server Flask (debug disattivato per produzione)
        logger.info("🌐 Avvio del server Flask...")
        app.run(host="0.0.0.0", port=5001, debug=False)
