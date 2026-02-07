import os
from datetime import datetime

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from whatsapp import send_message, parse_incoming
from data_handler import (
    add_transaction,
    get_budget_status,
    set_budget,
    get_budget,
    DEFAULT_TIPO_CAMBIO,
)

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


# --- Health check endpoint ---

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint for Render."""
    return jsonify({"status": "ok", "service": "FinPer Chatbot"}), 200


# --- Webhook endpoints ---

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta webhook verification (hub.challenge handshake)."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    """Handle incoming WhatsApp messages."""
    data = request.get_json()
    phone, text = parse_incoming(data)

    if phone and text:
        response_text = handle_message(phone, text)
        send_message(phone, response_text)

    return jsonify({"status": "ok"}), 200


# --- Message handling ---

def handle_message(phone, text):
    parts = text.lower().split()
    if not parts:
        return msg_ayuda()

    command = parts[0]

    if command in ("gasto", "egreso"):
        return handle_gasto(phone, parts[1:])
    elif command in ("ingreso", "entrada"):
        return handle_ingreso(phone, parts[1:])
    elif command in ("tope", "presupuesto"):
        return handle_tope(phone, parts[1:])
    elif command in ("estado", "resumen"):
        return handle_estado(phone)
    elif command == "ayuda":
        return msg_ayuda()
    else:
        return (
            "No entendi el comando. Escribe *ayuda* para ver los comandos disponibles."
        )


# --- Command handlers ---

def handle_gasto(phone, args):
    """Parse: gasto <monto> [USD] <categoria> <detalle...>"""
    if len(args) < 2:
        return (
            "Formato: *gasto <monto> <categoria> <detalle>*\n"
            "Ejemplo: gasto 50000 alimentacion almuerzo\n"
            "Para USD: gasto 20 USD tecnologia hosting"
        )

    try:
        cantidad = int(args[0])
    except ValueError:
        return "El monto debe ser un numero. Ejemplo: *gasto 50000 alimentacion almuerzo*"

    # Check if second arg is currency
    divisa = "COP"
    next_idx = 1
    if len(args) > 1 and args[1].upper() in ("USD", "COP"):
        divisa = args[1].upper()
        next_idx = 2

    categoria = args[next_idx] if len(args) > next_idx else "general"
    detalle = " ".join(args[next_idx + 1:]) if len(args) > next_idx + 1 else ""

    add_transaction(
        phone=int(phone),
        tipo="egreso",
        cantidad=cantidad,
        divisa=divisa,
        tipo_cambio=DEFAULT_TIPO_CAMBIO,
        categoria=categoria,
        detalle=detalle,
    )

    # Build response with budget status
    cantidad_cop = cantidad * DEFAULT_TIPO_CAMBIO if divisa == "USD" else cantidad
    response = f"Gasto registrado: ${cantidad:,} {divisa}"
    if divisa == "USD":
        response += f" (${cantidad_cop:,} COP)"
    response += f" en {categoria}"
    if detalle:
        response += f" - {detalle}"

    # Append budget status
    status = get_budget_status(int(phone))
    response += "\n\n" + format_budget_status(status)

    return response


def handle_ingreso(phone, args):
    """Parse: ingreso <monto> [USD] <categoria> <detalle...>"""
    if len(args) < 2:
        return (
            "Formato: *ingreso <monto> <categoria> <detalle>*\n"
            "Ejemplo: ingreso 3000000 salario mensual"
        )

    try:
        cantidad = int(args[0])
    except ValueError:
        return "El monto debe ser un numero. Ejemplo: *ingreso 3000000 salario mensual*"

    divisa = "COP"
    next_idx = 1
    if len(args) > 1 and args[1].upper() in ("USD", "COP"):
        divisa = args[1].upper()
        next_idx = 2

    categoria = args[next_idx] if len(args) > next_idx else "general"
    detalle = " ".join(args[next_idx + 1:]) if len(args) > next_idx + 1 else ""

    add_transaction(
        phone=int(phone),
        tipo="ingreso",
        cantidad=cantidad,
        divisa=divisa,
        tipo_cambio=DEFAULT_TIPO_CAMBIO,
        categoria=categoria,
        detalle=detalle,
    )

    return f"Ingreso registrado: ${cantidad:,} {divisa} en {categoria}"


def handle_tope(phone, args):
    """Parse: tope <monto>"""
    if not args:
        budget = get_budget(int(phone))
        if budget:
            return f"Tu tope mensual actual es: ${budget:,} COP\nPara cambiarlo: *tope <monto>*"
        return "No tienes un tope mensual. Usa: *tope <monto>*\nEjemplo: tope 2000000"

    try:
        amount = int(args[0])
    except ValueError:
        return "El monto debe ser un numero. Ejemplo: *tope 2000000*"

    set_budget(int(phone), amount)
    return f"Tope mensual actualizado: ${amount:,} COP"


def handle_estado(phone):
    """Show current month budget status."""
    status = get_budget_status(int(phone))
    return format_budget_status(status)


# --- Formatting ---

def format_budget_status(status):
    now = datetime.now()
    months_es = [
        "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    month_name = months_es[now.month]

    lines = [f"Estado del presupuesto - {month_name} {now.year}"]

    if not status["has_budget"]:
        lines.append(f"Gastado este mes: ${status['spent_cop']:,} COP")
        lines.append("")
        lines.append("No tienes un tope mensual configurado.")
        lines.append("Usa *tope <monto>* para definirlo.")
    else:
        lines.append(f"Tope mensual: ${status['budget']:,} COP")
        lines.append(f"Gastado: ${status['spent_cop']:,} COP ({status['percentage']}%)")
        if status["remaining"] >= 0:
            lines.append(f"Disponible: ${status['remaining']:,} COP")
        else:
            lines.append(f"EXCEDIDO por: ${abs(status['remaining']):,} COP")

    if status.get("by_category"):
        lines.append("")
        lines.append("Por categoria:")
        for cat, amount in sorted(status["by_category"].items()):
            lines.append(f"  - {cat}: ${amount:,} COP")

    return "\n".join(lines)


def msg_ayuda():
    return (
        "Comandos disponibles:\n\n"
        "*gasto <monto> <categoria> <detalle>*\n"
        "  Registrar un gasto en COP\n"
        "  Ej: gasto 50000 alimentacion almuerzo\n\n"
        "*gasto <monto> USD <categoria> <detalle>*\n"
        "  Registrar un gasto en dolares\n"
        "  Ej: gasto 20 USD tecnologia hosting\n\n"
        "*ingreso <monto> <categoria> <detalle>*\n"
        "  Registrar un ingreso\n"
        "  Ej: ingreso 3000000 salario mensual\n\n"
        "*tope <monto>*\n"
        "  Definir tope mensual en COP\n"
        "  Ej: tope 2000000\n\n"
        "*estado*\n"
        "  Ver resumen del mes (gastado, % y disponible)\n\n"
        "*ayuda*\n"
        "  Ver este mensaje"
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)