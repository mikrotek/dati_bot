from flask import Flask, jsonify, request
from flask_cors import CORS  
from database import connect_db  # Importiamo la connessione al database

app = Flask(__name__)
CORS(app)  # ✅ Abilita CORS per evitare problemi tra frontend e backend

def get_products(category=None):
    """📥 Estrae tutti i prodotti dal database, filtrando per categoria se specificata"""
    conn = connect_db()
    if not conn:
        return []

    try:
        with conn.cursor() as cur:
            if category:
                cur.execute("""
                    SELECT asin, name, price, old_price, discount, description, rating, 
                           reviews, availability, image_url, affiliate_link, category
                    FROM product_prices
                    WHERE category = %s;
                """, (category,))
            else:
                cur.execute("""
                    SELECT asin, name, price, old_price, discount, description, rating, 
                           reviews, availability, image_url, affiliate_link, category
                    FROM product_prices;
                """)
            prodotti = cur.fetchall()
            return [
                {
                    "asin": row[0],
                    "name": row[1],
                    "price": row[2],
                    "old_price": row[3],
                    "discount": row[4],
                    "description": row[5],
                    "rating": row[6],
                    "reviews": row[7],
                    "availability": row[8],
                    "image_url": row[9],
                    "affiliate_link": row[10],
                    "category": row[11]
                } for row in prodotti
            ]
    except Exception as e:
        print(f"❌ Errore nel recupero dei prodotti: {e}")
        return []
    finally:
        conn.close()

@app.route('/api/prodotti', methods=['GET'])
def get_prodotti():
    """📡 Restituisce tutti i prodotti o filtra per categoria e offerte"""
    category = request.args.get('category')
    discount_filter = request.args.get('discount', type=int)

    prodotti = get_products(category)

    # Se è richiesto un filtro sugli sconti
    if discount_filter:
        prodotti = [p for p in prodotti if p['discount'] and p['discount'] >= discount_filter]

    return jsonify(prodotti)

@app.route('/api/categorie', methods=['GET'])
def get_categorie():
    """📡 Restituisce la lista delle categorie disponibili"""
    conn = connect_db()
    if not conn:
        return jsonify([])

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT category FROM product_prices;")
            categories = [row[0] for row in cur.fetchall() if row[0]]
            return jsonify(categories)
    except Exception as e:
        print(f"❌ Errore nel recupero delle categorie: {e}")
        return jsonify([])
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)