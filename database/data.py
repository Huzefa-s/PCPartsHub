from django.db import connection, IntegrityError
import urllib.request
import base64
from django.contrib.auth.hashers import make_password, check_password

"""
Data-access helpers for the crochetAdmin app.

Aligned with:
- The database schema defined in `database/schema.txt`
- The helper patterns used in `crochetStore/database/data.py`

Key conventions from `schema.txt`:
- Table names  : Users, Items, ItemsQuant, Category, SubCategory,
                 Orders, OrderItems, Cart, Wishlist, Complaint, Address, UserAddress
- Primary keys : user_id, item_id, itemQuant_id, cat_id, subcat_id,
                 order_id, orderItem_id, cart_id, wishlist_id, complaint_id, addr_id

Note: The `image` column in Items table is BLOB (binary data), not a URL string.

SQLite note: All raw SQL uses ? placeholders (not %s) for parametrised queries.
             Django's connection.cursor() translates %s → ? for SQLite automatically
             when using cursor.execute(sql, params), but explicit ? is safer.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rows_to_dicts(cursor):
    """Convert cursor result set to a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def custom_sql_select(query, params=None):
    """
    Run a raw SELECT query and return a list of dicts.
    Use only for internal/admin tooling where `query` is trusted.
    Accepts optional params list for parameterised queries.
    """
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        return _rows_to_dicts(cursor)


# ---------------------------------------------------------------------------
# User helpers  (table: Users)
# ---------------------------------------------------------------------------

def login_sql_select(email, password):
    """
    Admin / staff login using the shared `Users` table.
    Returns the matching user dict, or False if not found.
    """
    with connection.cursor() as cursor:
        # Fetch user by email only
        cursor.execute(
            "SELECT * FROM Users WHERE email = %s",
            [email],
        )
        rows = _rows_to_dicts(cursor)

        if not rows:
            return False

        user = rows[0]

        # Verify hashed password
        if check_password(password, user["password"]):
            return user

        return False


def login_by_username(username, password):
    """
    Fallback login using the `name` column instead of email.
    Allows staff to sign in with their display name or an employee ID
    stored in the name field, in addition to their email address.
    Returns the matching user dict, or False if not found.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM Users WHERE name = %s AND password = %s",
            [username, password],
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return rows[0] if rows else False
 

def register_sql_insert(name, email, password, phone=None, role="customer"):
    """
    Insert a new user row into `Users`.
    Returns the new user_id.
    """
    # Hash password using Django's hasher
    hashed_password = make_password(password)

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Users (name, email, password, phone, role) VALUES (%s, %s, %s, %s, %s)",
            [name, email, hashed_password, phone, role],
        )
        connection.commit()
        return cursor.lastrowid



def register_user_if_new(name, email, password, phone=None, role="customer"):
    """
    Insert a user only if the email does not already exist.
    Returns the new user_id, or None if the email is already taken.
    """
    # Hash password before attempting insert
    hashed_password = make_password(password)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Users (name, email, password, phone, role) VALUES (%s, %s, %s, %s, %s)",
                [name, email, hashed_password, phone, role],
            )
            connection.commit()
            return cursor.lastrowid

    except IntegrityError:
        # This assumes email has a UNIQUE constraint in DB
        return None


def get_user_by_email(email):
    """Fetch a single user row by email. Returns dict or None."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE email = %s", [email])
        rows = _rows_to_dicts(cursor)
        return rows[0] if rows else None


def get_user_by_id(user_id):
    """Fetch a single user row by user_id. Returns dict or None."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Users WHERE user_id = %s", [user_id])
        rows = _rows_to_dicts(cursor)
        return rows[0] if rows else None


def change_user_password(user_id, old_password, new_password):
    """
    Change user password if old_password matches.
    """
    user = get_user_by_id(user_id)
    if not user:
        return False
    
    if not check_password(old_password, user["password"]):
        return False
        
    hashed_password = make_password(new_password)
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE Users SET password = %s WHERE user_id = %s",
            [hashed_password, user_id]
        )
        connection.commit()
        return cursor.rowcount > 0


def update_profile_sql(user_id, name=None, email=None, phone=None):
    """
    Update Users fields for a given user_id.
    Only updates fields that are not None.
    Used by staff (cannot change role).
    """
    fields, values = [], []

    if name  is not None: fields.append("name = %s");  values.append(name)
    if email is not None: fields.append("email = %s"); values.append(email)
    if phone is not None: fields.append("phone = %s"); values.append(phone)

    if not fields:
        return False

    values.append(user_id)
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE Users SET {', '.join(fields)} WHERE user_id = %s",
            values,
        )
        connection.commit()
        return cursor.rowcount > 0


def update_user(user_id, name, email, role, phone=None, notes=None):
    """
    Update core user fields including role.  Admin only.
    Also persists notes and phone when provided.
    """
    fields = ["name = %s", "email = %s", "role = %s"]
    values = [name, email, role]

    if phone is not None:
        fields.append("phone = %s")
        values.append(phone)
    if notes is not None:
        fields.append("notes = %s")
        values.append(notes)

    values.append(user_id)
    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE Users SET {', '.join(fields)} WHERE user_id = %s",
            values,
        )
        connection.commit()
        return cursor.rowcount > 0


def list_users():
    """
    Lightweight listing of all users for the admin Users tab.
    Includes notes so the user modal can pre-populate the Notes field.
    """
    sql = """
        SELECT user_id, name, email, role, phone,
               COALESCE(notes, '') AS notes,
               created_at
        FROM Users
        ORDER BY created_at DESC
    """
    return custom_sql_select(sql)


def search_users(query):
    """
    Search users by name, email, or role (case-insensitive partial match).
    Returns a list of user dicts with the same shape as list_users().
    """
    term = f"%{query}%"
    sql = """
        SELECT user_id, name, email, role, phone,
               COALESCE(notes, '') AS notes,
               created_at
        FROM Users
        WHERE name LIKE %s OR email LIKE %s OR role LIKE %s
        ORDER BY created_at DESC
    """
    return custom_sql_select(sql, [term, term, term])


def delete_user(user_id):
    """
    Delete a user and their associated non-order data.
    Orders are retained for records; user_id is set to NULL via FK.
    """
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM Cart        WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM Wishlist    WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM Complaint   WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM UserAddress WHERE user_id = %s", [user_id])
        cursor.execute("DELETE FROM Users       WHERE user_id = %s", [user_id])
        connection.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Item / inventory helpers  (Items, ItemsQuant, Category, SubCategory)
# ---------------------------------------------------------------------------

def get_items_by_ids(item_ids):
    """Return Items rows as dicts for the given list of item_ids."""
    if not item_ids:
        return []
    placeholders = ",".join(["%s"] * len(item_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT * FROM Items WHERE item_id IN ({placeholders})",
            list(item_ids),
        )
        return _rows_to_dicts(cursor)


def fetch_items(category=None, subcategory=None, search=None):
    """
    Return items optionally filtered by category, subcategory, and/or a
    name search term (case-insensitive partial match).
    Joins Items → SubCategory → Category.
    """
    sql = """
        SELECT i.* FROM Items i
        LEFT JOIN SubCategory s ON i.item_id = s.item_id
        LEFT JOIN Category c ON s.cat_id = c.cat_id
    """
    conditions, params = [], []
    if category:
        conditions.append("c.categoryName = %s"); params.append(category)
    if subcategory:
        conditions.append("s.subCatName = %s");   params.append(subcategory)
    if search:
        conditions.append("i.itemName LIKE %s");   params.append(f"%{search}%")
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " GROUP BY i.item_id"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _rows_to_dicts(cursor)


def fetch_categories():
    """Return all category rows as dicts (cat_id, categoryName)."""
    return custom_sql_select("SELECT cat_id, categoryName FROM Category ORDER BY categoryName")


def get_item_by_id(item_id):
    """
    Fetch a single item by its id.
    Returns a dict or None.  Note: image field is raw BLOB bytes.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Items WHERE item_id = %s", [item_id])
        rows = _rows_to_dicts(cursor)
        return rows[0] if rows else None


def get_product_image(item_id):
    """
    Return the raw BLOB bytes stored in Items.image for item_id.
    Returns bytes if found and non-empty, otherwise None.
    Called directly by get_product_image_view() in views.py.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT image FROM Items WHERE item_id = %s",
            [item_id],
        )
        row = cursor.fetchone()
        if row and row[0]:
            return bytes(row[0])
        return None


def url_to_blob(image_url):
    """
    Download an image from a URL / data URI / file path and return bytes
    for SQLite BLOB storage.  Returns None on failure.

    Supported sources:
      - data:image/...;base64,...   (inline data URI)
      - file:///path/to/image       (local file URI)
      - http:// or https://         (remote URL)
      - /path/to/image              (bare filesystem path)
    """
    if not image_url or not image_url.strip():
        return None

    image_url = image_url.strip()

    if image_url.startswith("data:image"):
        try:
            _, encoded = image_url.split(",", 1)
            return base64.b64decode(encoded)
        except Exception:
            return None

    if image_url.startswith("file://"):
        try:
            with open(image_url.replace("file://", ""), "rb") as f:
                return f.read()
        except Exception:
            return None

    if image_url.startswith("http://") or image_url.startswith("https://"):
        try:
            req = urllib.request.Request(image_url)
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read()
        except Exception:
            return None

    try:
        with open(image_url, "rb") as f:
            return f.read()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Admin CRUD helpers — Products
# ---------------------------------------------------------------------------

def list_products():
    """
    Aggregate product listing for the admin Products table.

    Returns per-product totals plus category, short_desc, and full_desc
    that the product modal needs to pre-populate on edit.
    The BLOB image column is excluded for performance; has_image flag
    lets the template decide whether to render the <img> tag.
    """
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            i.basePrice,
            COALESCE(i.short_desc, '')                      AS short_desc,
            COALESCE(i.full_desc,  '')                      AS full_desc,
            COALESCE(SUM(iq.stock), 0)                      AS total_stock,
            CASE WHEN i.image IS NOT NULL THEN 1 ELSE 0 END AS has_image,
            COALESCE(
                (SELECT c.categoryName
                 FROM SubCategory sc
                 JOIN Category c ON sc.cat_id = c.cat_id
                 WHERE sc.item_id = i.item_id
                 ORDER BY sc.subcat_id
                 LIMIT 1),
                ''
            ) AS category
        FROM Items i
        LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
        GROUP BY i.item_id, i.itemName, i.basePrice, i.short_desc, i.full_desc, i.image
        ORDER BY i.item_id DESC
    """
    return custom_sql_select(sql)


def search_products(query):
    """
    Search products by name (case-insensitive partial match).
    Returns the same shape as list_products() for easy template reuse.
    """
    term = f"%{query}%"
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            i.basePrice,
            COALESCE(i.short_desc, '') AS short_desc,
            COALESCE(i.full_desc,  '') AS full_desc,
            COALESCE(SUM(iq.stock), 0) AS total_stock,
            CASE WHEN i.image IS NOT NULL THEN 1 ELSE 0 END AS has_image,
            COALESCE(
                (SELECT c.categoryName
                 FROM SubCategory sc
                 JOIN Category c ON sc.cat_id = c.cat_id
                 WHERE sc.item_id = i.item_id
                 LIMIT 1),
                ''
            ) AS category
        FROM Items i
        LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
        WHERE i.itemName LIKE %s
        GROUP BY i.item_id
        ORDER BY i.item_id DESC
    """
    return custom_sql_select(sql, [term])


def get_product(item_id):
    """
    Fetch a single product with its first ItemsQuant variant and category.
    Used when pre-filling the edit modal with full detail.
    """
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            i.basePrice,
            COALESCE(i.short_desc, '') AS short_desc,
            COALESCE(i.full_desc,  '') AS full_desc,
            CASE WHEN i.image IS NOT NULL THEN 1 ELSE 0 END AS has_image,
            iq.itemQuant_id,
            iq.color,
            iq.stock,
            iq.description,
            COALESCE(
                (SELECT c.categoryName
                 FROM SubCategory sc
                 JOIN Category c ON sc.cat_id = c.cat_id
                 WHERE sc.item_id = i.item_id
                 LIMIT 1),
                ''
            ) AS category
        FROM Items i
        LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
        WHERE i.item_id = %s
        ORDER BY iq.itemQuant_id
        LIMIT 1
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [item_id])
        rows = _rows_to_dicts(cursor)
        return rows[0] if rows else None


def save_product(item_id, name, price, stock, short_desc, full_desc, image, color="default"):
    """
    Create or update a product.

    Parameters
    ----------
    item_id   : int or None — None means create new
    name      : str
    price     : float
    stock     : int
    short_desc: str
    full_desc : str
    image     : bytes or None
                Raw image bytes to store in the BLOB column.
                Pass None to leave the existing image untouched on update.
                Pass b'' (empty bytes) to explicitly clear the image.
    color     : str — ItemsQuant variant label (default 'default')

    Returns the item_id (new or existing).
    """
    description = " - ".join(filter(None, [
        (short_desc or "").strip(),
        (full_desc  or "").strip(),
    ]))

    with connection.cursor() as cursor:
        if not item_id:
            # ── INSERT new product ──────────────────────────────────────────
            cursor.execute(
                """
                INSERT INTO Items (itemName, basePrice, short_desc, full_desc, image)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [name, price, (short_desc or "").strip(), (full_desc or "").strip(), image],
            )
            item_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO ItemsQuant (item_id, color, stock, description)
                VALUES (%s, %s, %s, %s)
                """,
                [item_id, color, stock, description],
            )
        else:
            # ── UPDATE existing product ─────────────────────────────────────
            if image is not None:
                cursor.execute(
                    """
                    UPDATE Items
                    SET itemName = %s, basePrice = %s,
                        short_desc = %s, full_desc = %s, image = %s
                    WHERE item_id = %s
                    """,
                    [name, price,
                     (short_desc or "").strip(), (full_desc or "").strip(),
                     image, item_id],
                )
            else:
                cursor.execute(
                    """
                    UPDATE Items
                    SET itemName = %s, basePrice = %s,
                        short_desc = %s, full_desc = %s
                    WHERE item_id = %s
                    """,
                    [name, price,
                     (short_desc or "").strip(), (full_desc or "").strip(),
                     item_id],
                )

            # Upsert the primary ItemsQuant variant
            cursor.execute(
                """
                SELECT itemQuant_id FROM ItemsQuant
                WHERE item_id = %s
                ORDER BY itemQuant_id
                LIMIT 1
                """,
                [item_id],
            )
            existing_variant = cursor.fetchone()
            if existing_variant:
                cursor.execute(
                    """
                    UPDATE ItemsQuant
                    SET color = %s, stock = %s, description = %s
                    WHERE itemQuant_id = %s
                    """,
                    [color, stock, description, existing_variant[0]],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO ItemsQuant (item_id, color, stock, description)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [item_id, color, stock, description],
                )

        connection.commit()
        return item_id


def delete_product(item_id):
    """
    Delete a product and all dependent rows to satisfy foreign keys.

    Deletion order (per schema.txt):
    - OrderItems, Cart, Wishlist  (FK → ItemsQuant.itemQuant_id)
    - ItemsQuant                  (FK → Items.item_id)
    - SubCategory                 (FK → Items.item_id)
    - Items                       (root row)
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT itemQuant_id FROM ItemsQuant WHERE item_id = %s",
            [item_id],
        )
        quant_ids = [row[0] for row in cursor.fetchall()]

        if quant_ids:
            ph = ",".join(["%s"] * len(quant_ids))
            cursor.execute(f"DELETE FROM OrderItems WHERE itemQuant_id IN ({ph})", quant_ids)
            cursor.execute(f"DELETE FROM Cart       WHERE itemQuant_id IN ({ph})", quant_ids)
            cursor.execute(f"DELETE FROM Wishlist   WHERE itemQuant_id IN ({ph})", quant_ids)

        cursor.execute("DELETE FROM ItemsQuant  WHERE item_id = %s", [item_id])
        cursor.execute("DELETE FROM SubCategory WHERE item_id = %s", [item_id])
        cursor.execute("DELETE FROM Items       WHERE item_id = %s", [item_id])
        connection.commit()
        return True


# ---------------------------------------------------------------------------
# Order / Complaint helpers
# ---------------------------------------------------------------------------

def get_all_orders():
    """
    Fetch all orders with customer name and email.
    Used by the admin Orders tab and the dashboard Recent Orders table.
    """
    sql = """
        SELECT
            o.*,
            COALESCE(u.name,  'Deleted User') AS customer_name,
            COALESCE(u.email, '')              AS customer_email
        FROM Orders o
        LEFT JOIN Users u ON o.user_id = u.user_id
        ORDER BY o.order_date DESC
    """
    return custom_sql_select(sql)


def get_order_details(order_id):
    """
    Fetch a single order with its line items.
    Returns a list of dicts (one row per OrderItem); the order header
    fields are repeated on every row — views.py uses details[0] for header.
    The BLOB image column is intentionally excluded here.
    """
    sql = """
        SELECT
            o.order_id,
            o.user_id,
            o.order_date,
            o.order_status,
            o.totalPrice,
            o.staff_id,
            COALESCE(u.name,  'Deleted User') AS customer_name,
            COALESCE(u.email, '')              AS customer_email,
            oi.orderItem_id,
            oi.quantity,
            oi.price,
            iq.itemQuant_id,
            iq.color,
            iq.stock,
            iq.description AS item_description,
            i.item_id,
            i.itemName,
            i.basePrice
        FROM Orders o
        LEFT JOIN Users      u  ON o.user_id      = u.user_id
        LEFT JOIN OrderItems oi ON o.order_id     = oi.order_id
        LEFT JOIN ItemsQuant iq ON oi.itemQuant_id = iq.itemQuant_id
        LEFT JOIN Items      i  ON iq.item_id      = i.item_id
        WHERE o.order_id = %s
        ORDER BY oi.orderItem_id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [order_id])
        return _rows_to_dicts(cursor)


def get_orders_by_status(status):
    """Return all orders matching a given status string."""
    sql = """
        SELECT o.*, COALESCE(u.name, 'Deleted User') AS customer_name,
               COALESCE(u.email, '') AS customer_email
        FROM Orders o
        LEFT JOIN Users u ON o.user_id = u.user_id
        WHERE o.order_status = %s
        ORDER BY o.order_date DESC
    """
    return custom_sql_select(sql, [status])


def get_orders_by_date_range(start_date, end_date):
    """
    Return all orders placed between start_date and end_date (inclusive).
    Dates should be strings in 'YYYY-MM-DD' format.
    """
    sql = """
        SELECT o.*, COALESCE(u.name, 'Deleted User') AS customer_name,
               COALESCE(u.email, '') AS customer_email
        FROM Orders o
        LEFT JOIN Users u ON o.user_id = u.user_id
        WHERE DATE(o.order_date) BETWEEN %s AND %s
        ORDER BY o.order_date DESC
    """
    return custom_sql_select(sql, [start_date, end_date])


def update_order_status(order_id, status):
    """Update the status of a single order."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT order_status FROM Orders WHERE order_id = %s", [order_id])
        row = cursor.fetchone()
        if not row:
            return False
        
        old_status = row[0]
        if status == 'Cancelled' and old_status != 'Cancelled':
            cursor.execute("SELECT itemQuant_id, quantity FROM OrderItems WHERE order_id = %s", [order_id])
            for q_row in cursor.fetchall():
                cursor.execute("UPDATE ItemsQuant SET stock = stock + %s WHERE itemQuant_id = %s", [q_row[1], q_row[0]])

        cursor.execute(
            "UPDATE Orders SET order_status = %s WHERE order_id = %s",
            [status, order_id],
        )
        connection.commit()
        return cursor.rowcount > 0


def get_complaints(status=None):
    """
    Fetch complaints, optionally filtered by status.
    Joins Complaint with Users.
    """
    sql = """
        SELECT c.*, u.name AS user_name, u.email AS user_email
        FROM Complaint c
        LEFT JOIN Users u ON c.user_id = u.user_id
    """
    params = []
    if status:
        sql += " WHERE c.status = %s"
        params.append(status)
    sql += " ORDER BY c.created_at DESC"
    return custom_sql_select(sql, params)


def update_complaint_status(complaint_id, status):
    """Update the status of a complaint ('open', 'in_progress', 'resolved')."""
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE Complaint SET status = %s WHERE complaint_id = %s",
            [status, complaint_id],
        )
        connection.commit()
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Inventory helpers
# ---------------------------------------------------------------------------

def get_inventory_snapshot():
    """
    Stock snapshot combining Items and ItemsQuant.
    Excludes the BLOB image column; use get_product_image() or the
    image-serving endpoint for images.
    """
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            i.basePrice,
            iq.itemQuant_id,
            iq.color,
            iq.stock,
            iq.description,
            CASE WHEN i.image IS NOT NULL THEN 1 ELSE 0 END AS has_image
        FROM Items i
        LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
        ORDER BY i.item_id, iq.itemQuant_id
    """
    return custom_sql_select(sql)


def get_inventory_value():
    """Total inventory value = SUM(basePrice × stock) across all variants."""
    sql = """
        SELECT COALESCE(SUM(i.basePrice * iq.stock), 0)
        FROM Items i
        JOIN ItemsQuant iq ON i.item_id = iq.item_id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] else 0.0


# ---------------------------------------------------------------------------
# Dashboard Statistics
# ---------------------------------------------------------------------------

def get_pending_orders_count():
    """Count orders with status 'Processing'."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM Orders WHERE order_status = 'Processing'"
        )
        row = cursor.fetchone()
        return row[0] if row else 0


def get_low_stock_count(threshold=10):
    """
    Count distinct items whose total stock across all variants is below threshold.
    Uses a subquery to avoid the GROUP BY/HAVING-inside-COUNT structural bug.
    """
    sql = """
        SELECT COUNT(*) FROM (
            SELECT i.item_id
            FROM Items i
            LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
            GROUP BY i.item_id
            HAVING COALESCE(SUM(iq.stock), 0) < %s
        ) AS low_stock_items
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [threshold])
        row = cursor.fetchone()
        return row[0] if row else 0


def get_low_stock_items(threshold=10):
    """
    Return the actual low-stock products (not just a count).
    Useful for the Reports tab to list items needing restock.
    """
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            i.basePrice,
            COALESCE(SUM(iq.stock), 0) AS total_stock,
            CASE WHEN i.image IS NOT NULL THEN 1 ELSE 0 END AS has_image
        FROM Items i
        LEFT JOIN ItemsQuant iq ON i.item_id = iq.item_id
        GROUP BY i.item_id, i.itemName, i.basePrice, i.image
        HAVING COALESCE(SUM(iq.stock), 0) < %s
        ORDER BY total_stock ASC
    """
    return custom_sql_select(sql, [threshold])


def get_todays_sales():
    """Get total revenue for today (uses SQLite DATE('now'))."""
    sql = """
        SELECT COALESCE(SUM(totalPrice), 0)
        FROM Orders
        WHERE DATE(order_date) = DATE('now')
          AND order_status != 'Cancelled'
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] else 0.0


def get_custom_requests_count():
    """Count open/pending complaints awaiting review."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM Complaint WHERE status IN ('open', 'pending')"
        )
        row = cursor.fetchone()
        return row[0] if row else 0


# ---------------------------------------------------------------------------
# Category Management
# ---------------------------------------------------------------------------

def list_categories():
    """List all categories ordered alphabetically."""
    return custom_sql_select(
        "SELECT cat_id, categoryName FROM Category ORDER BY categoryName"
    )


def get_or_create_category(category_name):
    """Return the cat_id for category_name, creating the row if absent."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT cat_id FROM Category WHERE categoryName = %s",
            [category_name],
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute(
            "INSERT INTO Category (categoryName) VALUES (%s)",
            [category_name],
        )
        connection.commit()
        return cursor.lastrowid


def get_item_total_stock(item_id):
    """Return total stock across all variants for an item_id"""
    with connection.cursor() as cursor:
        cursor.execute("SELECT COALESCE(SUM(stock), 0) FROM ItemsQuant WHERE item_id = %s", [item_id])
        row = cursor.fetchone()
        return row[0] if row else 0

def get_product_categories(item_id):
    """Return all category/subcategory associations for a product."""
    sql = """
        SELECT c.cat_id, c.categoryName, s.subcat_id, s.subCatName
        FROM SubCategory s
        JOIN Category c ON s.cat_id = c.cat_id
        WHERE s.item_id = %s
    """
    return custom_sql_select(sql, [item_id])


def assign_product_to_category(item_id, category_name, subcategory_name=None):
    """
    Assign a product to a category.  Creates the category if it doesn't exist.
    If subcategory_name is omitted, the category name is reused as the
    subcategory label (matches existing behaviour).
    """
    cat_id      = get_or_create_category(category_name)
    subcat_name = subcategory_name or category_name

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT subcat_id FROM SubCategory WHERE cat_id = %s AND item_id = %s",
            [cat_id, item_id],
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE SubCategory SET subCatName = %s WHERE subcat_id = %s",
                [subcat_name, existing[0]],
            )
        else:
            cursor.execute(
                "INSERT INTO SubCategory (cat_id, item_id, subCatName) VALUES (%s, %s, %s)",
                [cat_id, item_id, subcat_name],
            )
        connection.commit()


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def get_sales_summary():
    """
    Top 10 best-selling products by units sold.
    Excludes Cancelled orders.
    """
    sql = """
        SELECT
            i.item_id,
            i.itemName,
            SUM(oi.quantity)            AS total_sold,
            SUM(oi.price * oi.quantity) AS total_revenue
        FROM OrderItems oi
        JOIN ItemsQuant iq ON oi.itemQuant_id = iq.itemQuant_id
        JOIN Items      i  ON iq.item_id      = i.item_id
        JOIN Orders     o  ON oi.order_id     = o.order_id
        WHERE o.order_status != 'Cancelled'
        GROUP BY i.item_id, i.itemName
        ORDER BY total_sold DESC
        LIMIT 10
    """
    return custom_sql_select(sql)


def get_revenue_by_period(period="daily", limit=30):
    """
    Revenue aggregated by day, week, or month.

    period : 'daily'   → last `limit` days grouped by date
             'weekly'  → last `limit` weeks grouped by ISO week
             'monthly' → last `limit` months grouped by year-month

    Returns a list of dicts: [{period_label, order_count, total_revenue}]
    """
    if period == "weekly":
        group_expr = "strftime('%Y-W%W', order_date)"
    elif period == "monthly":
        group_expr = "strftime('%Y-%m', order_date)"
    else:  # daily (default)
        group_expr = "DATE(order_date)"

    sql = f"""
        SELECT
            {group_expr}                     AS period_label,
            COUNT(*)                         AS order_count,
            COALESCE(SUM(totalPrice), 0)     AS total_revenue
        FROM Orders
        WHERE order_status != 'Cancelled'
        GROUP BY {group_expr}
        ORDER BY {group_expr} DESC
        LIMIT %s
    """
    return custom_sql_select(sql, [limit])


def get_category_sales():
    """
    Revenue and units sold broken down by category.
    Useful for a category-level bar chart in Reports.
    """
    sql = """
        SELECT
            c.categoryName,
            SUM(oi.quantity)            AS total_sold,
            SUM(oi.price * oi.quantity) AS total_revenue
        FROM OrderItems oi
        JOIN ItemsQuant  iq ON oi.itemQuant_id = iq.itemQuant_id
        JOIN Items       i  ON iq.item_id      = i.item_id
        JOIN SubCategory sc ON i.item_id       = sc.item_id
        JOIN Category    c  ON sc.cat_id       = c.cat_id
        JOIN Orders      o  ON oi.order_id     = o.order_id
        WHERE o.order_status != 'Cancelled'
        GROUP BY c.cat_id, c.categoryName
        ORDER BY total_revenue DESC
    """
    return custom_sql_select(sql)


# ---------------------------------------------------------------------------
# User Order History
# ---------------------------------------------------------------------------

def get_user_order_history(user_id):
    """Full order history for a single user, newest first."""
    sql = """
        SELECT order_id, order_date, order_status, totalPrice
        FROM Orders
        WHERE user_id = %s
        ORDER BY order_date DESC
    """
    return custom_sql_select(sql, [user_id])


def get_user_order_stats(user_id):
    """
    Aggregate order stats for the customer summary panel in the user modal.
    Returns a dict with total_orders, pending_orders, total_revenue.
    """
    sql = """
        SELECT
            COUNT(*)                                                      AS total_orders,
            SUM(CASE WHEN order_status = 'Processing' THEN 1 ELSE 0 END) AS pending_orders,
            COALESCE(SUM(CASE WHEN order_status != 'Cancelled'
                              THEN totalPrice ELSE 0 END), 0)             AS total_revenue
        FROM Orders
        WHERE user_id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        if row:
            return dict(zip(columns, row))
        return {"total_orders": 0, "pending_orders": 0, "total_revenue": 0.0}




def get_user_addresses(user_id):
    """
    Return all addresses for a given user_id using Address and UserAddress tables.
    """
    sql = """
        SELECT a.addr_id, a.province, a.city, a.area, a.houseNumber
        FROM Address a
        INNER JOIN UserAddress ua ON a.addr_id = ua.addr_id
        WHERE ua.user_id = %s
        ORDER BY a.addr_id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def create_address(province, city, area, house_number):
    """
    Insert a new address and return its addr_id.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Address (province, city, area, houseNumber) VALUES (%s, %s, %s, %s)",
            [province, city, area, house_number],
        )
        connection.commit()
        return cursor.lastrowid


def link_user_address(user_id, addr_id):
    """
    Link a user to an address in UserAddress table.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO UserAddress (user_id, addr_id) VALUES (%s, %s)",
            [user_id, addr_id],
        )
        connection.commit()


def delete_user_address(user_id, addr_id):
    """
    Remove a mapping from UserAddress and, for simplicity, delete the address row.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM UserAddress WHERE user_id = %s AND addr_id = %s",
            [user_id, addr_id],
        )
        cursor.execute("DELETE FROM Address WHERE addr_id = %s", [addr_id])
        connection.commit()



def get_user_orders(user_id):
    """
    Fetch basic order history for a user from the Orders table.
    Returns a list of dicts with order_id, order_date, order_status, totalPrice.
    """
    sql = """
        SELECT order_id, order_date, order_status, totalPrice
        FROM Orders
        WHERE user_id = %s
        ORDER BY order_date DESC, order_id DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    

def get_user_orders_with_items(user_id):
    """
    Fetch user orders along with their items.

    Returns:
    [
        {
            order_id,
            order_date,
            order_status,
            totalPrice,
            staff_id,
            items: [
                {
                    orderItem_id,
                    itemQuant_id,
                    quantity,
                    price
                }
            ]
        }
    ]
    """

    sql = """
        SELECT 
            o.order_id, o.order_date, o.order_status, o.totalPrice, o.staff_id,
            oi.orderItem_id, oi.itemQuant_id, oi.quantity, oi.price
        FROM Orders o
        LEFT JOIN OrderItems oi ON o.order_id = oi.order_id
        WHERE o.user_id = %s
        ORDER BY o.order_date DESC, o.order_id DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        rows = cursor.fetchall()

    orders = {}

    for row in rows:
        (
            order_id, order_date, order_status, totalPrice, staff_id,
            orderItem_id, itemQuant_id, quantity, price
        ) = row

        # Create order if not exists
        if order_id not in orders:
            orders[order_id] = {
                "order_id": order_id,
                "order_date": order_date,
                "order_status": order_status,
                "totalPrice": totalPrice,
                "staff_id": staff_id,
                "items": []
            }

        # Add item if exists
        if orderItem_id is not None:
            orders[order_id]["items"].append({
                "orderItem_id": orderItem_id,
                "itemQuant_id": itemQuant_id,
                "quantity": quantity,
                "price": price
            })

    return list(orders.values())


def create_order(user_id, order_date, order_status, totalPrice, items, staff_id = 0):
    """
    Create an order and its associated order items.

    items: list of dicts like:
        {
            "itemQuant_id": int,
            "quantity": int,
            "price": float
        }

    Returns created order_id
    """
    order_sql = """
        INSERT INTO Orders (user_id, order_date, order_status, totalPrice, staff_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING order_id
    """

    item_sql = """
        INSERT INTO OrderItems (order_id, itemQuant_id, quantity, price)
        VALUES (%s, %s, %s, %s)
    """

    try:
        with connection.cursor() as cursor:
            # Insert order
            cursor.execute(order_sql, [user_id, order_date, order_status, totalPrice, staff_id])
            order_id = cursor.fetchone()[0]

            # Insert related items
            for item in items:
                cursor.execute("SELECT itemQuant_id FROM ItemsQuant WHERE item_id = %s LIMIT 1", [item["item_id"]])
                q_row = cursor.fetchone()
                item_quant_id = q_row[0] if q_row else item["item_id"]

                cursor.execute(item_sql, [
                    order_id,
                    item_quant_id,
                    item["quantity"],
                    item["line_total"]
                ])
                
                # Decrease stock
                cursor.execute(
                    "UPDATE ItemsQuant SET stock = stock - %s WHERE itemQuant_id = %s",
                    [item["quantity"], item_quant_id]
                )

            connection.commit()
            return order_id

    except Exception:
        connection.rollback()
        raise


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

def is_item_in_wishlist(user_id, item_id):
    """
    Check if an item already exists in the user's wishlist.
    Returns True if exists, False otherwise.
    """
    sql = """
        SELECT 1
        FROM Wishlist
        WHERE user_id = %s AND itemQuant_id = %s
        LIMIT 1
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id, item_id])
        return cursor.fetchone() is not None


def get_user_wishlist(user_id):
    """
    Fetch wishlist items for a user from the Wishlist table.
    Returns a list of dicts with item_id.
    """
    sql = """
        SELECT itemQuant_id
        FROM Wishlist
        WHERE user_id = %s
        ORDER BY wishlist_id DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def put_item_to_user_wishlist(user_id, item_id):
    """
    Insert item for a user into the Wishlist table
    only if it does not already exist.
    """
    if is_item_in_wishlist(user_id, item_id):
        return {"status": "exists", "message": "Item already in wishlist"}

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Wishlist (user_id, itemQuant_id) VALUES (%s, %s)",
            [user_id, item_id],
        )
        connection.commit()

    return {"status": "added", "message": "Item added to wishlist"}

def remove_user_wishlist(user_id):
    """
    Remove all wishlist items for a given user.
    """
    sql = """
        DELETE FROM Wishlist
        WHERE user_id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        affected_rows = cursor.rowcount
        connection.commit()

    return {
        "status": "success",
        "deleted_items": affected_rows
    }


def get_first_item_quant_id(item_id):
    """
    Returns the first itemQuant_id for a given item_id.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT itemQuant_id FROM ItemsQuant WHERE item_id = %s ORDER BY itemQuant_id LIMIT 1", [item_id])
        row = cursor.fetchone()
        return row[0] if row else None


def get_user_wishlist_item_ids(user_id):
    """
    Returns a list of integer item_ids for the user's wishlist, helpful for view templates.
    """
    sql = """
        SELECT iq.item_id
        FROM Wishlist w
        JOIN ItemsQuant iq ON w.itemQuant_id = iq.itemQuant_id
        WHERE w.user_id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [user_id])
        return [row[0] for row in cursor.fetchall()]