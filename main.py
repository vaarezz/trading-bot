from flask import Flask, request, jsonify
import requests
import os
import logging
from datetime import datetime

app = Flask(__name__)

ALPACA_API_KEY    = os.environ.get("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL   = "https://paper-api.alpaca.markets"
WEBHOOK_SECRET    = os.environ.get("WEBHOOK_SECRET", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def enviar_orden(ticker, action, quantity=1):
    url     = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID":     ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type":        "application/json"
    }
    orden = {
        "symbol":        ticker,
        "qty":           str(quantity),
        "side":          "buy" if action == "buy" else "sell",
        "type":          "market",
        "time_in_force": "day"
    }
    logger.info(f"Enviando orden: {action.upper()} {quantity} {ticker}")
    try:
        r   = requests.post(url, json=orden, headers=headers)
        res = r.json()
        if r.status_code in [200, 201]:
            logger.info(f"Orden ejecutada: {res.get('id','N/A')}")
            return {"success": True, "order": res}
        else:
            logger.error(f"Error Alpaca: {res}")
            return {"success": False, "error": res}
    except Exception as e:
        logger.error(f"Excepcion: {str(e)}")
        return {"success": False, "error": str(e)}

def tiene_posicion(ticker):
    url     = f"{ALPACA_BASE_URL}/v2/positions/{ticker}"
    headers = {
        "APCA-API-KEY-ID":     ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
    }
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            qty = float(r.json().get("qty", 0))
            logger.info(f"Posicion {ticker}: {qty} acciones")
            return qty > 0
        return False
    except:
        return False

@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info(f"Webhook recibido: {datetime.now().strftime('%H:%M:%S')}")

    secret = request.headers.get("X-Webhook-Secret", "")
    if secret != WEBHOOK_SECRET:
        logger.warning("Clave secreta incorrecta")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    ticker   = data.get("ticker",   "AMD")
    action   = data.get("action",   "").lower()
    quantity = int(data.get("quantity", 1))

    logger.info(f"Senal: {action.upper()} {quantity} {ticker}")

    if action == "buy":
        if tiene_posicion(ticker):
            logger.info("BUY ignorado — posicion ya abierta")
            return jsonify({"status": "ignored", "reason": "position already open"}), 200
        resultado = enviar_orden(ticker, "buy", quantity)

    elif action == "sell":
        if not tiene_posicion(ticker):
            logger.info("SELL ignorado — no hay posicion abierta")
            return jsonify({"status": "ignored", "reason": "no open position"}), 200
        resultado = enviar_orden(ticker, "sell", quantity)

    else:
        return jsonify({"error": f"Accion desconocida: {action}"}), 400

    return jsonify(resultado), 200 if resultado["success"] else 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":    "online",
        "broker":    "Alpaca Paper Trading",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@app.route("/posiciones", methods=["GET"])
def ver_posiciones():
    url     = f"{ALPACA_BASE_URL}/v2/positions"
    headers = {
        "APCA-API-KEY-ID":     ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
    }
    try:
        r = requests.get(url, headers=headers)
        return jsonify(r.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Servidor iniciado en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
