import pandas as pd
import numpy as np
import os
import joblib
import tensorflow as tf
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime

# ✅ Carica le variabili d'ambiente
load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ✅ Connessione al database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# ✅ Input categoria
category = input("🔍 Inserisci una categoria (Laptop, Smartphone, etc.): ").strip().lower()

# ✅ Caricamento dati storici
query = """
    SELECT price_history.asin, price_history.scraped_at, price_history.old_price, price_history.price_diff, 
           price_history.rolling_avg_7, price_history.rolling_avg_14, price_history.rolling_avg_30, 
           price_history.rating, price_history.reviews
    FROM price_history
    JOIN product_prices ON price_history.asin = product_prices.asin
    WHERE LOWER(product_prices.name) LIKE %s
"""
df = pd.read_sql(query, engine, params=(f"%{category}%",))
df.fillna(0, inplace=True)
df["scraped_at"] = pd.to_datetime(df["scraped_at"])
df.sort_values("scraped_at", inplace=True)
df["days_since"] = (df["scraped_at"] - df["scraped_at"].min()).dt.days

# ✅ Debug: Stampa le prime righe
print("\n📊 **Dati dal Database (Prime 5 righe):**")
print(df.head())

# ✅ Caricamento modello XGBoost
xgb_model = joblib.load(f"models/xgb_model_{category}.pkl")
xgb_scaler = joblib.load(f"models/scaler_{category}.pkl")

# **Fix Feature Order**
expected_columns = xgb_model.get_booster().feature_names
if expected_columns is None:
    raise ValueError("❌ Errore: Il modello XGBoost non ha feature names. Probabile errore nel training.")

# ✅ Creazione dataset e RIORDINO feature
feature_columns = list(expected_columns) + ["days_since"]
X_train = df[feature_columns]

# ✅ Trasformazione dati per XGBoost (Ora con colonne ordinate!)
X_train_scaled = xgb_scaler.transform(X_train)
xgb_predictions = xgb_model.predict(X_train_scaled)

# ✅ Stampa debug feature
print("\n📊 **Feature usate per il training:**")
print(feature_columns)

# ✅ Salvataggio CSV per debug
debug_file = f"data/ml/debug_xgb_features_{category}.csv"
df.to_csv(debug_file, index=False)
print(f"✅ Debug salvato in {debug_file}")
