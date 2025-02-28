from flask import Flask

app = Flask(__name__)

# ✅ Import dei moduli interni aggiornati
from api.database import connect_db, create_tables
from api.scraper_html_api import get_complete_product_data
from api.scraper_api import get_affiliate_link  # AGGIUNTO
from api.reports import generate_report
from api.telegram_bot import start_telegram_bot
from api.notifications import send_bulk_emails

# ✅ Importiamo gli endpoint API dopo aver creato l'istanza di Flask
from api.api import api_blueprint

# ✅ Registriamo il Blueprint
app.register_blueprint(api_blueprint)
