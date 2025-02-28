import psycopg2
import os
import logging
from psycopg2 import sql
from dotenv import load_dotenv
from scraper_api import get_affiliate_link


# ✅ Carica variabili d'ambiente
load_dotenv()

# 📌 Configurazione database PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def connect_db():
    """🔗 Connessione al database PostgreSQL."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_client_encoding('UTF8')
        logging.info("✅ Connessione al database avvenuta con successo!")
        return conn
    except Exception as e:
        logging.error(f"❌ Errore di connessione al database: {e}")
        return None      

def create_tables():
    """🛠️ Crea/Aggiorna tutte le tabelle del database."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS product_prices (
                    id SERIAL PRIMARY KEY,
                    asin TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    price FLOAT CHECK (price > 0),
                    old_price FLOAT,
                    discount FLOAT,
                    description TEXT,
                    rating FLOAT,
                    reviews INT,
                    availability TEXT NOT NULL,
                    image_url TEXT,
                    affiliate_link TEXT,
                    category TEXT NOT NULL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_product_prices_asin ON product_prices(asin);
            """)
        conn.commit()
        logging.info("✅ Tabelle create/verificate con successo.")
    except Exception as e:
        logging.error(f"❌ Errore nella creazione delle tabelle: {e}")
    finally:
        conn.close()

def check_product_exists(asin):
    """🔍 Controlla se un prodotto con un determinato ASIN esiste nel database."""
    conn = connect_db()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM product_prices WHERE asin = %s", (asin,))
            exists = cur.fetchone() is not None
            return exists
    except Exception as e:
        logging.error(f"❌ Errore nel controllo dell'ASIN {asin}: {e}")
        return False
    finally:
        conn.close()

def get_product_by_asin(asin):
    """🔍 Recupera un prodotto dal database dato il suo ASIN."""
    conn = connect_db()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM product_prices WHERE asin = %s", (asin,))
            product = cur.fetchone()
            return product
    except Exception as e:
        logging.error(f"❌ Errore nel recupero del prodotto {asin}: {e}")
        return None
    finally:
        conn.close()

def save_product_data(asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category):
    """💾 Salva o aggiorna i dati di un prodotto nel database."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO product_prices (asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (asin) DO UPDATE
                SET name = EXCLUDED.name, 
                    price = EXCLUDED.price, 
                    old_price = product_prices.price, 
                    discount = EXCLUDED.discount, 
                    description = EXCLUDED.description, 
                    rating = EXCLUDED.rating, 
                    reviews = EXCLUDED.reviews, 
                    availability = EXCLUDED.availability, 
                    image_url = EXCLUDED.image_url, 
                    affiliate_link = EXCLUDED.affiliate_link, 
                    category = EXCLUDED.category, 
                    scraped_at = NOW();
            """, (asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category))
        conn.commit()
        
        # ✅ Se il link affiliato è mancante, lo recuperiamo tramite API
        if not affiliate_link or "N/A" in affiliate_link:
            fetch_and_update_affiliate_link(asin)

        logging.info(f"✅ Dati salvati per ASIN {asin} - Categoria: {category}")
    except Exception as e:
        logging.error(f"❌ Errore nel salvataggio dati di {asin}: {e}")
    finally:
        conn.close()

def update_product_in_db(asin, new_data):
    """🔄 Aggiorna i dati di un prodotto esistente nel database."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE product_prices
                SET name = %s, price = %s, old_price = %s, discount = %s, 
                    description = %s, rating = %s, reviews = %s, availability = %s, 
                    image_url = %s, affiliate_link = %s, category = %s, scraped_at = NOW()
                WHERE asin = %s;
            """, (
                new_data["name"], new_data["price"], new_data["old_price"], new_data["discount"],
                new_data["description"], new_data["rating"], new_data["reviews"], new_data["availability"],
                new_data["image_url"], new_data["affiliate_link"], new_data["category"], asin
            ))
        conn.commit()
        logging.info(f"✅ Prodotto {asin} aggiornato con successo.")
    except Exception as e:
        logging.error(f"❌ Errore nell'aggiornamento del prodotto {asin}: {e}")
    finally:
        conn.close()

def fetch_and_update_affiliate_link(asin):
    """🔗 Recupera il link affiliato tramite API Amazon e aggiorna il database"""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT affiliate_link FROM product_prices WHERE asin = %s", (asin,))
            result = cur.fetchone()

            # Se il link è mancante o non valido, lo aggiorniamo
            if result and (not result[0] or "N/A" in result[0]):
                affiliate_link = get_affiliate_link(asin)
                if affiliate_link and "amazon" in affiliate_link:
                    cur.execute("""
                        UPDATE product_prices 
                        SET affiliate_link = %s 
                        WHERE asin = %s;
                    """, (affiliate_link, asin))
                    conn.commit()
                    logging.info(f"✅ Link affiliato aggiornato per ASIN {asin}: {affiliate_link}")
    except Exception as e:
        logging.error(f"❌ Errore aggiornamento link affiliato per ASIN {asin}: {e}")
    finally:
        conn.close()        

# ✅ Test Database
if __name__ == "__main__":
    logger.info("🔍 Test connessione database e creazione tabelle...")
    create_tables()
    logger.info("✅ Test completato!")
