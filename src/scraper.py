import os
import time
import logging
import requests
from dotenv import load_dotenv

# Carica le credenziali da .env
load_dotenv()
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_ASSOCIATE_TAG = os.getenv("AWS_ASSOCIATE_TAG")

# URL API Amazon
AMAZON_API_ENDPOINT = "https://webservices.amazon.com/paapi5/getitems"

# Configurazione logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Funzione per ottenere informazioni su un prodotto
def get_amazon_product(asin):
    headers = {
        "Content-Type": "application/json",
        "x-amz-access-token": AWS_ACCESS_KEY,  # 🔥 Verifica che sia corretto!
    }

    payload = {
        "ItemIds": [asin],
        "Marketplace": "www.amazon.it",
        "PartnerTag": AWS_ASSOCIATE_TAG,
        "PartnerType": "Associates",
        "Resources": [
            "Images.Primary.Large",
            "ItemInfo.Title",
            "ItemInfo.Features",
            "Offers.Listings.Price",
            "Offers.Listings.Availability.Message",
            "Offers.Listings.IsPrimeEligible",
            "CustomerReviews.StarRating"
        ]
    }

    try:
        response = requests.post(AMAZON_API_ENDPOINT, json=payload, headers=headers)

        if response.status_code == 200:
            product = response.json()["ItemsResult"]["Items"][0]
            data = {
                "asin": asin,
                "name": product["ItemInfo"]["Title"]["DisplayValue"] if "Title" in product["ItemInfo"] else "N/A",
                "price": product["Offers"]["Listings"][0]["Price"]["Amount"] if "Offers" in product else None,
                "currency": product["Offers"]["Listings"][0]["Price"]["Currency"] if "Offers" in product else None,
                "availability": product["Offers"]["Listings"][0]["Availability"]["Message"] if "Offers" in product else "N/A",
                "rating": product["CustomerReviews"]["StarRating"] if "CustomerReviews" in product else None,
                "image": product["Images"]["Primary"]["Large"]["URL"] if "Images" in product else None,
                "affiliate_link": product["DetailPageURL"]
            }
            return data

        elif response.status_code == 429:
            logging.warning("⚠️ Troppe richieste. Attesa di 60 secondi...")
            time.sleep(60)
            return get_amazon_product(asin)  # 🔄 Riprova dopo l'attesa
        else:
            logging.error(f"❌ Errore API Amazon: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logging.error(f"❌ Errore: {e}")
        return None

# **TEST**
if __name__ == "__main__":
    asin_test = "B08N5WRWNW"  # iPhone 12 (64GB) - Nero
    product_data = get_amazon_product(asin_test)
    
    if product_data:
        logging.info("✅ Prodotto trovato!")
        print(product_data)
    else:
        logging.warning("⚠️ Nessun prodotto recuperato.")
