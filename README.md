# QR Code-Based Warehouse Inventory & Stock Movement Monitoring System

Single-app Django build: everything (models, views, forms, admin, urls) lives in one
`backend` app, wired up by the `qr_root` project config — matching the requested structure.

## Structure
```
QR-Code-Warehouse-System/
├── qr_root/            # project config (settings, urls, asgi, wsgi)
├── backend/            # the ONE app: models.py, views.py, forms.py, admin.py, urls.py
│   ├── migrations/
│   ├── templates/      # base.html + accounts/ core/ operations/ dashboard/ subfolders
│   ├── static/css/style.css
│   ├── management/commands/seed_demo.py
│   ├── templatetags/core_extras.py
│   ├── services.py     # atomic stock-movement functions (the core business logic)
│   ├── permissions.py  # role-based decorators
│   ├── mixins.py       # role-based CBV mixins
│   └── qr_utils.py     # QR image + scan URL helpers
├── media/
├── manage.py
└── db.sqlite3
```

`backend/urls.py` defines four pattern lists (`accounts_patterns`, `core_patterns`,
`operations_patterns`, `dashboard_patterns`); `qr_root/urls.py` includes each under its
own namespace, so templates still use `{% url 'core:product_list' %}`,
`{% url 'operations:receiving_list' %}`, etc., even though it's all one app.

## Setup
```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo        # demo users + sample warehouse/products
python manage.py runserver
```
Visit **http://127.0.0.1:8000/**.

## Demo Accounts
| Username    | Password      | Role                  |
|-------------|---------------|-----------------------|
| admin       |               | Administrator (superuser, /admin/ too) |
| manager1    |               | Warehouse Manager     |
| staff1      |               | Warehouse Staff       |
| requester1  |               | Requesting Department |
| auditor1    |               | Auditor / Viewer (read-only) |

**Change these before any real use.**

## What's included
Auth & 5 roles, warehouses/locations, categories/units/suppliers, products (quantity or
individual-asset), batches, assets, QR generation + camera scanning (`/inventory/scanner/`),
an atomic stock ledger (`backend/services.py` — every movement is `select_for_update()` +
`@transaction.atomic`, blocks negative stock, writes an immutable `StockTransaction`),
full receiving → transfer → request/release → return → inventory count → damage/disposal
workflows, a dashboard with charts and alerts, notifications, an audit log, and
CSV-exportable reports. Django Admin is wired for every model as a power-user fallback.

## Production notes
- Set `DEBUG=False`, a real `SECRET_KEY`, and `ALLOWED_HOSTS` via environment variables.
- Switch `DATABASES` to PostgreSQL.
- Serve with Gunicorn + Nginx + HTTPS; run `collectstatic`.
