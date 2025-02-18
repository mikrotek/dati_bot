from flask import Flask, request, jsonify

app = Flask(__name__)

# Simulazione di un database di licenze
LICENSES = {
    "securepremiumkey123": {"valid": True, "email": "utente@example.com"},
    "trialkey456": {"valid": False, "email": "demo@example.com"}
}

@app.route('/api/validate_license', methods=['GET'])
def validate_license():
    """Endpoint per validare una chiave di licenza."""
    key = request.args.get("key")
    if key in LICENSES and LICENSES[key]["valid"]:
        return jsonify({"valid": True})
    return jsonify({"valid": False})

@app.route('/api/generate_license', methods=['POST'])
def generate_license():
    """Endpoint per generare una nuova chiave di licenza."""
    data = request.json
    new_key = data.get("key")
    email = data.get("email")

    if new_key and email:
        LICENSES[new_key] = {"valid": True, "email": email}
        return jsonify({"success": True, "message": f"Chiave generata con successo per {email}."})
    return jsonify({"success": False, "message": "Errore nella generazione della chiave."})

@app.route('/api/revoke_license', methods=['POST'])
def revoke_license():
    """Endpoint per revocare una chiave di licenza."""
    data = request.json
    key = data.get("key")

    if key in LICENSES:
        LICENSES[key]["valid"] = False
        return jsonify({"success": True, "message": "Chiave revocata con successo."})
    return jsonify({"success": False, "message": "Chiave non trovata."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
