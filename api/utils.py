import logging
import time
import re
import os
from dotenv import load_dotenv
from amazon_paapi import AmazonApi

# Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Carica credenziali API dal file .env
load_dotenv()
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")
REGION = "IT"

# Inizializza Amazon API
if AWS_ACCESS_KEY and AWS_SECRET_KEY and AWS_ASSOCIATE_TAG:
    amazon_api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, REGION)
else:
    amazon_api = None
    logger.error("❌ Credenziali Amazon API non trovate. Verifica il file .env")


def clean_price(price_text):
    """Pulisce il testo del prezzo e lo converte in float."""
    if price_text and isinstance(price_text, str):
        price_text = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
        try:
            return float(price_text)
        except ValueError:
            return None
    return None


def get_affiliate_link(asin, max_retries=5, initial_wait=5):
    """Recupera il link affiliato di un prodotto dato un ASIN con gestione delle richieste."""
    if not amazon_api:
        logger.warning("⚠️ Amazon API non inizializzata. Impossibile ottenere il link affiliato.")
        return None

    retries = 0
    wait_time = initial_wait
    while retries < max_retries:
        try:
            response = amazon_api.get_items(items=[asin])

            if response and hasattr(response, "items") and isinstance(response.items, list) and len(response.items) > 0:
                product = response.items[0]  # 🔹 Prendi il primo elemento della lista
                return product.detail_page_url if hasattr(product, "detail_page_url") else None
            else:
                logger.warning(f"⚠️ Nessun link affiliato trovato per ASIN {asin}")
                return None
        except Exception as e:
            if "TooManyRequests" in str(e):
                logger.error(f"❌ Errore: Limite di richieste raggiunto per Amazon API. Riprovo in {wait_time} secondi...")
                time.sleep(wait_time)
                wait_time *= 2  # Exponential backoff
                retries += 1
            else:
                logger.error(f"❌ Errore nel recupero del link affiliato: {e}")
                return None

    logger.error(f"❌ Impossibile ottenere il link affiliato per ASIN {asin} dopo {max_retries} tentativi.")
    return None
