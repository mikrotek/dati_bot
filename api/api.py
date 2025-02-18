from flask import Blueprint, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ✅ Abilita CORS per permettere richieste da siti esterni

# ✅ Creiamo un Blueprint per l'API
api_blueprint = Blueprint('api', __name__)

# ✅ Carica variabili d'ambiente
load_dotenv()

# 📌 Configurazione database PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# 🔗 Funzione per connettersi al database
def connect_db():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# ✅ Endpoint API per ottenere i prodotti
@api_blueprint.route('/api/prodotti', methods=['GET'])
def get_products():
    try:
        conn = connect_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT asin, name, price, old_price, discount, rating, reviews, affiliate_link
            FROM product_prices
            ORDER BY scraped_at DESC
            LIMIT 50;
        """)
        products = cur.fetchall()

        result = []
        for product in products:
            result.append({
                "asin": product[0],
                "name": product[1],
                "price": product[2],
                "old_price": product[3],
                "discount": product[4],
                "rating": product[5],
                "reviews": product[6],
                "affiliate_link": product[7]
            })

        cur.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
