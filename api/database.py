import psycopg2
import os
import logging
from psycopg2 import sql
from dotenv import load_dotenv
from utils import get_affiliate_link

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
                    offer_text TEXT,  -- ✅ Aggiunto campo per offerte speciali
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

def get_products(category=None):
    """📥 Estrae tutti i prodotti dal database, inclusi gli sconti e le offerte speciali."""
    conn = connect_db()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            query = """
                SELECT asin, name, price, old_price, discount, description, rating, 
                       reviews, availability, image_url, affiliate_link, category, offer_text
                FROM product_prices
            """
            if category:
                query += " WHERE category = %s;"
                cur.execute(query, (category,))
            else:
                query += ";"
                cur.execute(query)

            prodotti = cur.fetchall()
            return [
                {
                    "asin": row[0],
                    "name": row[1],
                    "price": row[2],
                    "old_price": row[3],
                    "discount": row[4],
                    "description": row[5],
                    "rating": row[6],
                    "reviews": row[7],
                    "availability": row[8],
                    "image_url": row[9],
                    "affiliate_link": row[10],
                    "category": row[11],
                    "offer_text": row[12]  # ✅ Aggiunto il testo dell'offerta
                } for row in prodotti
            ]
    except Exception as e:
        print(f"❌ Errore nel recupero dei prodotti: {e}")
        return []
    finally:
        conn.close()

def save_product_data(asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category, offer_text=None):
    """💾 Salva o aggiorna i dati di un prodotto nel database."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO product_prices (asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category, offer_text, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (asin) DO UPDATE
                SET name = EXCLUDED.name, 
                    price = EXCLUDED.price, 
                    old_price = CASE 
                        WHEN product_prices.old_price IS NULL THEN product_prices.price 
                        ELSE product_prices.old_price 
                    END,
                    discount = EXCLUDED.discount, 
                    description = EXCLUDED.description, 
                    rating = EXCLUDED.rating, 
                    reviews = EXCLUDED.reviews, 
                    availability = EXCLUDED.availability, 
                    image_url = EXCLUDED.image_url, 
                    affiliate_link = EXCLUDED.affiliate_link, 
                    category = EXCLUDED.category, 
                    offer_text = EXCLUDED.offer_text,
                    scraped_at = NOW();
            """, (asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, category, offer_text))
        conn.commit()
        
        # ✅ Se il link affiliato è mancante, lo recuperiamo tramite API
        if not affiliate_link or "N/A" in affiliate_link:
            fetch_and_update_affiliate_link(asin)

        logging.info(f"✅ Dati salvati per ASIN {asin} - Categoria: {category}")
    except Exception as e:
        logging.error(f"❌ Errore nel salvataggio dati di {asin}: {e}")
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
