-- Enable FK support
PRAGMA foreign_keys = ON;

-- =========================
-- DJANGO SESSION TABLE
-- =========================
CREATE TABLE django_session (
    session_key TEXT PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date DATETIME NOT NULL
);

-- =========================
-- USERS
-- =========================
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    role TEXT DEFAULT 'customer',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- CATEGORY
-- =========================
CREATE TABLE Category (
    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoryName TEXT NOT NULL
);

-- =========================
-- ITEMS
-- =========================
CREATE TABLE Items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    itemName TEXT NOT NULL,
    basePrice REAL NOT NULL,
    short_desc TEXT,
    full_desc TEXT,
    image BLOB
);

-- =========================
-- SUBCATEGORY
-- =========================
CREATE TABLE SubCategory (
    subcat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_id INTEGER,
    item_id INTEGER,
    subCatName TEXT,
    FOREIGN KEY (cat_id) REFERENCES Category(cat_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES Items(item_id) ON DELETE CASCADE
);

-- =========================
-- ITEM VARIANTS
-- =========================
CREATE TABLE ItemsQuant (
    itemQuant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    color TEXT,
    stock INTEGER DEFAULT 0,
    description TEXT,
    FOREIGN KEY (item_id) REFERENCES Items(item_id) ON DELETE CASCADE
);

-- =========================
-- ORDERS
-- =========================
CREATE TABLE Orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    order_status TEXT,
    totalPrice REAL,
    staff_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- =========================
-- ORDER ITEMS
-- =========================
CREATE TABLE OrderItems (
    orderItem_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    itemQuant_id INTEGER,
    quantity INTEGER,
    price REAL,
    FOREIGN KEY (order_id) REFERENCES Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (itemQuant_id) REFERENCES ItemsQuant(itemQuant_id) ON DELETE CASCADE
);

-- =========================
-- CART
-- =========================
CREATE TABLE Cart (
    cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    itemQuant_id INTEGER,
    quantity INTEGER,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (itemQuant_id) REFERENCES ItemsQuant(itemQuant_id) ON DELETE CASCADE
);

-- =========================
-- WISHLIST
-- =========================
CREATE TABLE Wishlist (
    wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    itemQuant_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (itemQuant_id) REFERENCES ItemsQuant(itemQuant_id) ON DELETE CASCADE
);

-- =========================
-- COMPLAINT
-- =========================
CREATE TABLE Complaint (
    complaint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT,
    status TEXT DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- =========================
-- ADDRESS
-- =========================
CREATE TABLE Address (
    addr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    province TEXT,
    city TEXT,
    area TEXT,
    houseNumber TEXT
);

-- =========================
-- USER ADDRESS LINK
-- =========================
CREATE TABLE UserAddress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    addr_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (addr_id) REFERENCES Address(addr_id) ON DELETE CASCADE
);

-- =========================
-- INSERT ADMIN USER
-- =========================
INSERT INTO Users (
    user_id,
    name,
    email,
    phone,
    password,
    role,
    created_at
)
VALUES (
    1,
    'hello',
    'hello@hello.com',
    '03330000000',
    'hello',
    'admin',
    DATE('now')
);