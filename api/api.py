import os
import time
import random
import logging
import psycopg2
import requests
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

# Configura il logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Carica le variabili d'ambiente
load_dotenv("config/.env")

# **Connessione al Database**
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        logging.info("✅ Connessione al database avvenuta con successo!")
        return conn
    except Exception as e:
        logging.error(f"❌ Errore di connessione al database: {e}")
        return None

# **Verifica struttura Database**
def check_database_structure(conn):
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='product_prices'")
    existing_columns = {row[0] for row in cur.fetchall()}
    required_columns = {"asin", "title", "price", "image", "category", "created_at"}
    
    missing_columns = required_columns - existing_columns
    if missing_columns:
        logging.error(f"❌ Mancano le seguenti colonne nel database: {missing_columns}")
        return False
    return True

# **Scraping HTML con headers avanzati**
def scrape_html(category):
    url = f"https://www.amazon.it/s?k={category}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com",
        "DNT": "1"
    }

    try:
        logging.info(f"🔍 Avvio scraping HTML per categoria: {category}")
        time.sleep(random.uniform(2, 5))  # Ritardo per evitare blocchi
        response = requests.get(url, headers=headers)
        
        if response.status_code == 503:
            logging.error("❌ Amazon ha bloccato lo scraping (503 Service Unavailable)")
            return []

        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        products = []

        for item in soup.select(".s-result-item"):
            asin = item.get("data-asin")
            title = item.select_one("h2 a span")
            price = item.select_one(".a-price-whole")
            image = item.select_one("img.s-image")

            if asin and title and price and image:
                products.append({
                    "asin": asin,
                    "title": title.text.strip(),
                    "price": price.text.strip(),
                    "image": image["src"],
                    "category": category,
                    "created_at": datetime.now()
                })

        if not products:
            logging.warning(f"⚠️ Nessun prodotto trovato con scraping HTML.")
        
        return products
    except requests.RequestException as e:
        logging.error(f"❌ Errore nello scraping HTML: {e}")
        return []

# **Chiamata API Amazon**
def fetch_from_amazon_api(asin):
    url = "https://webservices.amazon.it/paapi5/getItems"
    headers = {"Content-Type": "application/json"}
    payload = {
        "ItemIds": [asin],
        "Resources": ["Images.Primary.Large", "ItemInfo.Title", "Offers.Listings.Price"],
        "PartnerTag": os.getenv("AWS_ASSOCIATE_TAG"),
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.it"
    }

    try:
        logging.info(f"🔍 Recupero dati API Amazon per ASIN: {asin}")
        response = requests.post(url, json=payload, headers=headers, auth=("AWS_ACCESS_KEY", "AWS_SECRET_KEY"))

        # **DEBUG: Stampiamo la risposta API**
        logging.debug(f"🔍 Risposta API Amazon: {response.status_code} - {response.text}")

        if response.status_code != 200:
            logging.error(f"❌ Errore API Amazon: {response.status_code} - {response.text}")
            return None

        data = response.json()
        if "ItemsResult" in data and "Items" in data["ItemsResult"]:
            item = data["ItemsResult"]["Items"][0]
            return {
                "asin": asin,
                "title": item["ItemInfo"]["Title"]["DisplayValue"],
                "price": item["Offers"]["Listings"][0]["Price"]["Amount"],
                "image": item["Images"]["Primary"]["Large"]["URL"],
                "category": "Unknown",
                "created_at": datetime.now()
            }
        else:
            logging.warning(f"⚠️ Nessun dato trovato per ASIN {asin}")
            return None
    except Exception as e:
        logging.error(f"❌ Errore API Amazon: {e}")
        return None

# **Salvataggio dati nel database**
def save_to_db(conn, products):
    if not conn:
        logging.error("❌ Connessione al database non disponibile! Impossibile salvare dati.")
        return
    
    try:
        with conn.cursor() as cur:
            for product in products:
                cur.execute("""
                    INSERT INTO product_prices (asin, title, price, image, category, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (asin) DO UPDATE 
                    SET price = EXCLUDED.price, category = EXCLUDED.category, created_at = NOW();
                """, (product["asin"], product["title"], product["price"], product["image"], product["category"], product["created_at"]))

            conn.commit()
            logging.info(f"✅ Salvati {len(products)} prodotti nel database.")
    except Exception as e:
        logging.error(f"❌ Errore nel salvataggio dati: {e}")

# **Funzione principale**
def main():
    category = input("Inserisci la categoria da cercare (Laptop, Smartphone, Tablet, ecc.): ").strip()
    conn = connect_db()
    if not conn:
        return

    if not check_database_structure(conn):
        return

    cur = conn.cursor()
    cur.execute("SELECT asin FROM product_prices WHERE category = %s", (category,))
    existing_asins = {row[0] for row in cur.fetchall()}

    logging.info(f"✅ Trovati {len(existing_asins)} prodotti nel database per la categoria {category}.")

    if not existing_asins:
        logging.info(f"🔍 Nessun prodotto trovato nel database. Avvio scraping...")
        scraped_products = scrape_html(category)

        if scraped_products:
            save_to_db(conn, scraped_products)
        else:
            logging.warning(f"⚠️ Nessun prodotto trovato con scraping HTML. Provo API Amazon per un solo prodotto.")
            test_asin = "B09FYZC9BV"
            if test_asin not in existing_asins:
                product = fetch_from_amazon_api(test_asin)
                if product:
                    save_to_db(conn, [product])
                else:
                    logging.error(f"❌ Nessun dato trovato per {test_asin}, anche via API.")

    cur.close()
    conn.close()
    logging.info("✅ Scraping completato!")

if __name__ == "__main__":
    main()
