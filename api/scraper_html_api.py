import logging
import time
import random
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from scraper_api import get_affiliate_link
from database import check_product_exists, save_product_data

# ✅ Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Carica credenziali API dal file .env
load_dotenv()
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")


# ✅ Impostazioni WebDriver per Selenium
def setup_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{random.randint(80, 115)}.0.{random.randint(4000, 5000)}.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ✅ Controlla se Amazon ha bloccato lo scraper
def check_blocked(soup):
    error_messages = [
        "Enter the characters you see below",
        "Sorry! Something went wrong!",
        "Spiacenti, si è verificato un problema!"
    ]
    return any(msg in soup.text for msg in error_messages)


# ✅ Accetta i cookie se presenti
def accept_cookies(driver):
    try:
        time.sleep(2)
        accept_button = driver.find_element(By.ID, "sp-cc-accept")
        accept_button.click()
        logger.info("✅ Banner cookie accettato.")
    except Exception:
        logger.info("⚠️ Nessun banner cookie trovato.")


# ✅ Scroll della pagina per caricare più prodotti
def scroll_page(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(3):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(1, 3))
        logger.info("✅ Scroll della pagina completato.")
    except Exception as e:
        logger.error(f"⚠️ Errore nello scroll: {e}")


# ✅ Funzione per estrarre il testo in sicurezza
def safe_get_text(tag, default="N/A"):
    return tag.get_text(strip=True) if tag else default


# ✅ Pulisce il prezzo e lo converte in float
def clean_price(price_text):
    if price_text and isinstance(price_text, str):
        price_text = re.sub(r"[^\d,]", "", price_text).replace(",", ".")
        try:
            return float(price_text)
        except ValueError:
            return None
    return None


# ✅ Converte le recensioni in float
def clean_rating(rating_text):
    if rating_text and isinstance(rating_text, str):
        rating_match = re.search(r"(\d+,\d+|\d+)", rating_text)
        if rating_match:
            return float(rating_match.group().replace(",", "."))
    return None


# ✅ Funzione principale per il web scraping HTML
def get_product_data_from_html(query, search_type="asin"):
    url = f"https://www.amazon.it/dp/{query}" if search_type == "asin" else f"https://www.amazon.it/s?k={query.replace(' ', '+')}"

    driver = setup_driver()
    driver.get(url)
    accept_cookies(driver)
    scroll_page(driver)
    time.sleep(random.uniform(3, 6))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    if check_blocked(soup):
        logger.warning("⚠️ Amazon ha bloccato lo scraper! Riprova con un proxy o VPN.")
        return []

    products = [soup] if search_type == "asin" else soup.select("div.s-main-slot div[data-component-type='s-search-result']")
    logger.info(f"✅ Numero di prodotti trovati: {len(products)}")

    scraped_data = []

    for product in products[:20]:
        try:
            asin = product.get("data-asin", query if search_type == "asin" else "N/A")

            # ✅ Correggo il selettore del titolo
            title = safe_get_text(product.select_one("h2 a span"))
            if title == "N/A":
                title = safe_get_text(product.select_one("span.a-size-medium.a-color-base"))
            if title == "N/A":
                title = safe_get_text(product.select_one("span.a-text-normal"))
            if title == "N/A":
                title = safe_get_text(product.select_one("div.s-title-instructions-style"))

            price_raw = safe_get_text(product.select_one("span.a-price span.a-offscreen"))
            price = clean_price(price_raw)
            rating_raw = safe_get_text(product.select_one("span.a-icon-alt"))
            rating = clean_rating(rating_raw)
            reviews_raw = safe_get_text(product.select_one("span.a-size-base"))
            reviews = int(re.sub(r"\D", "", reviews_raw)) if reviews_raw.isdigit() else None
            image_url = product.select_one("img.s-image")["src"] if product.select_one("img.s-image") else "N/A"
            description = safe_get_text(product.select_one("div.a-row.a-size-small"))

            # ✅ Recupera il link affiliato dall'API se l'ASIN esiste
            if check_product_exists(asin):
                logger.info(f"🔄 Recupero link affiliato per ASIN {asin}...")
                affiliate_link = get_affiliate_link(asin)
            else:
                affiliate_link = f"https://www.amazon.it/dp/{asin}?tag={AWS_ASSOCIATE_TAG}" if asin != "N/A" else "N/A"

            product_data = {
                "asin": asin,
                "name": title,
                "price": price,
                "old_price": None,
                "discount": None,
                "description": description,
                "rating": rating,
                "reviews": reviews,
                "availability": None,
                "image_url": image_url,
                "affiliate_link": affiliate_link,
                "category": query  # ✅ Assegniamo la categoria
            }

            scraped_data.append(product_data)

            # ✅ Salviamo nel database
            save_product_data(
                asin=asin,
                name=title,
                price=price,
                old_price=None,
                discount=None,
                description=description,
                rating=rating,
                reviews=reviews,
                availability=None,
                image_url=image_url,
                affiliate_link=affiliate_link,
                category=query  # ✅ Passiamo la categoria
            )
            logger.info(f"✅ Prodotto salvato nel database: {title}")

        except Exception as e:
            logger.error(f"❌ Errore nell'estrazione prodotto: {e}")

    return scraped_data


# ✅ Funzione per ottenere dati (API + HTML Scraping)
def get_complete_product_data(asin_or_keyword, search_type="asin"):
    try:
        if search_type == "asin":
            if check_product_exists(asin_or_keyword):
                logger.info(f"✅ Prodotto {asin_or_keyword} già nel database. Verifica aggiornamenti...")
                return get_affiliate_link(asin_or_keyword)

            return get_product_data_from_html(asin_or_keyword)

        elif search_type == "search":
            logger.info(f"🔎 Avvio ricerca per categoria: {asin_or_keyword}")
            return get_product_data_from_html(asin_or_keyword, search_type="search")

        else:
            logger.error("❌ Tipo di ricerca non valido. Usa 'asin' o 'search'.")
            return None
    except Exception as e:
        logger.error(f"❌ Errore imprevisto: {str(e)}")
        return None


if __name__ == "__main__":
    category = input("🔎 Inserisci la categoria da cercare su Amazon: ")
    get_complete_product_data(category, search_type="search")
