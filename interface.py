"""
Hotel Management — Tkinter + SQLite (All-in-One) - FIXED IMAGE VERSION
Tabs:
  • POS (Menu/Orders) with image preview per item
  • Bookings (Rooms & Reservations)
  • Support (Customer Care Tickets) with CATEGORY DROPDOWN (+ add custom)
  • Reports (user activity: orders, bookings, tickets + totals)

DB: hotel.db (SQLite)
Assets: put PNG/JPGs into ./assets (e.g., assets/logo.png, assets/pizza.png)
Run: python hotel_app.py

Tested: Python 3.10–3.13, Windows OK (Pillow optional for images)
"""

from __future__ import annotations
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import datetime as dt

# ------------------------------ Paths ------------------------------ #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hotel.db")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Try to import Pillow for image support (optional)
try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# ------------------------------ Feature Flags ------------------------------ #
# If you want to overwrite whatever is in the DB and force the
# customer care categories to be exactly the list below, set this to True.
FORCE_CATEGORY_SET = True
# If True, will auto-create colored placeholder images. You don't want that.
USE_PLACEHOLDER_IMAGES = False


# ------------------------------ Database Layer ------------------------------ #

CREATE_TABLES_SQL = [
    # Menu & Orders
    """
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        price INTEGER NOT NULL CHECK(price >= 0),
        image_path TEXT, -- optional image path (relative to ASSETS_DIR or absolute)
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        phone TEXT,
        total INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        qty INTEGER NOT NULL CHECK(qty >= 1),
        line_total INTEGER NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY(item_id) REFERENCES menu_items(id) ON DELETE RESTRICT
    )
    """,
    # Customers
    """
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        UNIQUE(name, phone)
    )
    """,
    # Rooms & Bookings
    """
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_no TEXT NOT NULL UNIQUE,
        room_type TEXT NOT NULL,
        price_per_night INTEGER NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        room_id INTEGER NOT NULL,
        check_in TEXT NOT NULL,
        check_out TEXT NOT NULL,
        nights INTEGER NOT NULL,
        total INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Booked',
        FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
        FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE RESTRICT
    )
    """,
    # Support Tickets + Categories
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        category TEXT, -- dropdown value
        subject TEXT NOT NULL,
        message TEXT,
        status TEXT NOT NULL DEFAULT 'Open',
        created_at TEXT NOT NULL,
        FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ticket_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """,
]

# Seed menu with image filenames relative to ./assets/
# Place matching files in the assets folder (e.g., assets/pizza.png, assets/pasta.png, etc.)
MENU_SEED = [
    ("Pizza Margherita", "Main",    500, "pizza.png.png"),
    ("Pasta Alfredo",    "Main",    750, "pasta.png.png"),
    ("Spring Rolls",     "Starter", 525, "spring_rolls.png.png"),
    ("Garlic Bread",     "Starter", 350, "garlic_bread.png.png"),
    ("Brownie Ice-cream","Dessert", 450, "brownie.png.png"),
    ("Soft Drink",       "Beverage",250, "soda.png.png"),
    ("Mineral Water",    "Beverage",100, "water.png.png"),
]


ROOMS_SEED = [
    ("101", "Single", 3500),
    ("102", "Double", 5000),
    ("201", "Deluxe", 7500),
    ("301", "Suite", 12000),
]

# Your requested customer care categories (exact list)
SUPPORT_CATEGORIES_DEFAULT = [
    "Room Cleaning",
    "Food Delivery",
    "Taxi Service",
    "Laundry",
    "Complaint",
    "Other",
]

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(seed: bool = True) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        for sql in CREATE_TABLES_SQL:
            cur.execute(sql)
        # Backwards-compatible column adds if old DB exists
        try:
            cur.execute("PRAGMA table_info(tickets)")
            cols = {r[1] for r in cur.fetchall()}
            if "category" not in cols:
                cur.execute("ALTER TABLE tickets ADD COLUMN category TEXT")
        except Exception:
            pass
        try:
            cur.execute("PRAGMA table_info(menu_items)")
            cols = {r[1] for r in cur.fetchall()}
            if "image_path" not in cols:
                cur.execute("ALTER TABLE menu_items ADD COLUMN image_path TEXT")
        except Exception:
            pass

        if seed:
            for name, category, price, img in MENU_SEED:
                cur.execute(
                    "INSERT OR IGNORE INTO menu_items(name, category, price, image_path) VALUES (?,?,?,?)",
                    (name, category, price, img)
                )
            for room_no, room_type, price in ROOMS_SEED:
                cur.execute(
                    "INSERT OR IGNORE INTO rooms(room_no, room_type, price_per_night) VALUES (?,?,?)",
                    (room_no, room_type, price)
                )
            # If forcing, clear and set EXACT categories
            if FORCE_CATEGORY_SET:
                cur.execute("DELETE FROM ticket_categories")
            for cat in SUPPORT_CATEGORIES_DEFAULT:
                cur.execute("INSERT OR IGNORE INTO ticket_categories(name) VALUES (?)", (cat,))
        conn.commit()
    finally:
        conn.close()

# ------------------------------ Repos ------------------------------ #

@dataclass
class MenuItem:
    id: int
    name: str
    category: str
    price: int
    image_path: Optional[str]

class MenuRepo:
    @staticmethod
    def list_items(category: Optional[str] = None, search: str = "") -> List[MenuItem]:
        conn = get_conn()
        try:
            sql = "SELECT id, name, category, price, image_path FROM menu_items WHERE is_active = 1"
            params: List[object] = []
            if category and category != "All":
                sql += " AND category = ?"
                params.append(category)
            if search:
                sql += " AND name LIKE ?"
                params.append(f"%{search}%")
            sql += " ORDER BY category, name"
            cur = conn.execute(sql, params)
            return [MenuItem(*row) for row in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def categories() -> List[str]:
        conn = get_conn()
        try:
            cur = conn.execute("SELECT DISTINCT category FROM menu_items WHERE is_active = 1 ORDER BY category")
            cats = [r[0] for r in cur.fetchall()]
            return ["All"] + cats
        finally:
            conn.close()

class OrderRepo:
    @staticmethod
    def create_order(customer_name: str, phone: str, cart: Dict[int, int]) -> int:
        conn = get_conn()
        try:
            cur = conn.cursor()
            total = 0
            items: List[Tuple[int,int,int]] = []
            for item_id, qty in cart.items():
                cur.execute("SELECT price FROM menu_items WHERE id = ?", (item_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Menu item id {item_id} not found")
                price = int(row[0])
                line_total = price * qty
                total += line_total
                items.append((item_id, qty, line_total))
            now = dt.datetime.now().isoformat(timespec="seconds")
            cur.execute("INSERT INTO orders(customer_name, phone, total, created_at) VALUES (?,?,?,?)",
                        (customer_name, phone, total, now))
            order_id = int(cur.lastrowid)
            for item_id, qty, line_total in items:
                cur.execute("INSERT INTO order_items(order_id, item_id, qty, line_total) VALUES (?,?,?,?)",
                            (order_id, item_id, qty, line_total))
            conn.commit()
            return order_id
        finally:
            conn.close()

    @staticmethod
    def list_orders(name: Optional[str] = None, phone: Optional[str] = None) -> List[Tuple[int, str, str, str, int]]:
        """Return (id, created_at, customer_name, phone, total). Optional filters."""
        conn = get_conn()
        try:
            sql = "SELECT id, created_at, IFNULL(customer_name,''), IFNULL(phone,''), total FROM orders WHERE 1=1"
            params: List[object] = []
            if name:
                sql += " AND customer_name LIKE ?"; params.append(f"%{name}%")
            if phone:
                sql += " AND IFNULL(phone,'') LIKE ?"; params.append(f"%{phone}%")
            sql += " ORDER BY id DESC"
            return list(conn.execute(sql, params))
        finally:
            conn.close()

class CustomerRepo:
    @staticmethod
    def ensure_customer(name: str, phone: str = "", email: str = "") -> int:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM customers WHERE name = ? AND IFNULL(phone,'') = ?", (name, phone))
            row = cur.fetchone()
            if row:
                return int(row[0])
            cur.execute("INSERT INTO customers(name, phone, email) VALUES (?,?,?)", (name, phone, email))
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

class RoomRepo:
    @staticmethod
    def list_active() -> List[Tuple[int, str, str, int]]:
        conn = get_conn()
        try:
            cur = conn.execute("SELECT id, room_no, room_type, price_per_night FROM rooms WHERE is_active = 1 ORDER BY room_no")
            return cur.fetchall()
        finally:
            conn.close()

class BookingRepo:
    @staticmethod
    def create_booking(customer_name: str, phone: str, room_id: int, check_in: str, check_out: str) -> int:
        d1 = dt.date.fromisoformat(check_in)
        d2 = dt.date.fromisoformat(check_out)
        nights = (d2 - d1).days
        if nights <= 0:
            raise ValueError("Check-out must be after check-in")
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT price_per_night FROM rooms WHERE id = ?", (room_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Room not found")
            price = int(row[0])
            total = price * nights
            cust_id = CustomerRepo.ensure_customer(customer_name, phone)
            now = dt.datetime.now().isoformat(timespec="seconds")
            cur.execute(
                "INSERT INTO bookings(customer_id, room_id, check_in, check_out, nights, total, created_at, status) VALUES (?,?,?,?,?,?,?,?)",
                (cust_id, room_id, check_in, check_out, nights, total, now, 'Booked')
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    @staticmethod
    def list_bookings() -> List[Tuple[int, str, str, str, str, int, int, str]]:
        conn = get_conn()
        try:
            cur = conn.execute(
                """
                SELECT b.id,
                       c.name,
                       c.phone,
                       r.room_no,
                       r.room_type,
                       b.nights,
                       b.total,
                       b.status
                FROM bookings b
                JOIN customers c ON c.id = b.customer_id
                JOIN rooms r ON r.id = b.room_id
                ORDER BY b.id DESC
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def list_bookings_filtered(name: Optional[str] = None, phone: Optional[str] = None) -> List[Tuple[int, str, str, str, str, int, int, str, str]]:
        """Return (id, created_at, name, phone, room_no, room_type, nights, total, status)."""
        conn = get_conn()
        try:
            sql = (
                "SELECT b.id, b.created_at, c.name, c.phone, r.room_no, r.room_type, b.nights, b.total, b.status "
                "FROM bookings b JOIN customers c ON c.id=b.customer_id JOIN rooms r ON r.id=b.room_id WHERE 1=1"
            )
            params: List[object] = []
            if name:
                sql += " AND c.name LIKE ?"; params.append(f"%{name}%")
            if phone:
                sql += " AND IFNULL(c.phone,'') LIKE ?"; params.append(f"%{phone}%")
            sql += " ORDER BY b.id DESC"
            return list(conn.execute(sql, params))
        finally:
            conn.close()

class TicketRepo:
    @staticmethod
    def create_ticket(name: str, phone: str, category: str, subject: str, message: str) -> int:
        cust_id = CustomerRepo.ensure_customer(name, phone)
        now = dt.datetime.now().isoformat(timespec="seconds")
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO tickets(customer_id, category, subject, message, status, created_at) VALUES (?,?,?,?,?,?)",
                (cust_id, category, subject, message, 'Open', now)
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    @staticmethod
    def list_tickets() -> List[Tuple[int, str, str, str, str, str]]:
        conn = get_conn()
        try:
            cur = conn.execute(
                """
                SELECT t.id, c.name, c.phone, t.category, t.subject, t.status
                FROM tickets t
                LEFT JOIN customers c ON c.id = t.customer_id
                ORDER BY t.id DESC
                """
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def list_tickets_filtered(name: Optional[str] = None, phone: Optional[str] = None) -> List[Tuple[int, str, str, str, str, str, str]]:
        """Return (id, created_at, name, phone, category, subject, status)."""
        conn = get_conn()
        try:
            sql = (
                "SELECT t.id, t.created_at, c.name, c.phone, t.category, t.subject, t.status "
                "FROM tickets t LEFT JOIN customers c ON c.id=t.customer_id WHERE 1=1"
            )
            params: List[object] = []
            if name:
                sql += " AND c.name LIKE ?"; params.append(f"%{name}%")
            if phone:
                sql += " AND IFNULL(c.phone,'') LIKE ?"; params.append(f"%{phone}%")
            sql += " ORDER BY t.id DESC"
            return list(conn.execute(sql, params))
        finally:
            conn.close()

class TicketCategoryRepo:
    @staticmethod
    def list_active() -> List[str]:
        conn = get_conn()
        try:
            # Order by id to preserve insertion order (matches your numbered list)
            cur = conn.execute("SELECT name FROM ticket_categories WHERE is_active = 1 ORDER BY id")
            return [r[0] for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def add(name: str) -> None:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO ticket_categories(name) VALUES (?)", (name,))
            conn.commit()
        finally:
            conn.close()

# ------------------------------ UI Theme ------------------------------ #

class ThemedStyle(ttk.Style):
    def setup(self, root: tk.Tk):
        root.title("Hotel Raj Mahal — Management")
        root.geometry("1200x820")
        root.minsize(1100, 720)
        self.theme_use("clam")
        self._images = {}

        # Vibrant, eye-catching palette
        self.colors = {
            "primary": "#8B5CF6",       # violet
            "primary_dark": "#7C3AED",
            "bg": "#F8FAFC",            # very light
            "card": "#FFFFFF",
            "text": "#0F172A",          # slate-900
            "muted": "#64748B",         # slate-500
            "accent": "#22D3EE",        # cyan
            "accent2": "#F472B6",       # pink
            "accent3": "#F59E0B",       # amber
            "success": "#10B981",       # emerald
            "row_odd": "#F9FAFB",       # zebra rows
        }
        c = self.colors

        root.configure(bg=c["bg"])
        self.configure("TFrame", background=c["bg"]) 
        self.configure("Card.TFrame", background=c["card"]) 
        self.configure("H1.TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 22, "bold"))
        self.configure("H2.TLabel", background=c["bg"], foreground=c["text"], font=("Segoe UI", 14, "bold"))
        self.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"], font=("Segoe UI", 10))

        # Buttons
        self.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        self.map("Primary.TButton",
                 background=[("!disabled", c["primary"]), ("pressed", c["primary_dark"]), ("active", c["primary_dark"])],
                 foreground=[("!disabled", "#fff")])
        self.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=10)
        self.map("Accent.TButton",
                 background=[("!disabled", c["accent"]), ("pressed", c["accent2"]), ("active", c["accent2"])],
                 foreground=[("!disabled", "#0F172A")])

        # Tables
        self.configure("Menu.Treeview", background=c["card"], fieldbackground=c["card"], rowheight=28, font=("Segoe UI", 10))
        self.configure("Cart.Treeview", background=c["card"], fieldbackground=c["card"], rowheight=26, font=("Segoe UI", 10))
        self.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        # Notebook tabs (more colorful)
        self.configure("TNotebook", background=c["bg"], borderwidth=0)
        self.configure("TNotebook.Tab", padding=(16, 10), font=("Segoe UI", 10, "bold"))
        self.map("TNotebook.Tab",
                 background=[("selected", c["accent"])],
                 foreground=[("selected", "#0F172A"), ("!selected", c["text"])])

# ------------------------------ App Shell ------------------------------ #

class App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.pack(fill="both", expand=True)
        self.style = ThemedStyle(); self.style.setup(master)
        self._build_nav()
        self._build_tabs()

    def _build_nav(self):
        c = self.style.colors
        nav = ttk.Frame(self, style="TFrame")
        nav.pack(fill="x")
        banner = tk.Canvas(nav, height=110, bg=c["primary"], highlightthickness=0)
        banner.pack(fill="x")

        # Try showing a logo image if available
        text_x = 24
        if PIL_AVAILABLE:
            for candidate in ("logo.png", "logo.jpg", "hero.png"):
                p = os.path.join(ASSETS_DIR, candidate)
                if os.path.exists(p):
                    try:
                        img = Image.open(p).resize((90, 90), Image.LANCZOS)
                        self.style._images['logo'] = ImageTk.PhotoImage(img)
                        banner.create_image(24, 55, image=self.style._images['logo'], anchor="w")
                        text_x = 24 + 90 + 16
                        break
                    except Exception as e:
                        print(f"Failed to load logo {candidate}: {e}")
        # Title and subtitle on banner
        banner.create_text(text_x, 38, anchor="w", text="Hotel Raj Mahal", fill="white", font=("Segoe UI", 24, "bold"))
        banner.create_text(text_x, 68, anchor="w", text="Dashboard — POS • Bookings • Support • Reports", fill="#eef2ff", font=("Segoe UI", 12))
        # Decorative colorful shapes
        banner.create_oval(980, 10, 1140, 100, fill=self.style.colors["accent"], outline="")
        banner.create_oval(900, 26, 1030, 90, fill=self.style.colors["accent2"], outline="")
        banner.create_oval(1030, 40, 1180, 105, fill=self.style.colors["accent3"], outline="")

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=12)
        self.pos_tab = POSFrame(nb)
        nb.add(self.pos_tab, text="🧾 POS")
        self.book_tab = BookingFrame(nb)
        nb.add(self.book_tab, text="🛏️ Bookings")
        self.support_tab = SupportFrame(nb)
        nb.add(self.support_tab, text="💬 Support")
        self.report_tab = ReportsFrame(nb)
        nb.add(self.report_tab, text="📊 Reports")

# ------------------------------ POS (Menu/Orders) ------------------------------ #
def resolve_image_path(path: Optional[str]) -> Optional[str]:
    """Return an absolute path to an existing image. Tries a few variants."""
    if not path:
        return None

    # If given an absolute path, prefer it
    if os.path.isabs(path) and os.path.exists(path):
        return path

    # Try relative to assets
    cand = os.path.join(ASSETS_DIR, path)
    if os.path.exists(cand):
        return cand

    # Handle users who saved with/without double .png.png
    base = os.path.splitext(path)[0]
    variants = [
        path,                       # original
        f"{base}.png",              # .png
        f"{base}.jpg",              # .jpg
        f"{base}.jpeg",             # .jpeg
        f"{path}.png",              # foo.png -> foo.png.png
    ]
    for v in variants:
        cand = os.path.join(ASSETS_DIR, v)
        if os.path.exists(cand):
            return cand

    return None



class POSFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.cart: Dict[int, int] = {}
        self.preview_img = None  # keep ref for menu image
        self._build()
        self._refresh_categories()
        self._refresh_menu()
        self._refresh_cart()

    def _build(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        # Filters
        filters = ttk.Frame(left)
        filters.pack(fill="x", pady=(0, 8))
        ttk.Label(filters, text="Menu", style="H1.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filters, textvariable=self.search_var, width=28)
        search_entry.pack(side="right")
        search_entry.insert(0, "Search dishes...")
        search_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(search_entry, "Search dishes..."))
        search_entry.bind("<FocusOut>", lambda e: self._add_placeholder(search_entry, "Search dishes..."))
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_menu())
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(filters, textvariable=self.category_var, width=18, state="readonly")
        self.category_combo.pack(side="right", padx=8)
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_menu())
        # Menu + preview
        menu_card = ttk.Frame(left, style="Card.TFrame")
        menu_card.pack(fill="both", expand=True)
        cols = ("name", "category", "price")
        self.menu_tv = ttk.Treeview(menu_card, columns=cols, show="headings", style="Menu.Treeview")
        for cid, text, w, anchor in (
            ("name", "Item", 260, "w"),
            ("category", "Category", 120, "center"),
            ("price", "Price (PKR)", 120, "e"),
        ):
            self.menu_tv.heading(cid, text=text)
            self.menu_tv.column(cid, width=w, anchor=anchor)
        self.menu_tv.pack(side="left", fill="both", expand=True, padx=(12,6), pady=12)

        # Image preview panel
        self.preview_card = ttk.Frame(menu_card, style="Card.TFrame")
        self.preview_card.pack(side="left", fill="both", expand=False, padx=(6,12), pady=12)
        ttk.Label(self.preview_card, text="Preview", style="H2.TLabel").pack(anchor="w", padx=10, pady=(10,0))
        self.preview_canvas = tk.Canvas(self.preview_card, width=240, height=170, bg="#eef2ff", highlightthickness=0)
        self.preview_canvas.pack(padx=10, pady=10)
        self.menu_tv.bind("<<TreeviewSelect>>", lambda e: self._show_menu_image())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(4, 0))
        ttk.Button(btns, text="Add Selected", style="Primary.TButton", command=self._add_selected).pack(side="left")
        ttk.Button(btns, text="Remove Selected", command=self._remove_selected).pack(side="left", padx=8)

        # Right: cart
        right = ttk.Frame(main)
        right.pack(side="left", fill="y", padx=(16, 0))
        cart_card = ttk.Frame(right, style="Card.TFrame")
        cart_card.pack(fill="both", expand=True)
        ttk.Label(cart_card, text="Your Cart", style="H2.TLabel").pack(anchor="w", padx=12, pady=(12, 0))
        self.cart_tv = ttk.Treeview(cart_card, columns=("item", "qty", "price", "total"), show="headings", style="Cart.Treeview")
        for col, text, w, anchor in (
            ("item", "Item", 180, "w"),
            ("qty", "Qty", 50, "center"),
            ("price", "Price", 80, "e"),
            ("total", "Line Total", 100, "e"),
        ):
            self.cart_tv.heading(col, text=text)
            self.cart_tv.column(col, width=w, anchor=anchor)
        self.cart_tv.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        form = ttk.Frame(cart_card)
        form.pack(fill="x", padx=12)
        ttk.Label(form, text="Customer", width=10).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Label(form, text="Phone", width=10).grid(row=1, column=0, sticky="w", pady=2)
        self.name_var = tk.StringVar(); self.phone_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Entry(form, textvariable=self.phone_var).grid(row=1, column=1, sticky="ew", pady=2)
        form.grid_columnconfigure(1, weight=1)

        totals = ttk.Frame(cart_card)
        totals.pack(fill="x", padx=12, pady=8)
        self.total_var = tk.StringVar(value="0")
        ttk.Label(totals, text="Total (PKR):", style="H2.TLabel").pack(side="left")
        ttk.Label(totals, textvariable=self.total_var, style="H2.TLabel").pack(side="left", padx=(6, 0))
        actions = ttk.Frame(cart_card)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(actions, text="Clear Cart", command=self._clear_cart).pack(side="left")
        ttk.Button(actions, text="Checkout", style="Primary.TButton", command=self._checkout).pack(side="right")

    # POS helpers
    def _clear_placeholder(self, entry: ttk.Entry, text: str):
        if entry.get() == text:
            entry.delete(0, tk.END)

    def _add_placeholder(self, entry: ttk.Entry, text: str):
        if not entry.get():
            entry.insert(0, text)

    def _refresh_categories(self):
        cats = MenuRepo.categories()
        self.category_combo["values"] = cats
        if self.category_var.get() not in cats:
            self.category_var.set("All")

    def _refresh_menu(self):
        for iid in self.menu_tv.get_children():
            self.menu_tv.delete(iid)
        category = self.category_var.get()
        search = self.search_var.get()
        if search == "Search dishes...":
            search = ""
        odd = False
        for item in MenuRepo.list_items(category=category, search=search):
            tag = ("odd",) if odd else ()
            self.menu_tv.insert("", "end", iid=str(item.id), values=(item.name, item.category, item.price), tags=tag)
            odd = not odd
        # zebra row style
        self.menu_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])
        # preview first selection if available
        children = self.menu_tv.get_children()
        if children:
            self.menu_tv.selection_set(children[0])
            self._show_menu_image()

    def _refresh_cart(self):
        for iid in self.cart_tv.get_children():
            self.cart_tv.delete(iid)
        total = 0
        conn = get_conn()
        try:
            cur = conn.cursor()
            odd = False
            for item_id, qty in self.cart.items():
                cur.execute("SELECT name, price FROM menu_items WHERE id = ?", (item_id,))
                row = cur.fetchone()
                if row:
                    name, price = row
                    line = price * qty
                    total += line
                    tag = ("odd",) if odd else ()
                    self.cart_tv.insert("", "end", iid=str(item_id), values=(name, qty, price, line), tags=tag)
                    odd = not odd
        finally:
            conn.close()
        self.cart_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])
        self.total_var.set(str(total))

    def _show_menu_image(self):
        sel = self.menu_tv.selection()
        if not sel:
            self.preview_canvas.delete("all")
            self.preview_canvas.create_text(120, 85, text="No item selected", font=("Segoe UI", 12), fill="#64748B")
            return
            
        item_id = int(sel[0])
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT image_path FROM menu_items WHERE id = ?", (item_id,))
            row = cur.fetchone()
            path = row[0] if row else None
        finally:
            conn.close()
            
        self.preview_canvas.delete("all")
        
        if not path:
            self.preview_canvas.create_text(120, 85, text="No image available", font=("Segoe UI", 12), fill="#64748B")
            return
            
        # Handle relative paths
        if not os.path.isabs(path):
            full_path = os.path.join(ASSETS_DIR, path)
        else:
            full_path = path
            
        if not os.path.exists(full_path):
            self.preview_canvas.create_text(120, 85, text="Image file not found", font=("Segoe UI", 10), fill="#ef4444")
            self.preview_canvas.create_text(120, 105, text=f"Looking for: {path}", font=("Segoe UI", 8), fill="#64748B")
            return
            
        if not PIL_AVAILABLE:
            self.preview_canvas.create_text(120, 85, text="Install Pillow package", font=("Segoe UI", 10), fill="#f59e0b")
            self.preview_canvas.create_text(120, 105, text="to view images", font=("Segoe UI", 10), fill="#f59e0b")
            return
            
        try:
            # Load and resize image with proper resampling
            img = Image.open(full_path)
            img = img.resize((240, 170), Image.LANCZOS)
            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_canvas.create_image(120, 85, image=self.preview_img, anchor="center")
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            self.preview_canvas.create_text(120, 85, text="Failed to load image", font=("Segoe UI", 10), fill="#ef4444")
            self.preview_canvas.create_text(120, 105, text=str(e)[:30] + "...", font=("Segoe UI", 8), fill="#64748B")

    def _add_selected(self):
        sel = self.menu_tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Please select an item to add.")
            return
        item_id = int(sel[0])
        self.cart[item_id] = self.cart.get(item_id, 0) + 1
        self._refresh_cart()

    def _remove_selected(self):
        sel = self.cart_tv.selection()
        if not sel:
            messagebox.showinfo("No selection", "Please select an item in cart to remove.")
            return
        item_id = int(sel[0])
        if item_id in self.cart:
            self.cart[item_id] -= 1
            if self.cart[item_id] <= 0:
                self.cart.pop(item_id)
        self._refresh_cart()

    def _clear_cart(self):
        self.cart.clear()
        self._refresh_cart()

    def _checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty cart", "Add items before checkout.")
            return
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        try:
            order_id = OrderRepo.create_order(customer_name=name, phone=phone, cart=self.cart)
            total = self.total_var.get()
            self._clear_cart()
            self.name_var.set("")
            self.phone_var.set("")
            messagebox.showinfo("Order Saved", f"Order #{order_id} placed. Total: PKR {total}")
        except Exception as e:
            messagebox.showerror("Checkout failed", str(e))

# ------------------------------ Bookings Tab ------------------------------ #

class BookingFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._build()
        self._refresh_rooms()
        self._refresh_bookings()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Bookings", style="H1.TLabel").pack(side="left")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0,12))
        form = ttk.Frame(left, style="Card.TFrame")
        form.pack(fill="x", padx=4, pady=4)
        # Customer
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Phone").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Room").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Check-in (YYYY-MM-DD)").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Check-out (YYYY-MM-DD)").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        self.c_name = tk.StringVar()
        self.c_phone = tk.StringVar()
        self.room_var = tk.StringVar()
        self.in_var = tk.StringVar()
        self.out_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.c_name, width=28).grid(row=0, column=1, padx=8, pady=6)
        ttk.Entry(form, textvariable=self.c_phone, width=28).grid(row=1, column=1, padx=8, pady=6)
        self.room_combo = ttk.Combobox(form, textvariable=self.room_var, state="readonly", width=25)
        self.room_combo.grid(row=2, column=1, padx=8, pady=6)
        ttk.Entry(form, textvariable=self.in_var, width=28).grid(row=3, column=1, padx=8, pady=6)
        ttk.Entry(form, textvariable=self.out_var, width=28).grid(row=4, column=1, padx=8, pady=6)
        ttk.Button(form, text="Create Booking", style="Primary.TButton", command=self._create_booking).grid(row=5, column=1, sticky="e", padx=8, pady=10)
        form.grid_columnconfigure(1, weight=1)

        # Right: bookings table
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        cols = ("id","name","phone","room","type","nights","total","status")
        self.book_tv = ttk.Treeview(right, columns=cols, show="headings")
        headers = [
            ("id","#",50,"center"), ("name","Name",160,"w"), ("phone","Phone",120,"center"),
            ("room","Room",70,"center"), ("type","Type",90,"center"), ("nights","Nights",70,"center"),
            ("total","Total",100,"e"), ("status","Status",100,"center")
        ]
        for cid, text, w, anchor in headers:
            self.book_tv.heading(cid, text=text)
            self.book_tv.column(cid, width=w, anchor=anchor)
        self.book_tv.pack(fill="both", expand=True, padx=4, pady=4)

    def _refresh_rooms(self):
        rooms = RoomRepo.list_active()
        self.room_map: Dict[str,int] = {}
        values = []
        for rid, rno, rtype, price in rooms:
            label = f"{rno} | {rtype} | PKR {price}"
            self.room_map[label] = rid
            values.append(label)
        self.room_combo["values"] = values
        if values:
            self.room_combo.current(0)

    def _create_booking(self):
        try:
            name = self.c_name.get().strip()
            phone = self.c_phone.get().strip()
            label = self.room_var.get()
            if not label:
                raise ValueError("Please select a room")
            room_id = self.room_map[label]
            check_in = self.in_var.get().strip()
            check_out = self.out_var.get().strip()
            bid = BookingRepo.create_booking(name, phone, room_id, check_in, check_out)
            messagebox.showinfo("Booking Saved", f"Booking #{bid} created")
            # Clear form
            self.c_name.set("")
            self.c_phone.set("")
            self.in_var.set("")
            self.out_var.set("")
            self._refresh_bookings()
        except Exception as e:
            messagebox.showerror("Booking failed", str(e))

    def _refresh_bookings(self):
        for iid in self.book_tv.get_children():
            self.book_tv.delete(iid)
        odd = False
        for row in BookingRepo.list_bookings():
            tag = ("odd",) if odd else ()
            self.book_tv.insert("", "end", values=row, tags=tag)
            odd = not odd
        self.book_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])

# ------------------------------ Support Tab ------------------------------ #

class SupportFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._build()
        self._refresh_categories()
        self._refresh_tickets()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Customer Care / Tickets", style="H1.TLabel").pack(side="left")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0,12))
        form = ttk.Frame(left, style="Card.TFrame")
        form.pack(fill="x", padx=4, pady=4)
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Phone").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Category").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Subject").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(form, text="Message").grid(row=4, column=0, sticky="nw", padx=8, pady=6)
        self.t_name = tk.StringVar()
        self.t_phone = tk.StringVar()
        self.t_subject = tk.StringVar()
        self.cat_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.t_name, width=28).grid(row=0, column=1, padx=8, pady=6)
        ttk.Entry(form, textvariable=self.t_phone, width=28).grid(row=1, column=1, padx=8, pady=6)
        rowcat = ttk.Frame(form)
        rowcat.grid(row=2, column=1, sticky="ew", padx=8, pady=6)
        self.cat_combo = ttk.Combobox(rowcat, textvariable=self.cat_var, state="readonly", width=22)
        self.cat_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(rowcat, text="+ Add", command=self._add_category).pack(side="left", padx=(6,0))
        ttk.Entry(form, textvariable=self.t_subject, width=28).grid(row=3, column=1, padx=8, pady=6)
        self.t_message = tk.Text(form, width=32, height=6)
        self.t_message.grid(row=4, column=1, padx=8, pady=6)
        ttk.Button(form, text="Create Ticket", style="Primary.TButton", command=self._create_ticket).grid(row=5, column=1, sticky="e", padx=8, pady=10)
        form.grid_columnconfigure(1, weight=1)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        cols = ("id","name","phone","category","subject","status")
        self.tickets_tv = ttk.Treeview(right, columns=cols, show="headings")
        headers = [
            ("id","#",50,"center"), ("name","Name",160,"w"), ("phone","Phone",120,"center"),
            ("category","Category",140,"center"), ("subject","Subject",220,"w"), ("status","Status",100,"center")
        ]
        for cid, text, w, anchor in headers:
            self.tickets_tv.heading(cid, text=text)
            self.tickets_tv.column(cid, width=w, anchor=anchor)
        self.tickets_tv.pack(fill="both", expand=True, padx=4, pady=4)

    def _create_ticket(self):
        try:
            name = self.t_name.get().strip()
            phone = self.t_phone.get().strip()
            subject = self.t_subject.get().strip()
            category = self.cat_var.get().strip()
            message = self.t_message.get("1.0", tk.END).strip()
            if not subject:
                raise ValueError("Subject is required")
            tid = TicketRepo.create_ticket(name, phone, category, subject, message)
            messagebox.showinfo("Ticket Created", f"Ticket #{tid} created")
            # Clear form
            self.t_message.delete("1.0", tk.END)
            self.t_subject.set("")
            self.t_name.set("")
            self.t_phone.set("")
            self._refresh_tickets()
        except Exception as e:
            messagebox.showerror("Ticket failed", str(e))

    def _refresh_tickets(self):
        for iid in self.tickets_tv.get_children():
            self.tickets_tv.delete(iid)
        odd = False
        for row in TicketRepo.list_tickets():
            tag = ("odd",) if odd else ()
            self.tickets_tv.insert("", "end", values=row, tags=tag)
            odd = not odd
        self.tickets_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])

    def _refresh_categories(self):
        """
        Refresh Customer Care categories dropdown.

        - Pulls active categories from DB.
        - If DB is empty, seeds your exact list:
          ["Room Cleaning", "Food Delivery", "Taxi Service", "Laundry", "Complaint", "Other"]
        - Keeps previous selection if still valid.
        """
        cats = TicketCategoryRepo.list_active()

        # Fallback + seed with your exact list if DB has none
        if not cats:
            for c in SUPPORT_CATEGORIES_DEFAULT:
                TicketCategoryRepo.add(c)  # INSERT OR IGNORE
            cats = SUPPORT_CATEGORIES_DEFAULT[:]

        # If DB set matches your desired set, enforce the exact order you want
        if set(cats) == set(SUPPORT_CATEGORIES_DEFAULT):
            cats = SUPPORT_CATEGORIES_DEFAULT[:]

        # Update combobox
        self.cat_combo["values"] = cats

        # Preserve current selection if possible
        current = self.cat_var.get().strip()
        if current in cats:
            self.cat_combo.set(current)
        elif cats:
            self.cat_combo.current(0)

    def _add_category(self):
        new = simpledialog.askstring("New Category", "Enter category name:")
        if not new:
            return
        new = new.strip()
        if not new:
            return
        TicketCategoryRepo.add(new)
        self._refresh_categories()

# ------------------------------ Reports Tab ------------------------------ #

class ReportsFrame(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Reports", style="H1.TLabel").pack(side="left")

        # Filters
        filt = ttk.Frame(self)
        filt.pack(fill="x", pady=8)
        ttk.Label(filt, text="Name").pack(side="left", padx=(0,6))
        self.f_name = tk.StringVar()
        ttk.Entry(filt, textvariable=self.f_name, width=22).pack(side="left", padx=(0,12))
        ttk.Label(filt, text="Phone").pack(side="left", padx=(0,6))
        self.f_phone = tk.StringVar()
        ttk.Entry(filt, textvariable=self.f_phone, width=18).pack(side="left", padx=(0,12))
        ttk.Button(filt, text="Search", style="Accent.TButton", command=self._search).pack(side="left")
        ttk.Button(filt, text="Clear", command=self._clear).pack(side="left", padx=(6,0))

        # Stats row
        stats = ttk.Frame(self, style="Card.TFrame")
        stats.pack(fill="x", pady=(0,8))
        self.stat_orders = tk.StringVar(value="Orders: 0 | Total PKR 0")
        self.stat_book = tk.StringVar(value="Bookings: 0 | Total PKR 0")
        self.stat_tickets = tk.StringVar(value="Tickets: 0")
        ttk.Label(stats, textvariable=self.stat_orders, style="H2.TLabel").pack(side="left", padx=12, pady=10)
        ttk.Label(stats, textvariable=self.stat_book, style="H2.TLabel").pack(side="left", padx=12)
        ttk.Label(stats, textvariable=self.stat_tickets, style="H2.TLabel").pack(side="left", padx=12)

        # Notebook with three tables
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        # Orders tab
        orders_tab = ttk.Frame(nb)
        nb.add(orders_tab, text="Orders")
        self.orders_tv = ttk.Treeview(orders_tab, columns=("id","when","name","phone","total"), show="headings")
        for cid, text, w, anchor in (
            ("id","#",60,"center"), ("when","Created",180,"center"), ("name","Name",200,"w"),
            ("phone","Phone",140,"center"), ("total","Total (PKR)",120,"e")
        ):
            self.orders_tv.heading(cid, text=text)
            self.orders_tv.column(cid, width=w, anchor=anchor)
        self.orders_tv.pack(fill="both", expand=True, padx=8, pady=8)

        # Bookings tab
        books_tab = ttk.Frame(nb)
        nb.add(books_tab, text="Bookings")
        self.books_tv = ttk.Treeview(books_tab, columns=("id","when","name","phone","room","type","nights","total","status"), show="headings")
        for cid, text, w, anchor in (
            ("id","#",60,"center"),("when","Created",180,"center"),("name","Name",160,"w"),("phone","Phone",120,"center"),
            ("room","Room",70,"center"),("type","Type",90,"center"),("nights","Nights",70,"center"),("total","Total (PKR)",120,"e"),("status","Status",100,"center")
        ):
            self.books_tv.heading(cid, text=text)
            self.books_tv.column(cid, width=w, anchor=anchor)
        self.books_tv.pack(fill="both", expand=True, padx=8, pady=8)

        # Tickets tab
        tickets_tab = ttk.Frame(nb)
        nb.add(tickets_tab, text="Tickets")
        self.tix_tv = ttk.Treeview(tickets_tab, columns=("id","when","name","phone","category","subject","status"), show="headings")
        for cid, text, w, anchor in (
            ("id","#",60,"center"),("when","Created",180,"center"),("name","Name",160,"w"),("phone","Phone",120,"center"),
            ("category","Category",140,"center"),("subject","Subject",240,"w"),("status","Status",100,"center")
        ):
            self.tix_tv.heading(cid, text=text)
            self.tix_tv.column(cid, width=w, anchor=anchor)
        self.tix_tv.pack(fill="both", expand=True, padx=8, pady=8)

        # initial search (all)
        self._search()

    def _clear_tables(self):
        for tv in (self.orders_tv, self.books_tv, self.tix_tv):
            for iid in tv.get_children():
                tv.delete(iid)

    def _clear(self):
        self.f_name.set("")
        self.f_phone.set("")
        self._search()

    def _search(self):
        name = self.f_name.get().strip() or None
        phone = self.f_phone.get().strip() or None
        self._clear_tables()

        # Orders
        odd = False
        total_orders = 0
        sum_orders = 0
        for oid, created, oname, ophone, total in OrderRepo.list_orders(name=name, phone=phone):
            tag = ("odd",) if odd else ()
            self.orders_tv.insert("", "end", values=(oid, created, oname, ophone, total), tags=tag)
            odd = not odd
            total_orders += 1
            sum_orders += int(total)
        self.orders_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])

        # Bookings
        odd = False
        total_books = 0
        sum_books = 0
        for row in BookingRepo.list_bookings_filtered(name=name, phone=phone):
            bid, created, bname, bphone, room_no, rtype, nights, total, status = row
            tag = ("odd",) if odd else ()
            self.books_tv.insert("", "end", values=(bid, created, bname, bphone, room_no, rtype, nights, total, status), tags=tag)
            odd = not odd
            total_books += 1
            sum_books += int(total)
        self.books_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])

        # Tickets
        odd = False
        total_tix = 0
        for row in TicketRepo.list_tickets_filtered(name=name, phone=phone):
            tid, created, tname, tphone, cat, subj, status = row
            tag = ("odd",) if odd else ()
            self.tix_tv.insert("", "end", values=(tid, created, tname, tphone, cat, subj, status), tags=tag)
            odd = not odd
            total_tix += 1
        self.tix_tv.tag_configure('odd', background=self.master.master.style.colors["row_odd"])

        # Update stats
        self.stat_orders.set(f"Orders: {total_orders} | Total PKR {sum_orders}")
        self.stat_book.set(f"Bookings: {total_books} | Total PKR {sum_books}")
        self.stat_tickets.set(f"Tickets: {total_tix}")

# ------------------------------ Utilities ------------------------------ #

def import_simple_menu(dict_like: Dict[str, int], category: str = "Main", default_image: Optional[str] = None) -> int:
    """Quickly import {name: price} into menu_items. Optionally set one image for all.
    Returns number of rows inserted (ignores existing by name).
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        count = 0
        for name, price in dict_like.items():
            cur.execute(
                "INSERT OR IGNORE INTO menu_items(name, category, price, image_path) VALUES (?,?,?,?)",
                (str(name).title(), category, int(price), default_image)
            )
            if cur.rowcount:
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()

def set_image_for(item_name: str, path: str) -> None:
    """Helper: set image_path for a dish. Accepts relative (assets/xyz.png) or absolute path."""
    conn = get_conn()
    try:
        conn.execute("UPDATE menu_items SET image_path = ? WHERE name = ?", (path, item_name))
        conn.commit()
    finally:
        conn.close()

def ensure_menu_images():
    """Backfill image_path for menu items if it is NULL/empty."""
    mapping = {
        "Pizza Margherita":  "pizza.png.png",
        "Pasta Alfredo":     "pasta.png.png",
        "Spring Rolls":      "spring_rolls.png.png",
        "Garlic Bread":      "garlic_bread.png.png",
        "Brownie Ice-cream": "brownie.png.png",
        "Soft Drink":        "soda.png.png",
        "Mineral Water":     "water.png.png",
    }
    conn = get_conn()
    try:
        cur = conn.cursor()
        for name, img in mapping.items():
            cur.execute(
                "UPDATE menu_items "
                "SET image_path = ? "
                "WHERE name = ? AND (image_path IS NULL OR image_path = '')",
                (img, name),
            )
        conn.commit()
    finally:
        conn.close()

def create_sample_images():
    """Create placeholder images for testing if PIL is available."""
    if not PIL_AVAILABLE:
        print("PIL not available - cannot create sample images")
        return
        
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # Define colors for different food items
    colors = {
        "pizza.png": "#FF6B35",      # Orange-red
        "pasta.png": "#F7931E",      # Orange  
        "spring_rolls.png": "#8BC34A", # Green
        "garlic_bread.png": "#D4AF37", # Gold
        "brownie.png": "#8B4513",    # Brown
        "soda.png": "#1E90FF",       # Blue
        "water.png": "#87CEEB",      # Sky blue
        "logo.png": "#8B5CF6"        # Purple
    }
    
    
    
    for filename, color in colors.items():
        filepath = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(filepath):
            try:
                # Create a simple colored rectangle with text
                img = Image.new('RGB', (300, 200), color)
                
                # Add text (basic fallback if no font available)
                try:
                    from PIL import ImageDraw, ImageFont
                    draw = ImageDraw.Draw(img)
                    
                    # Try to use a system font
                    try:
                        font = ImageFont.truetype("arial.ttf", 24)
                    except:
                        try:
                            font = ImageFont.truetype("DejaVuSans.ttf", 24)
                        except:
                            font = ImageFont.load_default()
                    
                    # Get filename without extension for text
                    text = filename.replace('.png', '').replace('_', ' ').title()
                    
                    # Get text size and center it
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (300 - text_width) // 2
                    y = (200 - text_height) // 2
                    
                    # Add text with contrasting color
                    text_color = "white" if color in ["#8B4513", "#8B5CF6", "#1E90FF"] else "black"
                    draw.text((x, y), text, fill=text_color, font=font)
                    
                except ImportError:
                    # If ImageDraw not available, just save the colored rectangle
                    pass
                
                img.save(filepath)
                print(f"Created sample image: {filepath}")
                
            except Exception as e:
                print(f"Failed to create {filepath}: {e}")

# ------------------------------ Main ------------------------------ #

def main():
    """Main entry point - initialize database and start the GUI."""
    # Ensure assets directory exists
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    # Initialize database with seed data
    init_db(seed=True)
    ensure_menu_images()
    
    # Create sample images only if you explicitly want them
    if USE_PLACEHOLDER_IMAGES:
        create_sample_images()
    
    # Print helpful information
    print("Hotel Management System Starting...")
    print(f"Database: {DB_PATH}")
    print(f"Assets folder: {ASSETS_DIR}")
    print(f"PIL available for images: {PIL_AVAILABLE}")
    
    if PIL_AVAILABLE:
        print("\nPlace your menu item images in the assets folder:")
        for name, _, _, img in MENU_SEED:
            print(f"  - {name}: {os.path.join(ASSETS_DIR, img)}")
    else:
        print("\nTo display images, install Pillow: pip install Pillow")
    
    # Start the GUI
    root = tk.Tk()
    app = App(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Application error: {e}")
        messagebox.showerror("Application Error", f"An error occurred: {e}")

    
    
if __name__ == "__main__":
    main()
