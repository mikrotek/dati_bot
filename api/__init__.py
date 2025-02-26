from flask import Flask

app = Flask(__name__)

# ✅ Import dei moduli interni per rendere 'api' un vero pacchetto
from api.database import connect_db, create_tables
from api.scraper import run_scraper
from api.reports import generate_report
from api.telegram_bot import start_telegram_bot
from api.notifications import send_bulk_emails

# ✅ Importiamo gli endpoint API dopo aver creato l'istanza di Flask
from api.api import api_blueprint

# ✅ Registriamo il Blueprint
app.register_blueprint(api_blueprint)
