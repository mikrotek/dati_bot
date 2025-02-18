import logging
import json
import csv
import psycopg2
from amazon_paapi import AmazonApi
from dotenv import load_dotenv
import os

# ✅ Carica variabili d'ambiente
load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ✅ Configurazione credenziali AWS
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")
AWS_REGION = "IT"

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Connessione al database
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("✅ Connessione al database avvenuta con successo!")
        return conn
    except Exception as e:
        logger.error(f"❌ Errore nella connessione al database: {e}")
        return None

# ✅ Recupera ASIN dal database
def get_asin_from_db():
    conn = connect_db()
    if not conn:
        return []

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT asin FROM product_prices WHERE updated_at < NOW() - INTERVAL '1 day' LIMIT 10;")
            asin_list = [row[0] for row in cursor.fetchall()]
            return asin_list
    except Exception as e:
        logger.error(f"❌ Errore nel recupero degli ASIN: {e}")
        return []
    finally:
        conn.close()

# ✅ Formatta i dati ricevuti da PA-API
def format_data(item):
    try:
        return {
            "ASIN": item.asin if hasattr(item, "asin") else "N/A",
            "Titolo": item.item_info.title.display_value if hasattr(item.item_info, "title") else "N/A",
            "Prezzo": item.offers.listings[0].price.display_amount if item.offers and item.offers.listings else "N/A",
            "URL": item.detail_page_url if hasattr(item, "detail_page_url") else "N/A",
            "Immagine": item.images.primary.large.url if item.images and item.images.primary else "N/A",
        }
    except Exception as e:
        logger.error(f"❌ Errore nel formattare i dati: {e}")
        return {}

# ✅ Salva i dati aggiornati nel database
def save_to_db(data):
    conn = connect_db()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO product_prices (asin, name, price, url, image, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (asin) DO UPDATE 
                SET price = EXCLUDED.price, name = EXCLUDED.name, url = EXCLUDED.url, image = EXCLUDED.image, updated_at = NOW();
            """, (data["ASIN"], data["Titolo"], data["Prezzo"], data["URL"], data["Immagine"]))

        conn.commit()
        logger.info(f"✅ Dati aggiornati per ASIN: {data['ASIN']}")
    except Exception as e:
        logger.error(f"❌ Errore nel salvataggio dati: {e}")
    finally:
        conn.close()

# ✅ Avvio richiesta API con ASIN dal database
try:
    logger.info("🔄 Inizializzazione connessione a PA-API 5...")
    api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, AWS_REGION)
    logger.info("✅ Connessione a PA-API 5 riuscita!")

    ASIN_LIST = get_asin_from_db()
    if not ASIN_LIST:
        logger.warning("⚠️ Nessun ASIN da aggiornare.")
    else:
        logger.info(f"📡 Inviando richiesta API per ASIN: {ASIN_LIST}")
        response = api.get_items(ASIN_LIST)

        if response:
            logger.info("✅ Risposta ricevuta con successo!")

            # ✅ Salva ogni prodotto aggiornato
            for item in response:
                formatted_data = format_data(item)
                save_to_db(formatted_data)

            # ✅ Salvataggio in JSON per backup
            with open("amazon_data.json", "w", encoding="utf-8") as json_file:
                json.dump(response, json_file, ensure_ascii=False, indent=4)

            logger.info("✅ Dati salvati in 'amazon_data.json'")

        else:
            logger.error("❌ Nessun dato ricevuto dalla API!")

except Exception as e:
    logger.error(f"❌ Errore critico: {e}")
