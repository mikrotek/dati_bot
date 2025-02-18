import os
import sys
import logging


def get_base_dir():
    """Determina il percorso base del programma, compatibile con l'eseguibile .exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")


def setup_logger():
    """Configura il logger per il programma."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(BASE_DIR, "dati_bot.log")),
            logging.StreamHandler()
        ]
    )


setup_logger()
