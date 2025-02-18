import requests
from bs4 import BeautifulSoup
import logging
import time
import random
import psycopg2
from dotenv import load_dotenv
import os
import json
import csv
from amazon_paapi import AmazonApi

# ✅ Carica variabili d'ambiente
load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")
AWS_REGION = "IT"

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ User-Agents multipli per evitare blocchi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
]

# ✅ Inizializza Amazon API
try:
    amazon_api = AmazonApi(AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_ASSOCIATE_TAG, AWS_REGION)
    logger.info("✅ Amazon API configurata correttamente!")
except Exception as e:
    logger.error(f"❌ Errore nella configurazione Amazon API: {e}")
    amazon_api = None

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
        return conn
    except Exception as e:
        logger.error(f"❌ Errore di connessione al database: {e}")
        return None

def parse_price(price):
    if price and isinstance(price, str):
        clean_price = price.replace("€", "").replace(",", ".").strip()
        return float(clean_price) if clean_price.replace(".", "").isdigit() else None
    return None

def scrape_amazon_product_html(url):
    """🔍 Effettua lo scraping HTML di un prodotto Amazon."""
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        return {
            "name": soup.find("span", {"id": "productTitle"}).text.strip() if soup.find("span", {"id": "productTitle"}) else "N/A",
            "price": parse_price(soup.find("span", {"class": "a-price-whole"}).text) if soup.find("span", {"class": "a-price-whole"}) else None,
            "old_price": parse_price(soup.find("span", {"class": "a-price a-text-price"}).text) if soup.find("span", {"class": "a-price a-text-price"}) else "N/A",
            "rating": soup.find("span", {"class": "a-icon-alt"}).text.strip() if soup.find("span", {"class": "a-icon-alt"}) else "N/A",
            "reviews": soup.find("span", {"id": "acrCustomerReviewText"}).text.strip() if soup.find("span", {"id": "acrCustomerReviewText"}) else "N/A",
            "image_url": soup.find("img", {"id": "landingImage"})["src"] if soup.find("img", {"id": "landingImage"}) else "N/A",
            "affiliate_link": url
        }
    except Exception as e:
        logger.error(f"❌ Errore nello scraping HTML di {url}: {e}")
        return None

def scrape_amazon_product_api(asin):
    """🔍 Recupera il prodotto tramite Amazon API."""
    try:
        response = amazon_api.get_items([asin])
        if response:
            item = response[0]
            
            def parse_price(price):
                if price and isinstance(price, str):
                    clean_price = price.replace("€", "").replace(",", ".").strip()
                    return float(clean_price) if clean_price.replace(".", "").isdigit() else None
                return None

            current_price = parse_price(item.offers.listings[0].price.display_amount) if item.offers and item.offers.listings else None
            old_price = parse_price(item.offers.listings[0].price.amount) if item.offers and item.offers.listings and hasattr(item.offers.listings[0].price, "amount") else None
            
            discount = None
            if current_price is not None and old_price is not None and old_price > 0:
                discount = round((1 - (current_price / old_price)) * 100, 2)
            
            return {
                "asin": asin,
                "name": item.item_info.title.display_value if item.item_info and hasattr(item.item_info, "title") else "N/A",
                "price": current_price,
                "old_price": old_price,
                "discount": discount,
                "rating": "N/A",
                "reviews": "N/A",
                "image_url": item.images.primary.large.url if item.images and item.images.primary else "N/A",
                "affiliate_link": item.detail_page_url if hasattr(item, "detail_page_url") else "N/A"
            }
    except Exception as e:
        logger.error(f"❌ Errore Amazon API per ASIN {asin}: {e}")
        return None

def save_product_to_db(product):
    """💾 Salva un prodotto nel database."""
    conn = connect_db()
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO product_prices (asin, name, price, old_price, discount, rating, reviews, image_url, affiliate_link, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (asin) DO UPDATE SET
                    price = COALESCE(EXCLUDED.price, product_prices.price),
                    old_price = COALESCE(EXCLUDED.old_price, product_prices.old_price),
                    discount = COALESCE(EXCLUDED.discount, product_prices.discount),
                    rating = COALESCE(EXCLUDED.rating, product_prices.rating),
                    reviews = COALESCE(EXCLUDED.reviews, product_prices.reviews),
                    image_url = EXCLUDED.image_url,
                    affiliate_link = EXCLUDED.affiliate_link,
                    scraped_at = CURRENT_TIMESTAMP;
            """, (
                product["asin"],
                product["name"],
                product["price"] if isinstance(product["price"], (int, float)) else None,
                product["old_price"] if isinstance(product["old_price"], (int, float)) else None,
                product["discount"] if isinstance(product["discount"], (int, float)) else None,
                product["rating"] if isinstance(product["rating"], (int, float)) else None,
                product["reviews"] if isinstance(product["reviews"], int) else None,
                product["image_url"],
                product["affiliate_link"]
            ))
        conn.commit()
        logger.info(f"✅ Prodotto salvato: {product['name']}")
    except Exception as e:
        logger.error(f"❌ Errore nel salvataggio del prodotto: {e}")
    finally:
        conn.close()

def scrape_and_save(asin, url):
    """🔄 Scrape prodotto con API, altrimenti fallback su HTML."""
    product = scrape_amazon_product_api(asin)
    if not product:
        product = scrape_amazon_product_html(url)
    if product:
        save_product_to_db(product)
    else:
        logger.warning(f"⚠️ Nessun dato recuperato per {asin}")

if __name__ == "__main__":
    test_products = [
        {"asin": "B0DKTJ22QN", "url": "https://www.amazon.it/dp/B0DKTJ22QN/?tag=mikrotech-21"},
        {"asin": "B0D8WDJXR6", "url": "https://www.amazon.it/dp/B0D8WDJXR6/?tag=mikrotech-21"}
    ]
    for product in test_products:
        scrape_and_save(product["asin"], product["url"])
