import boto3
import requests
import json
import logging
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

# ✅ Credenziali API Amazon
AWS_ACCESS_KEY = "AKIAJZ2ABBY4F4ZJAAKQ"
AWS_SECRET_KEY = "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"
AWS_ASSOCIATE_TAG = "mikrotech-21"
AWS_REGION = "eu-west-1"  # 🔹 Amazon IT usa "eu-west-1" per PA-API

# ✅ Configura il logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ✅ URL corretto per Amazon IT
API_URL = "https://webservices.amazon.it/paapi5/searchitems"

# ✅ Corpo della richiesta manuale
payload = {
    "PartnerTag": AWS_ASSOCIATE_TAG,
    "PartnerType": "Associates",
    "Marketplace": "www.amazon.it",
    "Keywords": "laptop",
    "SearchIndex": "Electronics",
    "ItemCount": 3
}

# ✅ Headers richiesti da Amazon PA-API
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ✅ Creiamo l'oggetto AWSRequest per firmare la richiesta
aws_credentials = Credentials(AWS_ACCESS_KEY, AWS_SECRET_KEY)
request = AWSRequest(method="POST", url=API_URL, data=json.dumps(payload), headers=headers)
SigV4Auth(aws_credentials, "ProductAdvertisingAPI", AWS_REGION).add_auth(request)

# ✅ Converte la richiesta firmata in formato utilizzabile da `requests`
signed_headers = dict(request.headers)

# ✅ Eseguiamo la richiesta con la firma corretta
try:
    logger.info("📡 Eseguendo richiesta diretta a Amazon PA-API con firma AWS...")
    response = requests.post(API_URL, headers=signed_headers, data=json.dumps(payload))

    logger.debug("📥 Risposta API:")
    logger.debug(response.text)

except Exception as e:
    logger.error(f"❌ ERRORE: {e}")
