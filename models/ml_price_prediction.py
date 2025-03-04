import pandas as pd
import numpy as np
import os
import logging
import optuna
import joblib
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import xgboost as xgb

# ✅ Carica variabili d'ambiente
load_dotenv()

# ✅ Configurazione Database
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ✅ Connessione al database con SQLAlchemy
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

# ✅ Selezione categoria
def get_category():
    return input("🔍 Inserisci una categoria (Laptop, Smartphone, etc.): ").strip().lower()

category = get_category()

# ✅ Query per estrarre i dati dal database
query = """
    SELECT price_history.asin, price_history.price, price_history.old_price, price_history.price_diff, 
           price_history.rolling_avg_7, price_history.rolling_avg_14, price_history.rolling_avg_30, 
           price_history.rating, price_history.reviews, price_history.scraped_at
    FROM price_history
    JOIN product_prices ON price_history.asin = product_prices.asin
    WHERE LOWER(product_prices.name) LIKE %s
    ORDER BY price_history.scraped_at;
"""

try:
    df = pd.read_sql(query, engine, params=(f"%{category}%",))
    if df.empty:
        raise ValueError(f"⚠️ Nessun dato trovato per la categoria '{category}'.")
except Exception as e:
    logging.error(f"❌ Errore nel caricamento dei dati dal database: {e}")
    exit()

# ✅ Pulizia dati
df.fillna(method='ffill', inplace=True)  # Riempimento forward dei dati mancanti
df.fillna(0, inplace=True)  # Sostituzione eventuali NaN con 0

# ✅ Conversione timestamp
if "scraped_at" in df.columns:
    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df["days_since"] = (df["scraped_at"].max() - df["scraped_at"]).dt.days

# ✅ Feature Engineering
df["rolling_avg_60"] = df["price"].rolling(window=60, min_periods=1).mean()
df["rolling_avg_90"] = df["price"].rolling(window=90, min_periods=1).mean()

selected_features = ["days_since", "old_price", "price_diff", "rolling_avg_7", "rolling_avg_14", "rolling_avg_30", "rolling_avg_60", "rolling_avg_90", "rating", "reviews"]
X = df[selected_features]
y = df["price"]

# ✅ Debug: Verifica dei dati
print("📌 Esempio dati usati per training:")
print(X.head())

# ✅ Divisione train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ✅ Scalatura dei dati
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ✅ **Funzione per tuning con Optuna**
def objective(trial):
    param = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "gamma": trial.suggest_float("gamma", 0.01, 1.0, log=True),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10)
    }
    
    model = xgb.XGBRegressor(**param, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    mae = np.mean(np.abs(y_test - y_pred))
    return mae

# ✅ **Ottimizzazione iperparametri**
study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=30)

# ✅ Migliori parametri trovati
best_params = study.best_params
print(f"✅ Migliori parametri trovati: {best_params}")

# ✅ Addestramento finale con i migliori parametri
best_model = xgb.XGBRegressor(**best_params, random_state=42)
best_model.fit(X_train_scaled, y_train)

# ✅ Valutazione finale
y_pred = best_model.predict(X_test_scaled)
r2 = 1 - (np.sum((y_test - y_pred) ** 2) / np.sum((y_test - np.mean(y_test)) ** 2))
mae = np.mean(np.abs(y_test - y_pred))
rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))

print(f"📊 XGBoost Ottimizzato - R²: {r2:.4f}, MAE: {mae:.2f}€, RMSE: {rmse:.2f}€")

# ✅ Salvataggio modello e scaler
model_filename = f"models/xgb_model_{category}.pkl"
scaler_filename = f"models/scaler_{category}.pkl"

joblib.dump(best_model, model_filename)
joblib.dump(scaler, scaler_filename)

print(f"✅ Modello ottimizzato salvato in {model_filename}")
