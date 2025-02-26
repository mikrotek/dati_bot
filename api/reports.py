import pandas as pd
import os
import logging
from datetime import datetime

# Import dinamico per evitare errori
try:
    from api.database import get_all_products
except ImportError:
    from database import get_all_products

# Configurazione del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_report(output_dir="data/reports"):
    """
    📊 Genera un report in formato CSV con tutti i prodotti nel database.
    """
    try:
        # Recupera i dati dal database
        products = get_all_products()

        if not products:
            logger.warning("⚠️ Nessun prodotto trovato nel database. Report non generato.")
            return None

        # Creazione della directory per i report se non esiste
        os.makedirs(output_dir, exist_ok=True)

        # Nome del file report
        report_filename = f"{output_dir}/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Creazione del DataFrame e salvataggio
        df = pd.DataFrame(products, columns=["ASIN", "Nome", "Prezzo", "Vecchio Prezzo", "Sconto", "Rating", "Recensioni", "URL", "Immagine"])
        df.to_csv(report_filename, index=False, encoding="utf-8")

        logger.info(f"✅ Report generato con successo: {report_filename}")
        return report_filename

    except Exception as e:
        logger.error(f"❌ Errore nella generazione del report: {e}")
        return None
