import os
import time
import random
import logging
import psycopg2
import requests
import json  # Aggiunto import JSON
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

# Configura il logging con DEBUG ATTIVO
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

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

# **Verifica la struttura della tabella**
def check_database_structure(conn):
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='product_prices'")
    existing_columns = {row[0] for row in cur.fetchall()}
    required_columns = {"asin", "name", "price", "image_url", "category", "created_at"}

    missing_columns = required_columns - existing_columns
    if missing_columns:
        logging.error(f"❌ Mancano le seguenti colonne nel database: {missing_columns}")
        return False
    return True

# **Verifica i prodotti nel database**
def get_existing_products(conn, category):
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM product_prices;")
    categories = cur.fetchall()
    logging.debug(f"📊 Categorie nel database: {categories}")

    cur.execute("SELECT asin, name, price, image_url FROM product_prices WHERE LOWER(category) = LOWER(%s)", (category,))
    products = cur.fetchall()

    if not products:
        logging.warning(f"⚠️ Nessun prodotto trovato per la categoria '{category}' nel database.")
    else:
        logging.info(f"✅ {len(products)} prodotti trovati per la categoria '{category}':")
        for product in products[:5]:  # Mostra solo i primi 5 prodotti
            logging.info(f"🔹 {product[1]} (€{product[2]}) - ASIN: {product[0]}")

    return products

# **Scraping HTML**
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
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logging.error(f"❌ Errore HTTP {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        products = []
        for item in soup.select("div[data-asin]"):
            asin = item.get("data-asin")
            title = item.select_one("span.a-text-normal")
            price = item.select_one("span.a-price-whole")
            image = item.select_one("img.s-image")

            if asin and title and price and image:
                products.append({
                    "asin": asin,
                    "name": title.text.strip(),
                    "price": float(price.text.replace(",", ".")),
                    "image_url": image["src"],
                    "category": category,
                    "created_at": datetime.now()
                })
        logging.info(f"📊 {len(products)} prodotti trovati nello scraping HTML")
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

    logging.debug(f"📡 Payload della richiesta API Amazon: {json.dumps(payload, indent=4)}")

    try:
        logging.info(f"🔍 Recupero dati API Amazon per ASIN: {asin}")
        response = requests.post(url, json=payload, headers=headers, auth=(os.getenv("AWS_ACCESS_KEY"), os.getenv("AWS_SECRET_KEY")))
        logging.debug(f"📡 Risposta API Amazon: {response.status_code} - {response.text}")

        if response.status_code != 200:
            logging.error(f"❌ Errore API Amazon: {response.status_code} - {response.text}")
            return None

        data = response.json()
        if "ItemsResult" in data and "Items" in data["ItemsResult"]:
            item = data["ItemsResult"]["Items"][0]
            return {
                "asin": asin,
                "name": item["ItemInfo"]["Title"]["DisplayValue"],
                "price": item["Offers"]["Listings"][0]["Price"]["Amount"],
                "image_url": item["Images"]["Primary"]["Large"]["URL"],
                "category": "Unknown",
                "created_at": datetime.now()
            }
        else:
            logging.warning(f"⚠️ Nessun dato trovato per ASIN {asin}")
            return None
    except Exception as e:
        logging.error(f"❌ Errore API Amazon: {e}")
        return None

# **Funzione principale**
def main():
    category = input("Inserisci la categoria da cercare (Laptop, Smartphone, Tablet, ecc.): ").strip().lower()
    conn = connect_db()
    if not conn:
        return

    existing_products = get_existing_products(conn, category)
    if not existing_products:
        scraped_products = scrape_html(category)
        if scraped_products:
            logging.info("✅ Scraping completato con successo!")

    conn.close()
    logging.info("✅ Processo terminato!")

if __name__ == "__main__":
    main()
