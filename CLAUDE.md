# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **personal financial chatbot** ("Finanzas_Bot") designed to track and manage personal financial transactions. The chatbot processes income and expense data, integrating with messaging platforms (phone numbers are tracked in the data).

**Data Storage**: Financial transactions are stored in **Excel files** (`Finanzas_Bot.xlsx`) rather than database tables. This Excel-based approach is suitable for personal use and allows easy manual inspection and backup.

### Financial Data Structure

The core data model tracks financial transactions with the following schema (stored in Excel):
- **ID**: Unique transaction identifier (e.g., "97a4efjt")
- **Fecha**: Transaction date
- **Tipo**: Transaction type (`ingreso` for income, `egreso` for expenses)
- **Cantidad**: Amount (integer)
- **Divisa**: Currency code
- **Tipo de Cambio**: Exchange rate (integer)
- **Categoría**: Transaction category
- **Detalle**: Transaction details/description
- **Notas**: Additional notes
- **Productos**: Product quantity (float, optional)
- **Ubicacion**: Location/store name (optional)
- **Telefono**: User phone number (for chatbot interaction)
- **Creado**: Creation timestamp

The Excel file is the single source of truth for all financial data.

## Development Setup

This is a personal Python-based project that uses Excel as data storage.

### Prerequisites
- Python 3.x
- pandas (for Excel file manipulation)
- openpyxl or xlrd (Excel file readers)
- Any chatbot framework being used (e.g., python-telegram-bot, discord.py, etc.)

### Typical Project Structure
```
Chatbot/
├── Finanzas_Bot.xlsx       # Main financial data storage (Excel)
├── chatbot.py              # Main chatbot logic (when created)
├── data_handler.py         # Excel read/write operations (when created)
├── requirements.txt        # Python dependencies (when created)
├── tests/                  # Unit tests (when created)
└── config/                 # Configuration files (when created)
```

**Note**: Notebooks directory is not currently used in this project.

### Common Commands

**Development:**
```bash
# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt

# Run the chatbot
python chatbot.py

# Run Python scripts for data processing
python <script_name>.py
```

**Testing:**
```bash
# Run unit tests (when implemented)
pytest tests/

# Run specific test file
pytest tests/test_data_handler.py
```

**Excel Data Operations:**
```python
# Read financial data
import pandas as pd
df = pd.read_excel('Finanzas_Bot.xlsx')

# Write updated data
df.to_excel('Finanzas_Bot.xlsx', index=False)
```

## Architecture Notes

### Data Processing Pattern
- Use **pandas DataFrames** for data transformations and aggregations
- Financial calculations should handle multiple currencies via `Tipo de Cambio` (exchange rate)
- Group transactions by `Telefono` for per-user analysis
- Timestamp filtering uses `Fecha` for transaction dates and `Creado` for audit trails
- **All data persistence happens via Excel file read/write operations**

### Chatbot Integration
- Phone number (`Telefono`) is the user identifier
- Transactions are categorized by `Tipo` (ingreso/egreso) and `Categoría`
- Location data (`Ubicacion`) provides context for expenses
- Support for multi-currency transactions with exchange rate tracking

### Excel-Based Workflow
1. Chatbot receives transaction message from user
2. Parse and validate transaction data (amount, type, category, etc.)
3. Read existing Excel file (`Finanzas_Bot.xlsx`) using pandas
4. Append new transaction(s) as DataFrame rows
5. Write updated DataFrame back to Excel file
6. Perform queries/aggregations on DataFrame for user reports
7. Return formatted results to chatbot user

### Data Persistence Strategy
- **Single Excel file** (`Finanzas_Bot.xlsx`) stores all transactions
- Always read entire file before modifications to avoid data loss
- Use `pd.concat()` to append new rows to existing DataFrame
- Write with `index=False` to maintain clean Excel format
- Consider periodic backups of Excel file (e.g., dated copies)

## Data Handling Guidelines

- Always validate transaction amounts are positive integers
- Handle missing `Ubicacion` and `Productos` fields gracefully (nullable/NaN)
- Preserve all transaction IDs for audit trail
- When aggregating by currency, apply `Tipo de Cambio` conversions
- Filter by `Telefono` for user-specific queries
- Use `Creado` timestamp for data freshness and ordering

### Excel File Operations Best Practices

- **Always read before write**: Load entire Excel file before any modifications
- **Atomic updates**: Read → Modify DataFrame → Write in single operation
- **Backup strategy**: Consider creating timestamped backup copies before major updates
- **File locking**: Be aware that Excel file cannot be open in Excel during Python operations
- **Data types**: Ensure dates are properly formatted as datetime objects
- **Missing data**: Use `pd.NA` or `np.nan` for missing numeric values
- **Validation**: Validate new transactions before appending to prevent corrupt data

## Excel-Specific Considerations

### Reading Data
```python
# Read with proper date parsing
df = pd.read_excel('Finanzas_Bot.xlsx', parse_dates=['Fecha', 'Creado'])

# Handle missing values
df['Productos'] = df['Productos'].fillna(0)
df['Ubicacion'] = df['Ubicacion'].fillna('')
```

### Writing Data
```python
# Write back maintaining format
df.to_excel('Finanzas_Bot.xlsx', index=False, engine='openpyxl')

# For dated backups
from datetime import datetime
backup_name = f"Finanzas_Bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
df.to_excel(backup_name, index=False)
```

### Common Queries
```python
# Get all transactions for a user
user_transactions = df[df['Telefono'] == 573194601394]

# Calculate balance (ingresos - egresos)
ingresos = df[df['Tipo'] == 'ingreso']['Cantidad'].sum()
egresos = df[df['Tipo'] == 'egreso']['Cantidad'].sum()
balance = ingresos - egresos

# Group by category
category_summary = df.groupby(['Tipo', 'Categoría'])['Cantidad'].sum()

# Filter by date range
from datetime import datetime
df_filtered = df[(df['Fecha'] >= '2026-02-01') & (df['Fecha'] <= '2026-02-28')]
```

## ID Generation

Transaction IDs use lowercase alphanumeric format (e.g., "97a4efjt", "a4ae12f9"):
```python
import random
import string

def generate_transaction_id(length=8):
    """Generate unique transaction ID"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
```
