import pandas as pd
import xlsxwriter
import os
import psycopg2
import logging
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env
load_dotenv()

# Configurazione database PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Percorso file report
REPORT_PATH = "data/analysis/report.xlsx"
os.makedirs("data/analysis", exist_ok=True)  # Assicura che la cartella esista

def connect_db():
    """Connessione al database PostgreSQL."""
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

def fetch_data():
    """Recupera i dati dal database PostgreSQL."""
    conn = connect_db()
    if not conn:
        return pd.DataFrame()  # Ritorna un DataFrame vuoto se c'è un errore

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT asin, name, price, old_price, discount, rating, reviews, availability, affiliate_link, scraped_at
                FROM product_prices;
            """)
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            return pd.DataFrame(data, columns=columns)
    except Exception as e:
        logging.error(f"❌ Errore nel recupero dati: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def generate_report():
    """Genera un report Excel leggendo i dati dal database."""
    df = fetch_data()

    # Controllo se ci sono dati
    if df.empty:
        logging.warning("⚠️ Nessun dato disponibile per generare il report.")
        return

    # Creazione file Excel
    writer = pd.ExcelWriter(REPORT_PATH, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Dati', index=False)

    workbook = writer.book
    worksheet = writer.sheets['Dati']

    # Formattazione colonne
    currency_format = workbook.add_format({'num_format': '€#,##0.00'})
    bold_format = workbook.add_format({'bold': True})

    worksheet.set_column('C:C', 12, currency_format)  # Colonna prezzo
    worksheet.set_column('D:D', 12, currency_format)  # Colonna prezzo originale
    worksheet.set_column('E:E', 12, currency_format)  # Colonna sconto
    worksheet.set_column('F:F', 10)
    worksheet.set_column('G:G', 10)
    worksheet.set_column('H:H', 20)

    # Aggiunta statistiche chiave
    row_count = len(df) + 1  # +1 per tenere conto dell'intestazione
    worksheet.write(row_count, 0, "Statistiche Chiave", bold_format)
    worksheet.write(row_count + 1, 0, "Prezzo Medio (€)", bold_format)
    worksheet.write(row_count + 1, 1, f"=AVERAGE(C2:C{row_count})", currency_format)
    worksheet.write(row_count + 2, 0, "Numero Prodotti", bold_format)
    worksheet.write(row_count + 2, 1, f"=COUNTA(A2:A{row_count})")

    # Creazione grafico prezzi avanzato
    chart = workbook.add_chart({'type': 'line'})
    chart.add_series({
        'name': 'Prezzo',
        'categories': f'Dati!$B$2:$B${len(df)+1}',
        'values': f'Dati!$C$2:$C${len(df)+1}',
        'line': {'color': 'blue'}
    })
    chart.set_title({'name': 'Andamento Prezzi'})
    chart.set_x_axis({'name': 'Prodotti'})
    chart.set_y_axis({'name': 'Prezzo (€)'})
    worksheet.insert_chart(f'P2', chart)  # Posizione grafico

    # Salva il file Excel
    writer.close()
    logging.info(f"✅ Report Excel generato in {REPORT_PATH}")

if __name__ == "__main__":
    generate_report()
