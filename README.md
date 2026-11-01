# 🏠 RentEase – Rental Service Web Application

> **Aligning with UN SDG 11: Sustainable Cities and Communities**  
> A full-stack rental portal connecting Property Owners and Tenants built with Python 3.10+, Streamlit, and MySQL.

---

## 📁 Project Structure

```
rental_system/
├── database/
│   ├── schema.sql          # DDL: DB + tables + foreign keys + indexes
│   ├── seed_data.sql       # Realistic demo data (owners, tenants, properties, requests)
│   └── db_connection.py    # MySQL helper: execute_query, fetch_all, fetch_one
├── modules/
│   ├── auth.py             # Password hashing, registration, login, session guards
│   ├── owner_ops.py        # Owner CRUD: listings, requests (approve/reject)
│   ├── tenant_ops.py       # Tenant search, submit request, track applications
│   └── validators.py       # Email, phone, rent, URL, text sanitization
├── components/
│   ├── cards.py            # Reusable Streamlit UI cards and status badges
│   └── navbar.py           # Sidebar router (adapts per role)
├── app.py                  # Main entrypoint — session state, routing, all pages
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 🚀 Quick Start

### 1. Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or higher |
| MySQL Server | 8.0 or higher |
| pip | Latest |

---

### 2. Clone / Set Up the Project

```bash
cd rental_system
pip install -r requirements.txt
```

---

### 3. Configure the Database

**Step 1 – Create the schema:**
```sql
-- In MySQL Workbench or terminal:
SOURCE path/to/rental_system/database/schema.sql;
```

**Step 2 – Load seed data (optional but recommended for demo):**
```sql
SOURCE path/to/rental_system/database/seed_data.sql;
```

> **Note:** The seed data contains pre-hashed password placeholders. For a live demo, register new accounts through the app's Register tab. The app's `auth.py` will generate correct hashes automatically.

---

### 4. Configure Database Credentials

Database credentials are read from **environment variables** with sensible local defaults:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL server host |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | _(empty)_ | MySQL password |
| `DB_NAME` | `rental_db` | Database name |
| `DB_PORT` | `3306` | MySQL port |

**Set on Windows (PowerShell):**
```powershell
$env:DB_HOST     = "localhost"
$env:DB_USER     = "root"
$env:DB_PASSWORD = "your_password"
$env:DB_NAME     = "rental_db"
```

**Set on Linux/macOS:**
```bash
export DB_HOST=localhost
export DB_USER=root
export DB_PASSWORD=your_password
export DB_NAME=rental_db
```

Alternatively, edit `DB_CONFIG` directly in `database/db_connection.py` for local development.

---

### 5. Run the Application

```bash
cd rental_system
streamlit run app.py
```

The app will open at **http://localhost:8501** in your default browser.

---

## 👥 User Roles & Features

### 🏡 Tenant
| Feature | Description |
|---|---|
| **Explore Properties** | Multi-criteria search: city, type, rent range, furnishing, bedrooms |
| **Apply for Rental** | Submit application with proposed move-in date and a message |
| **My Requests** | Track all applications with live status badges |
| **Cancel Application** | Cancel pending applications before owner action |
| **Profile** | Update name, phone; change password |

### 🏢 Property Owner
| Feature | Description |
|---|---|
| **Add New Property** | List apartments, villas, studios, PG, independent houses |
| **My Listings** | View, edit, toggle availability, delete listings |
| **Incoming Requests** | Review tenant applications with full contact details |
| **Approve / Reject** | One-click approval auto-marks property unavailable + rejects others |
| **Profile** | Update name, phone; change password |

---

## 🔐 Security

- Passwords are hashed with **SHA-256 + app-level salt** (`hashlib`). No plaintext passwords are stored.
- All database queries use **parameterized statements** (`%s` placeholders) — SQL injection is not possible.
- Role-based routing enforced server-side: tenants cannot access owner pages and vice versa.
- Session state validated on every page render via `require_login()` / `require_role()` guards.

---

## 🗄️ Database Schema

```
users ──────────────────────────────────────────────
  user_id PK | full_name | email (UNIQUE) | password_hash
  phone | role ENUM(tenant, owner) | created_at

properties ─────────────────────────────────────────
  property_id PK | owner_id FK→users | title | description
  property_type ENUM | address | city (INDEXED)
  rent_monthly | security_deposit | bedrooms | bathrooms
  furnishing_status ENUM | is_available | image_url | created_at

rental_requests ────────────────────────────────────
  request_id PK | property_id FK→properties | tenant_id FK→users
  message | proposed_move_in_date | status ENUM | created_at | updated_at
```

All foreign keys use `ON DELETE CASCADE` — deleting a user removes their properties/requests automatically.

---

## 🧪 Demo Accounts

After running `seed_data.sql`, register accounts via the app's **Register** tab.  
Alternatively, these credentials match the seeded hashes **only** when registered through the app:

| Role | Email | Password |
|---|---|---|
| Owner | owner1@rentease.com | _(register via app)_ |
| Owner | owner2@rentease.com | _(register via app)_ |
| Tenant | tenant1@rentease.com | _(register via app)_ |

> **Tip:** Register a new owner and a new tenant via the app to get fully working accounts immediately.

---

## ⚙️ Environment

| Technology | Purpose |
|---|---|
| Python 3.10+ | Application language |
| Streamlit ≥ 1.32 | Web UI framework |
| MySQL 8.0+ | Relational database |
| mysql-connector-python | DB driver |
| hashlib (stdlib) | Password hashing |

---

## 📌 SDG 11 Alignment

RentEase supports **UN Sustainable Development Goal 11 – Sustainable Cities and Communities** by:
- Reducing information asymmetry between property seekers and owners.
- Enabling transparent, auditable rental processes.
- Promoting access to safe and affordable housing through a digital-first, inclusive platform.

---

*Built with ❤️ using Python & Streamlit.*
