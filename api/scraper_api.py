import logging
import json
import os
from amazon_paapi import AmazonApi
from dotenv import load_dotenv

# ✅ Caricamento variabili d'ambiente
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")
AWS_REGION = "IT"  # ✅ Amazon Italia

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Funzione per formattare i dati ricevuti dall'API Amazon
def format_data(item):
    try:
        return {
            "ASIN": getattr(item, "asin", "N/A"),
            "Titolo": getattr(item.item_info.title, "display_value", "N/A") if hasattr(item, "item_info") and hasattr(item.item_info, "title") else "N/A",
            "Prezzo": getattr(item.offers.listings[0].price, "display_amount", "N/A") if hasattr(item, "offers") and item.offers and hasattr(item.offers.listings[0], "price") else "N/A",
            "Stock": getattr(item.offers.listings[0].availability, "message", "N/A") if hasattr(item, "offers") and item.offers and hasattr(item.offers.listings[0], "availability") else "N/A",
            "Recensioni": getattr(item.customer_reviews, "count", "N/A") if hasattr(item, "customer_reviews") else "N/A",
            "Rating": getattr(item.customer_reviews, "star_rating", "N/A") if hasattr(item, "customer_reviews") else "N/A",
            "URL": getattr(item, "detail_page_url", "N/A"),
            "Immagine": getattr(item.images.primary.large, "url", "N/A") if hasattr(item, "images") and hasattr(item.images.primary, "large") else "N/A",
        }
    except Exception as e:
        logger.error(f"❌ Errore nel formattare i dati: {e}")
        return {}

# ✅ Funzione per ottenere dati e link affiliati da PA-API 5.0
def get_product_data_from_api(asin_list):
    try:
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY or not AWS_ASSOCIATE_TAG:
            logger.error("❌ Credenziali API mancanti! Verifica il file .env")
            return None

        logger.info(f"🔄 Inizializzazione connessione a PA-API 5 per {asin_list}...")
        api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, AWS_REGION)
        logger.info("✅ Connessione a PA-API 5 riuscita!")

        logger.info(f"📡 Inviando richiesta API per ASIN: {asin_list}")
        response = api.get_items(items=asin_list)

        if response:
            logger.info("✅ Risposta ricevuta con successo!")
            
            response_data = [item.to_dict() for item in response]
            logger.info(f"🔍 Risposta API: {json.dumps(response_data, indent=4, ensure_ascii=False)}")

            formatted_results = []
            for item in response:
                formatted_data = format_data(item)
                if formatted_data["ASIN"] != "N/A":
                    formatted_results.append(formatted_data)
                    logger.info(f"📊 Dati formattati per ASIN {formatted_data['ASIN']}: {json.dumps(formatted_data, indent=4, ensure_ascii=False)}")
                else:
                    logger.warning(f"⚠️ Nessun dato valido ricevuto per ASIN: {getattr(item, 'asin', 'Sconosciuto')}")

            return formatted_results

        else:
            logger.warning("⚠️ Nessun dato ricevuto dalla API.")
            return None

    except Exception as e:
        logger.error(f"❌ Errore critico: {e}")
        return None

# ✅ Funzione per recuperare il link affiliato per un singolo ASIN
def get_affiliate_link(asin):
    try:
        logger.info(f"🔗 Recupero link affiliato per ASIN: {asin}")
        data = get_product_data_from_api([asin])

        if data and len(data) > 0:
            affiliate_link = data[0].get("URL", "N/A")
            logger.info(f"✅ Link affiliato ottenuto: {affiliate_link}")
            return affiliate_link
        else:
            logger.warning(f"⚠️ Nessun link affiliato trovato per ASIN {asin}")
            return "N/A"

    except Exception as e:
        logger.error(f"❌ Errore nel recupero link affiliato: {e}")
        return "N/A"

# ✅ Avvio script
if __name__ == "__main__":
    asin_test = ["B0D18F23QW"]  # Esempio di ASIN
    data = get_product_data_from_api(asin_test)

    if data:
        with open("amazon_data.json", "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        logger.info("✅ Dati salvati in 'amazon_data.json'")
