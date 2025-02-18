import streamlit as st 
import pandas as pd
import psycopg2
import os
import hashlib
import logging
import plotly.express as px
import joblib
import numpy as np
from dotenv import load_dotenv

# ✅ Carica variabili d'ambiente
load_dotenv()

# ✅ Configurazione Database PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ✅ Configurazione della pagina
st.set_page_config(page_title="📊 AI-Powered Price Tracker", layout="wide")

# 📢 Sidebar - Navigazione
st.sidebar.title("🔍 Navigazione")
page = st.sidebar.radio("📌 Seleziona una sezione:", ["🏠 Home", "🛒 Offerte Attuali", "📈 Dashboard", "🤖 AI Previsioni"])

# ✅ Funzione per connettersi al database
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logging.error(f"❌ Errore di connessione al database: {e}")
        return None

# ✅ Funzione per recuperare i dati prodotti
def fetch_data():
    conn = connect_db()
    if not conn:
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ph.asin, pp.name, ph.price, ph.old_price, ph.price_diff,
                       ph.rolling_avg_7, ph.rolling_avg_14, ph.rolling_avg_30, 
                       ph.rating, ph.reviews, pp.availability, pp.affiliate_link, ph.scraped_at
                FROM price_history ph
                JOIN product_prices pp ON ph.asin = pp.asin
                ORDER BY ph.scraped_at DESC;
            """)
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            df = pd.DataFrame(data, columns=columns)
            df.fillna(0, inplace=True)
            return df
    except Exception as e:
        logging.error(f"❌ Errore nel recupero dati: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# ✅ Sidebar - Accesso Premium
license_key = st.sidebar.text_input("🔑 Inserisci la chiave di licenza", type="password")

def validate_license(key):
    valid_hash = "710cff4df1cb6c629766e75864480db9cb39f00e20015b41034212b5a4cab1b8"
    return hashlib.sha256(key.encode()).hexdigest() == valid_hash

is_premium = validate_license(license_key)
if is_premium:
    st.sidebar.success("✅ Accesso Premium sbloccato!")
else:
    st.sidebar.warning("🔒 Modalità demo attiva: Alcune funzioni sono limitate.")

# 🏠 **Home Page**
if page == "🏠 Home":
    st.title("🚀 AI-Powered Price Tracker")
    st.write("Monitoraggio e previsione prezzi per Amazon in tempo reale!")
    st.markdown("### 🔥 Perché scegliere AI-Powered Price Tracker?")
    st.write("✅ Analisi prezzi avanzata con AI")
    st.write("✅ Notifiche su offerte e sconti")
    st.write("✅ Previsioni basate su Machine Learning")

# 📈 **AI Previsioni**
if page == "🤖 AI Previsioni":
    st.title("🔮 Previsione Prezzi con AI")
    
    category = st.selectbox("📌 Seleziona una categoria:", ["Laptop", "Smartphone", "Smartwatch", "Tablet", "Televisori"])
    category = category.lower()

    model_path = f"models/xgb_model_{category}.pkl"
    scaler_path = f"models/scaler_{category}.pkl"
    prediction_file = f"data/ml/xgb_predictions_{category}.csv"

    try:
        # ✅ Carica il modello ML e lo scaler
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        pred_df = pd.read_csv(prediction_file)
        df = fetch_data()
        
        if df.empty or pred_df.empty:
            st.warning(f"⚠️ Nessun dato disponibile per {category}. Esegui lo scraper prima di visualizzare le previsioni.")
        else:
            fig = px.line(pred_df, x="days_since", y="predicted_price", markers=True, title=f"📈 Previsione Prezzi per {category}",
                          labels={"days_since": "Giorni nel futuro", "predicted_price": "Prezzo previsto (€)"},
                          line_shape="spline")
            st.plotly_chart(fig, use_container_width=True)
            st.success("✅ Queste previsioni AI sono aggiornate in tempo reale!")
    except FileNotFoundError:
        st.warning(f"⚠️ Nessuna previsione trovata per {category}. Esegui il training AI.")
