import logging
from database import get_product_by_asin, save_product_data, update_product_in_db
from scraper_api import get_product_data_from_api
from scraper_html import scrape_product_data
from scrap_html import scrape_amazon

# Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_complete_product_data(asin):
    """
    Recupera i dati di un prodotto dal database, API Amazon o tramite scraping HTML.
    """
    logger.info(f"🔎 Controllo il database per ASIN: {asin}")
    product = get_product_by_asin(asin)
    
    if product:
        logger.info("✅ Prodotto trovato nel database.")

    # Tentativo API Amazon
    logger.info(f"📡 Test API Amazon per ASIN: {asin}")
    product_data_api = get_product_data_from_api([asin])
    
    if product_data_api:
        logger.info("✅ Dati API Amazon ricevuti.")
        product_data_api = product_data_api[0]
        if product_data_api.get("Prezzo") == "N/A":
            logger.warning("⚠️ API Amazon non restituisce i dati di prezzo, potrebbe essere una limitazione dell'account.")
    else:
        logger.warning(f"❌ API Amazon non ha restituito dati utili per ASIN: {asin}")
    
    # Tentativo Scraper HTML
    logger.info(f"🌐 Test Scraping HTML per ASIN: {asin}")
    try:
        product_data_html = scrape_product_data(asin)
        if product_data_html:
            logger.info("✅ Dati Scraper HTML ricevuti.")
        else:
            logger.warning(f"❌ Scraper HTML non ha trovato dati per ASIN: {asin}")
    except Exception as e:
        logger.error(f"❌ Errore durante lo scraping HTML: {str(e)}")
        product_data_html = None
    
    # Determinazione del metodo migliore per il salvataggio
    final_data = product_data_api if product_data_api and product_data_api.get("Titolo") != "N/A" else product_data_html
    
    if final_data:
        logger.info("💾 Salvataggio dati nel database.")
        try:
            save_product_data(
                final_data.get("ASIN", "N/A"),
                final_data.get("Titolo", "N/A"),
                float(final_data.get("Prezzo", 0.00)) if final_data.get("Prezzo") not in [None, "N/A"] else 0.00,
                float(final_data.get("VecchioPrezzo", 0.00)) if final_data.get("VecchioPrezzo") not in [None, "N/A"] else 0.00,
                float(final_data.get("Sconto", 0.00)) if final_data.get("Sconto") not in [None, "N/A"] else 0.00,
                final_data.get("Descrizione", "N/A"),
                float(final_data.get("Rating", 0.00)) if final_data.get("Rating") not in [None, "N/A"] else 0.00,
                int(final_data.get("Recensioni", 0)) if final_data.get("Recensioni") not in [None, "N/A"] else 0,
                final_data.get("Stock", "N/A"),
                final_data.get("Immagine", "N/A"),
                final_data.get("URL", "N/A")
            )
        except Exception as e:
            logger.error(f"❌ Errore nel salvataggio dati: {str(e)}")
        return final_data
    
    # Ricerca testuale come fallback
    logger.warning(f"❌ Prodotto non trovato con API e Scraping diretto. Tentativo di ricerca testuale...")
    search_results = scrape_amazon(asin)
    
    if search_results:
        best_match = search_results[0]
        logger.info("✅ Prodotto trovato con ricerca testuale.")
        try:
            save_product_data(
                best_match.get("ASIN", "N/A"),
                best_match.get("Titolo", "N/A"),
                float(best_match.get("Prezzo", 0.00)) if best_match.get("Prezzo") not in [None, "N/A"] else 0.00,
                float(best_match.get("VecchioPrezzo", 0.00)) if best_match.get("VecchioPrezzo") not in [None, "N/A"] else 0.00,
                float(best_match.get("Sconto", 0.00)) if best_match.get("Sconto") not in [None, "N/A"] else 0.00,
                best_match.get("Descrizione", "N/A"),
                float(best_match.get("Rating", 0.00)) if best_match.get("Rating") not in [None, "N/A"] else 0.00,
                int(best_match.get("Recensioni", 0)) if best_match.get("Recensioni") not in [None, "N/A"] else 0,
                best_match.get("Stock", "N/A"),
                best_match.get("Immagine", "N/A"),
                best_match.get("URL", "N/A")
            )
        except Exception as e:
            logger.error(f"❌ Errore nel salvataggio dati: {str(e)}")
        return best_match
    
    logger.error(f"❌ Nessun dato trovato per ASIN: {asin}")
    return None

if __name__ == "__main__":
    test_asin = "B0D18F23QW"
    result = get_complete_product_data(test_asin)
    if result:
        logger.info("✅ Dati finali ottenuti.")
    else:
        logger.error("❌ Nessun prodotto trovato.")
