import logging
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--incognito")
    options.add_argument("--window-size=1920,1080")  # Simula una risoluzione desktop
    options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(80, 115)}.0.{random.randint(4000, 5000)}.0 Safari/537.36')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_blocked(soup):
    """Verifica se Amazon ha bloccato lo scraper."""
    error_messages = [
        "Enter the characters you see below",
        "Sorry! Something went wrong!",
        "Spiacenti, si è verificato un problema!"
    ]
    return any(msg in soup.text for msg in error_messages)

def accept_cookies(driver):
    """Accetta il banner dei cookie, se presente."""
    try:
        time.sleep(2)  # Aspetta il caricamento del popup
        accept_button = driver.find_element(By.ID, "sp-cc-accept")
        accept_button.click()
        logging.info("✅ Banner cookie accettato.")
    except Exception:
        logging.info("⚠️ Nessun banner cookie trovato.")

def scroll_page(driver):
    """Scorre la pagina verso il basso per caricare tutti gli elementi dinamici."""
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(3):  # Scorri più volte per caricare le sezioni
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(1, 3))
        logging.info("✅ Scroll della pagina completato.")
    except Exception as e:
        logging.error(f"⚠️ Errore nello scroll: {e}")

def scrape_product_data(asin):
    logging.info(f"🌐 Scraping HTML per ASIN: {asin}")
    url = f"https://www.amazon.it/dp/{asin}"
    driver = setup_driver()
    driver.get(url)
    
    accept_cookies(driver)  # Accetta i cookie se necessario
    scroll_page(driver)  # Scorri la pagina per caricare tutti gli elementi

    time.sleep(random.uniform(3, 6))  # Attesa random per evitare blocchi
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    
    if check_blocked(soup):
        logging.warning("⚠️ Amazon ha bloccato lo scraper! Riprova con un proxy o VPN.")
        return None
    
    def safe_get_text(tag, default="N/A"):
        return tag.get_text(strip=True) if tag else default
    
    try:
        titolo = safe_get_text(soup.find("span", id="productTitle"))
        prezzo_text = safe_get_text(soup.find("span", class_="a-price-whole"))
        prezzo = float(prezzo_text.replace(".", "").replace(",", ".")) if prezzo_text != "N/A" else 0.00
    except Exception as e:
        logging.error(f"Errore prezzo: {e}")
        prezzo = 0.00
    
    try:
        rating_text = safe_get_text(soup.find("span", class_="a-icon-alt"))
        rating = float(rating_text.split()[0].replace(",", ".")) if rating_text != "N/A" else None
    except Exception as e:
        logging.error(f"Errore rating: {e}")
        rating = None
    
    try:
        recensioni_text = safe_get_text(soup.find("span", id="acrCustomerReviewText"))
        recensioni = int(recensioni_text.split()[0].replace(".", "")) if recensioni_text != "N/A" else 0
    except Exception as e:
        logging.error(f"Errore recensioni: {e}")
        recensioni = 0
    
    try:
        immagine = soup.find("img", id="landingImage")["src"] if soup.find("img", id="landingImage") else "N/A"
    except Exception as e:
        logging.error(f"Errore immagine: {e}")
        immagine = "N/A"
    
    prodotto = {
        "ASIN": asin,
        "Titolo": titolo,
        "Prezzo": prezzo,
        "Rating": rating,
        "Recensioni": recensioni,
        "Immagine": immagine,
        "URL": url
    }
    
    logging.info(f"✅ Dati ottenuti dallo Scraper HTML: {prodotto}")
    return prodotto

if __name__ == "__main__":
    test_asin = "B0D18F23QW"
    result = scrape_product_data(test_asin)
    if result:
        logging.info(f"✅ Dati finali ottenuti: {result}")
    else:
        logging.error("❌ Nessun prodotto trovato.")
