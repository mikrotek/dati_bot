import logging
import json
import os
import time
from amazon_paapi import AmazonApi
from dotenv import load_dotenv
from database import save_product_data  # ✅ Usa la funzione aggiornata per salvare i prodotti
from utils import get_affiliate_link  # ✅ Mantiene il recupero del link affiliato

# ✅ Caricamento variabili d'ambiente
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")
AWS_REGION = "IT"  # ✅ Amazon Italia

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Funzione per formattare i dati ricevuti
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
            "offer_text": getattr(item.offers.listings[0], "violator", {}).get("text", None) if hasattr(item, "offers") and item.offers and hasattr(item.offers.listings[0], "violator") else None
        }
    except Exception as e:
        logger.error(f"❌ Errore nel formattare i dati: {e}")
        return {}

# ✅ Funzione per ottenere dati di un prodotto dall'API Amazon
def get_product_data_from_api(asin_list):
    try:
        if not AWS_ACCESS_KEY or not AWS_SECRET_KEY or not AWS_ASSOCIATE_TAG:
            logger.error("❌ Credenziali API mancanti! Verifica il file .env")
            return None

        logger.info(f"🔄 Inizializzazione connessione a PA-API 5 per {asin_list}...")
        api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, AWS_REGION)
        response = api.get_items(items=asin_list)

        if response:
            logger.info("✅ Risposta ricevuta con successo!")

            formatted_results = []
            for item in response.items:
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

# ✅ Funzione per ottenere offerte speciali e salvarle nel database
def get_special_offers():
    try:
        logger.info("🛠 Inviando richiesta API per offerte speciali...")
        api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, AWS_REGION)
        response = api.search_items(keywords="offerte Amazon", item_count=10)

        if hasattr(response, "items"):
            logger.info("✅ Offerte trovate con successo!")
            for item in response.items:
                formatted_data = format_data(item)
                asin = formatted_data["ASIN"]

                # ✅ Recupero il link affiliato per l'ASIN
                affiliate_link = get_affiliate_link(asin) if asin != "N/A" else "N/A"

                save_product_data(
                    asin=formatted_data["ASIN"],
                    name=formatted_data["Titolo"],
                    price=formatted_data["Prezzo"],
                    old_price=None,
                    discount=None,
                    description="Offerta speciale Amazon",
                    rating=formatted_data["Rating"],
                    reviews=formatted_data["Recensioni"],
                    availability=formatted_data["Stock"],
                    image_url=formatted_data["Immagine"],
                    affiliate_link=affiliate_link,
                    category="Offerte",
                    offer_text=formatted_data["offer_text"]
                )
                logger.info(f"✅ Offerta salvata per ASIN: {formatted_data['ASIN']}")
        else:
            logger.warning("⚠️ Nessuna offerta trovata.")
    except Exception as e:
        logger.error(f"❌ Errore critico: {e}")
        return None

# ✅ Avvio script di test
if __name__ == "__main__":
    test_asin = ["B0D18F23QW"]
    data = get_product_data_from_api(test_asin)

    if data:
        with open("amazon_data.json", "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        logger.info("✅ Dati salvati in 'amazon_data.json'")

    get_special_offers()
