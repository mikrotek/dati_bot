import logging
import time
from api.scraper_api import get_special_offers, get_product_data_from_api
from api.scraper_html_api import scrape_amazon_products
from api.database import create_tables, get_all_products
from api.notifications import send_bulk_emails
from api.reports import generate_report

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    """
    🚀 Avvia il processo principale: 
    - Scraping API + HTML 
    - Salvataggio dati nel database
    - Notifiche agli utenti
    - Generazione report
    """
    logger.info("🔄 Avvio AI-Powered Price Tracker...")

    # ✅ Creazione delle tabelle nel database (se non esistono)
    create_tables()

    # ✅ Step 1: Scraping API Amazon (recupero offerte speciali)
    logger.info("🛒 Recupero offerte speciali via API Amazon...")
    get_special_offers()

    # ✅ Step 2: Scraping HTML (recupero prodotti da categorie selezionate)
    categorie = ["laptop", "tablet", "smartphone", "tv"]
    for categoria in categorie:
        logger.info(f"🔎 Scraping categoria: {categoria}")
        scrape_amazon_products(categoria)
        time.sleep(2)  # Evita blocchi su Amazon

    # ✅ Step 3: Recupero dati dal database per verificare i prodotti estratti
    prodotti = get_all_products()
    logger.info(f"📊 Numero totale di prodotti nel database: {len(prodotti)}")

    # ✅ Step 4: Generazione report CSV con tutti i dati estratti
    report_path = generate_report()
    if report_path:
        logger.info(f"📁 Report generato: {report_path}")

    # ✅ Step 5: Invio notifiche via email agli utenti registrati
    logger.info("📩 Invio email agli utenti con le offerte aggiornate...")
    send_bulk_emails()

    logger.info("✅ Processo completato con successo!")

if __name__ == "__main__":
    main()
