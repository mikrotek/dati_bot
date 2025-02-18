from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Impostazioni logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# URL di Google Shopping
search_query = "laptop"
url = f"https://www.google.com/search?q={search_query}&hl=it&tbm=shop"

# Avvio driver
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Rimuovi se vuoi vedere il browser in azione
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

def handle_cookies(driver):
    """ Gestisce il popup dei cookie selezionando 'Rifiuta tutto' se disponibile """
    try:
        reject_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Rifiuta tutto")]'))
        )
        reject_button.click()
        logging.info("✅ Cookie rifiutati!")
        time.sleep(2)  # Aspettiamo il caricamento della pagina
        
    except Exception as e:
        logging.warning(f"⚠️ Nessun popup cookie trovato o errore: {str(e)}")

try:
    logging.info(f"🌐 Apertura pagina: {url}")
    driver.get(url)

    # **GESTIONE COOKIE**
    handle_cookies(driver)

    # **ATTENDERE IL CARICAMENTO DEI PRODOTTI**
    time.sleep(3)

    # **SCRAPING PRODOTTI**
    products = driver.find_elements(By.CSS_SELECTOR, ".sh-dgr__content")
    
    if products:
        logging.info(f"🔍 Trovati {len(products)} prodotti!")
        for product in products[:5]:  # Mostriamo solo i primi 5 per esempio
            try:
                name = product.find_element(By.CSS_SELECTOR, ".tAxDx").text
                price = product.find_element(By.CSS_SELECTOR, ".a8Pemb").text
                link = product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                logging.info(f"🛒 {name} - {price} - {link}")
            except:
                continue
    else:
        logging.warning("⚠️ Nessun prodotto trovato!")

except Exception as e:
    logging.error(f"❌ Errore nello scraping: {str(e)}")

finally:
    driver.quit()
    logging.info("🛑 Browser chiuso.")
