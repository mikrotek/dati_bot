import pandas as pd
import numpy as np
import os
import joblib
import tensorflow as tf
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sklearn.preprocessing import StandardScaler
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

# ✅ Selezione categoria
def get_category():
    return input("🔍 Inserisci una categoria (Laptop, Smartphone, etc.): ").strip().lower()

category = get_category()

# ✅ Caricamento dati storici
query = """
    SELECT price_history.asin, price_history.scraped_at, price_history.old_price, price_history.price_diff, 
           price_history.rolling_avg_7, price_history.rolling_avg_14, price_history.rolling_avg_30, 
           price_history.rating, price_history.reviews
    FROM price_history
    JOIN product_prices ON price_history.asin = product_prices.asin
    WHERE LOWER(product_prices.name) LIKE %s
    ORDER BY price_history.scraped_at
"""

df = pd.read_sql(query, engine, params=(f"%{category}%",))

if df.empty:
    raise ValueError("❌ Errore: Nessun dato disponibile per questa categoria!")

df.fillna(method='ffill', inplace=True)
df.fillna(0, inplace=True)

df["scraped_at"] = pd.to_datetime(df["scraped_at"])
df.sort_values("scraped_at", inplace=True)
df["days_since"] = (df["scraped_at"] - df["scraped_at"].min()).dt.days

# ✅ Caricamento modelli aggiornati
xgb_model = joblib.load(f"models/xgb_model_{category}.pkl")
xgb_scaler = joblib.load(f"models/scaler_{category}.pkl")
lstm_model = tf.keras.models.load_model(f"models/lstm_model_{category}.keras")
lstm_scaler_X = joblib.load(f"models/scaler_X_{category}.pkl")
lstm_scaler_y = joblib.load(f"models/scaler_y_{category}.pkl")

# ✅ Assicurarsi che le feature siano nell'ordine corretto
expected_columns = xgb_model.get_booster().feature_names
if expected_columns is None:
    raise ValueError("❌ Errore: Il modello XGBoost non ha feature names. Probabile errore nel training.")

X_train = df[expected_columns]

# ✅ Generazione dati futuri
num_days = 60
future_days = np.arange(1, num_days + 1).reshape(-1, 1)
mean_values = X_train.mean().values.reshape(1, -1)
future_features_df = pd.DataFrame(np.tile(mean_values, (num_days, 1)), columns=expected_columns)
future_features_df["days_since"] = future_days.flatten()

# ✅ Previsioni XGBoost
future_scaled_xgb = xgb_scaler.transform(future_features_df)
xgb_predictions = xgb_model.predict(future_scaled_xgb)

# ✅ Previsioni LSTM
future_scaled_lstm = lstm_scaler_X.transform(future_features_df).reshape(num_days, 1, len(expected_columns))
lstm_predictions = lstm_model.predict(future_scaled_lstm)
lstm_predictions = lstm_scaler_y.inverse_transform(lstm_predictions).flatten()

# ✅ Bilanciamento pesi tra XGBoost e LSTM
r2_xgb = r2_score(df["old_price"], xgb_model.predict(xgb_scaler.transform(X_train)))
r2_lstm = r2_score(df["old_price"].iloc[-num_days:], lstm_predictions[:num_days]) if len(df) >= num_days else 0

if r2_lstm < 0:
    weight_xgb, weight_lstm = 0.9, 0.1
else:
    weight_xgb = max(0, min(1, r2_xgb / (r2_xgb + r2_lstm)))
    weight_lstm = 1 - weight_xgb

hybrid_predictions = (weight_xgb * xgb_predictions) + (weight_lstm * lstm_predictions)

# ✅ Creazione grafico
plt.figure(figsize=(10, 5))
plt.plot(future_days, xgb_predictions, 'b--', label="XGBoost Predictions")
plt.plot(future_days, lstm_predictions, 'r--', label="LSTM Predictions")
plt.plot(future_days, hybrid_predictions, 'g-', label="Hybrid Model")
plt.xlabel("Giorni nel futuro")
plt.ylabel("Prezzo Previsto (€)")
plt.title(f"Previsione Prezzi Combinata ({category})")
plt.legend()
plt.grid(True)
plt.show()
