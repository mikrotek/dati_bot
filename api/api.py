from flask import Flask, jsonify, request, Blueprint
from api.database import get_all_products, get_product_by_asin, save_product_data
import logging


# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Creazione Blueprint API
api_blueprint = Blueprint("api", __name__)

@api_blueprint.route("/", methods=["GET"])
def home():
    """🌐 Endpoint Home - Messaggio di benvenuto"""
    return jsonify({"message": "Benvenuto nell'API di DatiBot! Usa /api/prodotti per accedere ai dati."})

@api_blueprint.route("/api/prodotti", methods=["GET"])
def get_products():
    """🔍 Endpoint per ottenere tutti i prodotti."""
    try:
        prodotti = get_all_products()
        return jsonify(prodotti), 200
    except Exception as e:
        logger.error(f"❌ Errore nel recupero prodotti: {e}")
        return jsonify({"errore": "Impossibile recuperare i prodotti."}), 500

@api_blueprint.route("/api/prodotti/<asin>", methods=["GET"])
def get_product(asin):
    """🔍 Endpoint per ottenere un prodotto specifico tramite ASIN."""
    try:
        prodotto = get_product_by_asin(asin)
        if prodotto:
            return jsonify(prodotto), 200
        else:
            return jsonify({"errore": "Prodotto non trovato."}), 404
    except Exception as e:
        logger.error(f"❌ Errore nel recupero prodotto: {e}")
        return jsonify({"errore": "Impossibile recuperare il prodotto."}), 500

@api_blueprint.route("/api/prodotti", methods=["POST"])
def add_product():
    """📝 Endpoint per aggiungere un nuovo prodotto."""
    data = request.get_json()
    if not data:
        return jsonify({"errore": "Dati mancanti."}), 400
    
    try:
        save_product_data([data])
        return jsonify({"messaggio": "Prodotto aggiunto con successo!"}), 201
    except Exception as e:
        logger.error(f"❌ Errore nel salvataggio prodotto: {e}")
        return jsonify({"errore": "Impossibile salvare il prodotto."}), 500

# Inizializzazione Flask
app = Flask(__name__)
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
