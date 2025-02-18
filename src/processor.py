import pandas as pd
import logging

class DataProcessor:
    def clean_data(self, input_file, output_file):
        try:
            df = pd.read_csv(input_file)

            # Rimuoviamo prodotti senza nome o prezzo
            df = df.dropna(subset=["name", "price"])
            
            # Filtriamo prezzi errati (es. prodotti con prezzo 0)
            df = df[df["price"] > 1]

            df.to_csv(output_file, index=False)
            logging.info(f"Dati puliti e salvati in {output_file}")
        except Exception as e:
            logging.error(f"Errore durante la pulizia dei dati: {e}")
