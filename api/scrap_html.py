import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# Carica credenziali API dal file .env
load_dotenv()
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")

# Funzione per generare user-agent casuale
def get_random_user_agent():
    ua = UserAgent()
    return ua.random

# Configurazione Selenium
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument(f"user-agent={get_random_user_agent()}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--incognito")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# Funzione per verificare se Amazon sta bloccando lo scraper
def check_blocked(soup):
    blocked_messages = ["Robot Check", "Inserisci i caratteri che vedi", "Verifica che non sei un robot"]
    if any(msg in soup.text for msg in blocked_messages):
        print("⚠️ Bloccato da Amazon! Cambia User-Agent o usa Proxy.")
        return True
    return False

# Funzione per estrarre i prodotti da Amazon HTML
def scrape_amazon(search_term):
    url = f"https://www.amazon.it/s?k={search_term}"
    driver = setup_driver()
    driver.get(url)
    
    time.sleep(random.uniform(3, 6))  # Ritardo casuale per evitare blocchi
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-main-slot div[data-component-type='s-search-result']"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        if check_blocked(soup):
            driver.quit()
            return []

        with open("debug_page.html", "w", encoding="utf-8") as file:
            file.write(page_source)
        print("✅ HTML salvato per debug.")

        products = soup.select("div.s-main-slot div[data-component-type='s-search-result']")
        print(f"Numero di prodotti trovati: {len(products)}")
        
        scraped_data = []
        
        for product in products[:20]:  # Prendiamo i primi 20 risultati
            try:
                asin = product.get("data-asin", "N/A")
                title_element = product.select_one("h2 a span, span.a-size-medium.a-color-base, span.a-text-normal, div.s-title-instructions-style")
                title = title_element.text.strip() if title_element else "Senza titolo"
                
                # Rimozione doppio "SponsorizzatoSponsorizzato"
                title = title.replace("SponsorizzatoSponsorizzato", "Sponsorizzato").strip()
                
                price_element = product.select_one("span.a-price span.a-offscreen")
                price = price_element.text.strip() if price_element else "Prezzo non disponibile"
                
                link_element = product.select_one("h2 a")
                link = f"https://www.amazon.it{link_element['href']}" if link_element else "N/A"
                
                if AWS_ASSOCIATE_TAG and "amazon.it" in link:
                    link += f"&tag={AWS_ASSOCIATE_TAG}"
                
                rating_element = product.select_one("span.a-icon-alt")
                rating = rating_element.text.strip() if rating_element else "N/A"
                
                reviews_element = product.select_one("span.a-size-base")
                reviews = reviews_element.text.strip() if reviews_element else "N/A"
                
                image_element = product.select_one("img.s-image")
                image_url = image_element["src"] if image_element else "N/A"
                
                description_element = product.select_one("div.a-row.a-size-small")
                description = description_element.text.strip() if description_element else "N/A"
                
                scraped_data.append({
                    "ASIN": asin,
                    "Titolo": title,
                    "Prezzo": price,
                    "Link": link,
                    "Rating": rating,
                    "Recensioni": reviews,
                    "Immagine": image_url,
                    "Descrizione": description
                })
                print(f"✅ Estratto: {title} | Prezzo: {price} | Rating: {rating} | Recensioni: {reviews} | Immagine: {image_url}")
                
            except Exception as e:
                print(f"❌ Errore nell'estrazione prodotto: {e}")
    
    except Exception as e:
        print(f"❌ Errore durante lo scraping: {e}")
    
    finally:
        driver.quit()

    save_results_csv(scraped_data)
    return scraped_data

# Funzione per salvare i dati estratti in CSV
def save_results_csv(data):
    with open("risultati_scraping.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["ASIN", "Titolo", "Prezzo", "Link", "Rating", "Recensioni", "Immagine", "Descrizione"])
        writer.writeheader()
        writer.writerows(data)
    print("📂 Dati salvati in risultati_scraping.csv")

# Avvio dello scraping
if __name__ == "__main__":
    search_term = "laptop"
    scrape_amazon(search_term)
