import json
import random
import string
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
EXCEL_PATH = BASE_DIR / "Finanzas_Bot.xlsx"
BUDGETS_PATH = BASE_DIR / "budgets.json"

DEFAULT_TIPO_CAMBIO = 3900


def generate_transaction_id(length=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


# --- Excel operations ---

def read_transactions():
    if not EXCEL_PATH.exists():
        return pd.DataFrame(columns=[
            "ID", "Fecha", "Tipo", "Cantidad", "Divisa", "Tipo de Cambio",
            "Categoría", "Detalle", "Notas", "Productos", "Ubicacion",
            "Telefono", "Creado",
        ])
    return pd.read_excel(EXCEL_PATH, parse_dates=["Fecha", "Creado"])


def save_transactions(df):
    df.to_excel(EXCEL_PATH, index=False, engine="openpyxl")


def add_transaction(phone, tipo, cantidad, divisa="COP", tipo_cambio=DEFAULT_TIPO_CAMBIO,
                    categoria="", detalle="", notas=None, productos=None, ubicacion=None):
    df = read_transactions()
    now = datetime.now()
    new_row = {
        "ID": generate_transaction_id(),
        "Fecha": now.strftime("%Y-%m-%d"),
        "Tipo": tipo,
        "Cantidad": cantidad,
        "Divisa": divisa,
        "Tipo de Cambio": tipo_cambio,
        "Categoría": categoria,
        "Detalle": detalle,
        "Notas": notas,
        "Productos": productos,
        "Ubicacion": ubicacion,
        "Telefono": phone,
        "Creado": now,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_transactions(df)
    return new_row


# --- Budget operations ---

def _load_budgets():
    if not BUDGETS_PATH.exists():
        return {}
    with open(BUDGETS_PATH, "r") as f:
        return json.load(f)


def _save_budgets(budgets):
    with open(BUDGETS_PATH, "w") as f:
        json.dump(budgets, f, indent=2)


def get_budget(phone):
    budgets = _load_budgets()
    return budgets.get(str(phone))


def set_budget(phone, amount):
    budgets = _load_budgets()
    budgets[str(phone)] = amount
    _save_budgets(budgets)


# --- Budget status ---

def get_monthly_expenses_cop(phone, year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    df = read_transactions()
    if df.empty:
        return 0, {}

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    mask = (
        (df["Telefono"] == phone)
        & (df["Tipo"] == "egreso")
        & (df["Fecha"].dt.year == year)
        & (df["Fecha"].dt.month == month)
    )
    expenses = df[mask].copy()

    if expenses.empty:
        return 0, {}

    # Convert all to COP
    expenses["Cantidad_COP"] = expenses.apply(
        lambda row: row["Cantidad"] * row["Tipo de Cambio"] if row["Divisa"] == "USD" else row["Cantidad"],
        axis=1,
    )

    total = int(expenses["Cantidad_COP"].sum())
    by_category = (
        expenses.groupby("Categoría")["Cantidad_COP"]
        .sum()
        .astype(int)
        .to_dict()
    )
    return total, by_category


def get_budget_status(phone):
    budget = get_budget(phone)
    spent, by_category = get_monthly_expenses_cop(phone)

    if budget is None:
        return {
            "has_budget": False,
            "spent_cop": spent,
            "by_category": by_category,
        }

    percentage = (spent / budget * 100) if budget > 0 else 0
    remaining = budget - spent

    return {
        "has_budget": True,
        "budget": budget,
        "spent_cop": spent,
        "percentage": round(percentage, 1),
        "remaining": remaining,
        "by_category": by_category,
    }
