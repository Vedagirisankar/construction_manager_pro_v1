"""
Database module for Construction Company Management App
Uses SQLite for persistent local storage - data survives app close/restart
"""

import sqlite3
import os
from datetime import datetime

# Store DB in user's home directory / AppData for persistence
def get_db_path():
    if os.name == 'nt':  # Windows
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        db_dir = os.path.join(appdata, 'ConstructionPro')
    else:
        db_dir = os.path.join(os.path.expanduser('~'), '.ConstructionPro')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'construction.db')

DB_PATH = get_db_path()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Employees table
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        daily_wage REAL DEFAULT 0,
        joining_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Attendance table
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT DEFAULT 'present',
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )''')

    # Diesel/Fuel table (for drivers)
    c.execute('''CREATE TABLE IF NOT EXISTS fuel_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        vehicle TEXT,
        liters REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
    )''')

    # Materials table
    c.execute('''CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        material_name TEXT NOT NULL,
        load_weight REAL DEFAULT 0,
        empty_weight REAL DEFAULT 0,
        net_weight REAL DEFAULT 0,
        supplier TEXT,
        vehicle_no TEXT,
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # GST Billing table
    c.execute('''CREATE TABLE IF NOT EXISTS gst_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no TEXT UNIQUE NOT NULL,
        bill_date TEXT NOT NULL,
        client_name TEXT NOT NULL,
        client_address TEXT,
        client_gstin TEXT,
        company_name TEXT DEFAULT 'Your Construction Company',
        company_gstin TEXT,
        subtotal REAL DEFAULT 0,
        cgst_rate REAL DEFAULT 9,
        sgst_rate REAL DEFAULT 9,
        cgst_amount REAL DEFAULT 0,
        sgst_amount REAL DEFAULT 0,
        total REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # GST Bill Items
    c.execute('''CREATE TABLE IF NOT EXISTS gst_bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        hsn_code TEXT,
        quantity REAL DEFAULT 1,
        unit TEXT DEFAULT 'Nos',
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        FOREIGN KEY(bill_id) REFERENCES gst_bills(id) ON DELETE CASCADE
    )''')

    # Diesel Fuel Details Log (standalone register — not per employee)
    c.execute('''CREATE TABLE IF NOT EXISTS diesel_fuel_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sl_no INTEGER,
        date TEXT NOT NULL,
        vehicle_no TEXT NOT NULL,
        qty_liters REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Cement Details Log
    c.execute('''CREATE TABLE IF NOT EXISTS cement_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        qty REAL DEFAULT 0,
        from_location TEXT,
        to_location TEXT,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Company settings
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    # Insert default settings
    defaults = [
        ('company_name', 'Sri Ram Construction Co.'),
        ('company_address', '123 Builder Street, Chennai, Tamil Nadu - 600001'),
        ('company_gstin', '33ABCDE1234F1Z5'),
        ('company_phone', '+91 98765 43210'),
        ('company_email', 'info@sriramconstruction.com'),
    ]
    for key, value in defaults:
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

# ─── Employee CRUD ────────────────────────────────────────────────────────────

def add_employee(name, role, phone='', address='', daily_wage=0, joining_date=''):
    conn = get_connection()
    conn.execute(
        'INSERT INTO employees (name, role, phone, address, daily_wage, joining_date) VALUES (?,?,?,?,?,?)',
        (name, role, phone, address, daily_wage, joining_date or datetime.now().strftime('%Y-%m-%d'))
    )
    conn.commit()
    conn.close()

def get_all_employees():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM employees ORDER BY name').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_employee(emp_id):
    conn = get_connection()
    row = conn.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_employee(emp_id, name, role, phone, address, daily_wage, joining_date):
    conn = get_connection()
    conn.execute(
        'UPDATE employees SET name=?, role=?, phone=?, address=?, daily_wage=?, joining_date=? WHERE id=?',
        (name, role, phone, address, daily_wage, joining_date, emp_id)
    )
    conn.commit()
    conn.close()

def delete_employee(emp_id):
    conn = get_connection()
    conn.execute('DELETE FROM employees WHERE id=?', (emp_id,))
    conn.commit()
    conn.close()

# ─── Attendance ───────────────────────────────────────────────────────────────

def add_attendance(employee_id, date, status='present', notes=''):
    conn = get_connection()
    # Upsert - update if date already exists for employee
    existing = conn.execute(
        'SELECT id FROM attendance WHERE employee_id=? AND date=?', (employee_id, date)
    ).fetchone()
    if existing:
        conn.execute('UPDATE attendance SET status=?, notes=? WHERE id=?', (status, notes, existing['id']))
    else:
        conn.execute('INSERT INTO attendance (employee_id, date, status, notes) VALUES (?,?,?,?)',
                     (employee_id, date, status, notes))
    conn.commit()
    conn.close()

def get_attendance(employee_id, from_date=None, to_date=None):
    conn = get_connection()
    query = 'SELECT * FROM attendance WHERE employee_id=?'
    params = [employee_id]
    if from_date:
        query += ' AND date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND date <= ?'
        params.append(to_date)
    query += ' ORDER BY date DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_attendance_summary(employee_id, month=None, year=None):
    conn = get_connection()
    if month and year:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM attendance WHERE employee_id=? AND strftime('%Y-%m', date)=? GROUP BY status",
            (employee_id, f"{year}-{month:02d}")
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT status, COUNT(*) as cnt FROM attendance WHERE employee_id=? GROUP BY status',
            (employee_id,)
        ).fetchall()
    conn.close()
    return {r['status']: r['cnt'] for r in rows}

# ─── Fuel Log ─────────────────────────────────────────────────────────────────

def add_fuel_log(employee_id, date, vehicle, liters, amount, notes=''):
    conn = get_connection()
    conn.execute('INSERT INTO fuel_log (employee_id, date, vehicle, liters, amount, notes) VALUES (?,?,?,?,?,?)',
                 (employee_id, date, vehicle, liters, amount, notes))
    conn.commit()
    conn.close()

def get_fuel_logs(employee_id, from_date=None, to_date=None):
    conn = get_connection()
    query = 'SELECT * FROM fuel_log WHERE employee_id=?'
    params = [employee_id]
    if from_date:
        query += ' AND date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND date <= ?'
        params.append(to_date)
    query += ' ORDER BY date DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_fuel_log(log_id):
    conn = get_connection()
    conn.execute('DELETE FROM fuel_log WHERE id=?', (log_id,))
    conn.commit()
    conn.close()

# ─── Materials ────────────────────────────────────────────────────────────────

def add_material(date, material_name, load_weight, empty_weight, net_weight,
                 supplier='', vehicle_no='', rate=0, amount=0, notes=''):
    conn = get_connection()
    conn.execute(
        'INSERT INTO materials (date, material_name, load_weight, empty_weight, net_weight, supplier, vehicle_no, rate, amount, notes) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (date, material_name, load_weight, empty_weight, net_weight, supplier, vehicle_no, rate, amount, notes)
    )
    conn.commit()
    conn.close()

def get_materials(from_date=None, to_date=None, material_name=None):
    conn = get_connection()
    query = 'SELECT * FROM materials WHERE 1=1'
    params = []
    if from_date:
        query += ' AND date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND date <= ?'
        params.append(to_date)
    if material_name:
        query += ' AND material_name LIKE ?'
        params.append(f'%{material_name}%')
    query += ' ORDER BY date DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_material(mat_id):
    conn = get_connection()
    conn.execute('DELETE FROM materials WHERE id=?', (mat_id,))
    conn.commit()
    conn.close()

# ─── GST Billing ──────────────────────────────────────────────────────────────

def generate_bill_no():
    conn = get_connection()
    count = conn.execute('SELECT COUNT(*) as c FROM gst_bills').fetchone()['c']
    conn.close()
    return f"BILL-{datetime.now().strftime('%Y%m')}-{count+1:04d}"

def add_gst_bill(bill_date, client_name, client_address, client_gstin, items,
                 cgst_rate=9, sgst_rate=9, notes=''):
    conn = get_connection()
    settings = {r['key']: r['value'] for r in conn.execute('SELECT * FROM settings').fetchall()}
    bill_no = generate_bill_no()
    subtotal = sum(i['amount'] for i in items)
    cgst = subtotal * cgst_rate / 100
    sgst = subtotal * sgst_rate / 100
    total = subtotal + cgst + sgst
    cur = conn.execute(
        '''INSERT INTO gst_bills (bill_no, bill_date, client_name, client_address, client_gstin,
           company_name, company_gstin, subtotal, cgst_rate, sgst_rate, cgst_amount, sgst_amount, total, notes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (bill_no, bill_date, client_name, client_address, client_gstin,
         settings.get('company_name', ''), settings.get('company_gstin', ''),
         subtotal, cgst_rate, sgst_rate, cgst, sgst, total, notes)
    )
    bill_id = cur.lastrowid
    for item in items:
        conn.execute(
            'INSERT INTO gst_bill_items (bill_id, description, hsn_code, quantity, unit, rate, amount) VALUES (?,?,?,?,?,?,?)',
            (bill_id, item['description'], item.get('hsn_code', ''), item['quantity'],
             item.get('unit', 'Nos'), item['rate'], item['amount'])
        )
    conn.commit()
    conn.close()
    return bill_no

def get_all_bills():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM gst_bills ORDER BY created_at DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_bill_with_items(bill_id):
    conn = get_connection()
    bill = dict(conn.execute('SELECT * FROM gst_bills WHERE id=?', (bill_id,)).fetchone())
    items = [dict(r) for r in conn.execute('SELECT * FROM gst_bill_items WHERE bill_id=?', (bill_id,)).fetchall()]
    conn.close()
    return bill, items

def delete_bill(bill_id):
    conn = get_connection()
    conn.execute('DELETE FROM gst_bills WHERE id=?', (bill_id,))
    conn.commit()
    conn.close()

# ─── Settings ─────────────────────────────────────────────────────────────────

def get_settings():
    conn = get_connection()
    rows = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_setting(key, value):
    conn = get_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, value))
    conn.commit()
    conn.close()

# ─── Diesel Fuel Log (Standalone Register) ────────────────────────────────────

def get_next_diesel_sl_no():
    conn = get_connection()
    row = conn.execute('SELECT MAX(sl_no) as m FROM diesel_fuel_log').fetchone()
    conn.close()
    return (row['m'] or 0) + 1

def add_diesel_fuel(date, vehicle_no, qty_liters, amount):
    sl_no = get_next_diesel_sl_no()
    conn = get_connection()
    conn.execute(
        'INSERT INTO diesel_fuel_log (sl_no, date, vehicle_no, qty_liters, amount) VALUES (?,?,?,?,?)',
        (sl_no, date, vehicle_no, qty_liters, amount)
    )
    conn.commit()
    conn.close()

def get_diesel_fuels(from_date=None, to_date=None, vehicle_no=None):
    conn = get_connection()
    query = 'SELECT * FROM diesel_fuel_log WHERE 1=1'
    params = []
    if from_date:
        query += ' AND date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND date <= ?'
        params.append(to_date)
    if vehicle_no:
        query += ' AND vehicle_no LIKE ?'
        params.append(f'%{vehicle_no}%')
    query += ' ORDER BY sl_no DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_diesel_fuel(rec_id, date, vehicle_no, qty_liters, amount):
    conn = get_connection()
    conn.execute(
        'UPDATE diesel_fuel_log SET date=?, vehicle_no=?, qty_liters=?, amount=? WHERE id=?',
        (date, vehicle_no, qty_liters, amount, rec_id)
    )
    conn.commit()
    conn.close()

def delete_diesel_fuel(rec_id):
    conn = get_connection()
    conn.execute('DELETE FROM diesel_fuel_log WHERE id=?', (rec_id,))
    conn.commit()
    conn.close()

# ─── Cement Log ───────────────────────────────────────────────────────────────

def add_cement_log(date, qty, from_location, to_location, details=''):
    conn = get_connection()
    conn.execute(
        'INSERT INTO cement_log (date, qty, from_location, to_location, details) VALUES (?,?,?,?,?)',
        (date, qty, from_location, to_location, details)
    )
    conn.commit()
    conn.close()

def get_cement_logs(from_date=None, to_date=None, location=None):
    conn = get_connection()
    query = 'SELECT * FROM cement_log WHERE 1=1'
    params = []
    if from_date:
        query += ' AND date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND date <= ?'
        params.append(to_date)
    if location:
        query += ' AND (from_location LIKE ? OR to_location LIKE ?)'
        params += [f'%{location}%', f'%{location}%']
    query += ' ORDER BY date DESC, id DESC'
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_cement_log(rec_id, date, qty, from_location, to_location, details):
    conn = get_connection()
    conn.execute(
        'UPDATE cement_log SET date=?, qty=?, from_location=?, to_location=?, details=? WHERE id=?',
        (date, qty, from_location, to_location, details, rec_id)
    )
    conn.commit()
    conn.close()

def delete_cement_log(rec_id):
    conn = get_connection()
    conn.execute('DELETE FROM cement_log WHERE id=?', (rec_id,))
    conn.commit()
    conn.close()
