from flask import Flask

# ✅ Crea l'istanza di Flask
app = Flask(__name__)

# ✅ Import dei moduli interni aggiornati
from api.database import connect_db, create_tables
from api.scraper_html_api import scrape_amazon_products
from api.scraper_api import get_special_offers, get_affiliate_link
from api.utils import get_affiliate_link  # ✅ Importato utils correttamente
from api.reports import generate_report
from api.telegram_bot import start_telegram_bot
from api.notifications import send_bulk_emails

# ✅ Importiamo gli endpoint API dopo aver creato l'istanza di Flask
from api.api import api_blueprint

# ✅ Registriamo il Blueprint API
app.register_blueprint(api_blueprint)

# ✅ Funzione di avvio per configurare il database
def initialize_app():
    """🔧 Inizializza l'applicazione creando le tabelle nel database."""
    with app.app_context():
        create_tables()
        print("✅ Database inizializzato correttamente.")

# ✅ Avvio automatico della configurazione del database
initialize_app()
