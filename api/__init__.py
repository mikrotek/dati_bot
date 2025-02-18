from flask import Flask

app = Flask(__name__)

# Importiamo gli endpoint API dopo aver creato l'istanza di Flask
from api.api import api_blueprint

# Registriamo il Blueprint
app.register_blueprint(api_blueprint)
