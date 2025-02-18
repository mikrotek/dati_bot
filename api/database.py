import psycopg2
import os
import logging
from psycopg2 import sql
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

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
    """🛠️ Crea/Aggiorna le tabelle ottimizzate."""
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
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_product_prices_asin ON product_prices(asin);

                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    asin TEXT NOT NULL,
                    price FLOAT CHECK (price > 0),
                    old_price FLOAT,
                    rating FLOAT,
                    reviews INT,
                    price_diff FLOAT GENERATED ALWAYS AS (old_price - price) STORED,
                    rolling_avg_7 FLOAT,
                    rolling_avg_14 FLOAT,
                    rolling_avg_30 FLOAT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (asin) REFERENCES product_prices(asin) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_price_history_asin ON price_history(asin);
            """)
        conn.commit()
        logging.info("✅ Tabelle ottimizzate create/verificate con successo.")
    except Exception as e:
        logging.error(f"❌ Errore nella creazione delle tabelle: {e}")
    finally:
        conn.close()

def save_product_data(products):
    """💾 Salva i dati dei prodotti nel database PostgreSQL."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            insert_query = sql.SQL("""
                INSERT INTO product_prices (asin, name, price, old_price, discount, description, rating, reviews, availability, image_url, affiliate_link, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (asin) DO UPDATE 
                SET price = EXCLUDED.price, 
                    old_price = COALESCE(EXCLUDED.old_price, product_prices.old_price),
                    discount = COALESCE(EXCLUDED.discount, product_prices.discount),
                    rating = COALESCE(EXCLUDED.rating, product_prices.rating),
                    reviews = COALESCE(EXCLUDED.reviews, product_prices.reviews),
                    availability = EXCLUDED.availability,
                    image_url = EXCLUDED.image_url, 
                    scraped_at = CURRENT_TIMESTAMP;
            """)

            for product in products:
                cur.execute(insert_query, (
                    product["asin"], product["name"], 
                    float(product["price"]) if product["price"] else None,
                    float(product["old_price"]) if product["old_price"] else None,
                    float(product["discount"]) if product["discount"] else None,
                    product["description"], 
                    float(product["rating"]) if product["rating"] else None,
                    int(product["reviews"]) if product["reviews"] else None,
                    product["availability"], 
                    product["image_url"], 
                    product["affiliate_link"]
                ))
        conn.commit()
        logging.info("✅ Dati prodotti salvati nel database.")
    except Exception as e:
        logging.error(f"❌ Errore nel salvataggio dei dati: {e}")
    finally:
        conn.close()

def get_all_products():
    """📊 Recupera tutti i prodotti dal database."""
    conn = connect_db()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM product_prices ORDER BY scraped_at DESC;")
            products = cur.fetchall()
        return products
    except Exception as e:
        logging.error(f"❌ Errore nel recupero dei prodotti: {e}")
        return []
    finally:
        conn.close()

def get_product_by_asin(asin):
    """🔍 Recupera un prodotto specifico tramite ASIN."""
    conn = connect_db()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM product_prices WHERE asin = %s;", (asin,))
            product = cur.fetchone()
        return product
    except Exception as e:
        logging.error(f"❌ Errore nel recupero del prodotto {asin}: {e}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
