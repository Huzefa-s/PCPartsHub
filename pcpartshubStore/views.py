from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
import base64
import math
import re
from datetime import datetime;

from database.data import (
    custom_sql_select,
    fetch_items,
    fetch_categories,
    get_item_by_id,
    get_items_by_ids,
    login_sql_select,
    register_user_if_new,
    update_profile_sql,
    get_user_by_id,
    get_user_addresses,
    create_address,
    link_user_address,
    delete_user_address,
    get_user_orders,
    get_user_by_email,   # ensure this exists in data.py – returns user dict or None
    create_order,
    put_item_to_user_wishlist,
    get_user_wishlist,
    remove_user_wishlist,
)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

SESSION_DEFAULTS = {
    "login_status": False,
    "user_id": 0,
    "username": "",
    "email": "",
    "phone": "",
    "role": "",
    "created_at": "",
}


def _ensure_session_defaults(request):
    for key, value in SESSION_DEFAULTS.items():
        request.session.setdefault(key, value)


def _session_user_context(request):
    _ensure_session_defaults(request)

    user_id = request.session.get("user_id")
    if request.session.get("login_status") and user_id:
        latest_user = get_user_by_id(user_id)
        if latest_user:
            _populate_session_from_user(request, latest_user)
        else:
            for key, value in SESSION_DEFAULTS.items():
                request.session[key] = value

    return {
        "is_authenticated": request.session["login_status"],
        "userID":           request.session["user_id"],
        "username":         request.session["username"],
        "email":            request.session["email"],
        "phone":            request.session["phone"],
        "role":             request.session["role"],
        "created_at":       request.session["created_at"],
    }


def _populate_session_from_user(request, user_row):
    request.session["login_status"] = True
    request.session["user_id"]      = user_row.get("user_id", 0)
    request.session["username"]     = user_row.get("name", "")
    request.session["email"]        = user_row.get("email", "")
    request.session["phone"]        = user_row.get("phone", "")
    request.session["role"]         = user_row.get("role", "")
    request.session["created_at"]   = str(user_row.get("created_at", ""))


# ---------------------------------------------------------------------------
# Password validation helper
# ---------------------------------------------------------------------------

def _validate_password(password):
    """
    Returns a list of error strings.
    Empty list means the password is valid.
    Rules: length > 8, at least 1 letter, 1 number, 1 special character.
    """
    errors = []
    if len(password) <= 8:
        errors.append("Password must be more than 8 characters.")
    if not re.search(r"[a-zA-Z]", password):
        errors.append("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if not re.search(r"[\W_]", password):
        errors.append("Password must contain at least one special character.")
    return errors


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

def index(request):
    user_ctx = _session_user_context(request)
    products = fetch_items()[:6]

    for item in products:
        if item.get("image"):
            item["image_base64"] = base64.b64encode(item["image"]).decode("utf-8")
        else:
            item["image_base64"] = None

    wishlist_ids = []
    if user_ctx.get("is_authenticated"):
        wishlist_ids = _get_wishlist(request, user_ctx["userID"])

    return render(
        request,
        "webPages/FrontEnd_ClientView/index.html",
        {"user": user_ctx, "featured_products": products, "wishlist_ids": wishlist_ids},
    )


def about(request, complain=""):
    user_ctx = _session_user_context(request)

    if complain:
        result = custom_sql_select("SELECT * FROM Complaint")
        return HttpResponse(str(result))

    return render(request, "webPages/FrontEnd_ClientView/about.html", {"user": user_ctx})

def submit_complaint(request):
    user_ctx = _session_user_context(request)
    if not user_ctx.get("is_authenticated"):
        return redirect("login")
        
    if request.method == "POST":
        description = request.POST.get("description", "").strip()
        rating = request.POST.get("rating", "5")
        
        if description:
            user_id = user_ctx["userID"]
            full_description = f"[Star Rating: {rating}/5] {description}"
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Complaint (user_id, description, status, created_at) VALUES (%s, %s, 'Pending', datetime('now'))",
                    [user_id, full_description]
                )
            messages.success(request, "Your feedback/complaint has been submitted. Thank you!")
            
    return redirect("myaccount")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login(request):
    """
    GET  → render login page
    POST → handled by login_submit
    """
    user_ctx = _session_user_context(request)
    if user_ctx["is_authenticated"]:
        return redirect("myaccount")

    return render(
        request,
        "webPages/FrontEnd_ClientView/login.html",
        {"user": user_ctx},
    )


def login_submit(request):
    """
    Handles POST from login.html.
    On success  → redirect to myaccount
    On failure  → redirect back to login with an error message
    """
    if request.method != "POST":
        return redirect("login")

    email    = request.POST.get("login_email", "").strip()
    password = request.POST.get("login_password", "").strip()

    # Basic server-side presence check
    if not email or not password:
        messages.error(request, "Email and password are required.")
        return redirect("login")

    login_data = login_sql_select(email, password)

    if login_data and isinstance(login_data, dict):
        _populate_session_from_user(request, login_data)
        messages.success(request, "Logged in successfully.")
        return redirect("myaccount")

    messages.error(request, "Incorrect email or password. Please try again.")
    return redirect("login")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def register(request):
    """
    GET  → render register page
    POST → handled by register_submit
    """
    user_ctx = _session_user_context(request)
    if user_ctx["is_authenticated"]:
        return redirect("myaccount")

    return render(
        request,
        "webPages/FrontEnd_ClientView/register.html",
        {"user": user_ctx},
    )


def register_submit(request):
    """
    Handles POST from register.html.
    Validates all fields server-side, including:
      - unique email (username)
      - password strength rules
      - password confirmation match
    """
    if request.method != "POST":
        return redirect("register")

    name             = request.POST.get("reg_name", "").strip()
    email            = request.POST.get("reg_email", "").strip()
    password         = request.POST.get("reg_password", "").strip()
    confirm_password = request.POST.get("reg_confirm_password", "").strip()
    phone            = request.POST.get("reg_phone", "").strip() or None

    # Collect all errors so we can surface them together
    errors = []

    if not name:
        errors.append("Full name is required.")

    if not email:
        errors.append("Email address is required.")
    elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        errors.append("Please enter a valid email address.")

    if not password:
        errors.append("Password is required.")
    else:
        pw_errors = _validate_password(password)
        errors.extend(pw_errors)

    if password and not errors:  # only check match if password itself is valid
        if password != confirm_password:
            errors.append("Password and confirm password do not match.")

    if phone:
        phone_digits = re.sub(r"[\s\-\+\(\)]", "", phone)
        if not re.match(r"^\d{7,15}$", phone_digits):
            errors.append("Phone number must contain 7–15 digits.")
    
    if not phone:
        errors.append("Phone number is required.")

    # Unique email / username check
    if email and not errors:
        existing = get_user_by_email(email)
        if existing:
            errors.append("An account with this email already exists.")

    if errors:
        for err in errors:
            messages.error(request, err)
        # Preserve filled-in data so the user doesn't have to retype
        request.session["_reg_form_data"] = {
            "reg_name":  name,
            "reg_email": email,
            "reg_phone": phone or "",
        }
        return redirect("register")

    # All good — create the account
    user_id = register_user_if_new(name, email, password, phone)
    if user_id is None:
        # Race condition: another request registered the same email
        messages.error(request, "An account with this email already exists.")
        return redirect("register")

    # Auto-login after registration
    login_data = login_sql_select(email, password)
    if login_data and isinstance(login_data, dict):
        _populate_session_from_user(request, login_data)
        messages.success(request, "Account created! Welcome aboard.")
        return redirect("register_address")

    messages.error(request, "Registration succeeded but auto-login failed. Please log in.")
    return redirect("login")


# ---------------------------------------------------------------------------
# My Account
# ---------------------------------------------------------------------------

def myaccount(request):
    user_ctx = _session_user_context(request)

    if not user_ctx["is_authenticated"]:
        messages.error(request, "Please log in to access your account.")
        return redirect("login")

    addresses = []
    orders    = []
    if user_ctx["userID"]:
        addresses = get_user_addresses(user_ctx["userID"])
        orders    = get_user_orders(user_ctx["userID"])

    context = {
        "user":                    user_ctx,
        "addresses":               addresses,
        "preferred_payment_method": request.session.get("preferred_payment_method", ""),
        "orders":                  orders,
    }

    return render(request, "webPages/FrontEnd_ClientView/my-account.html", context)


# ---------------------------------------------------------------------------
# Address management
# ---------------------------------------------------------------------------

def manage_addresses(request):
    _ensure_session_defaults(request)
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "You must be logged in to manage addresses.")
        return redirect("login")

    if request.method == "POST":
        if "add_address" in request.POST:
            province     = request.POST.get("province", "").strip()
            city         = request.POST.get("city", "").strip()
            area         = request.POST.get("area", "").strip()
            house_number = request.POST.get("houseNumber", "").strip()

            if province and city and area and house_number:
                addr_id = create_address(province, city, area, house_number)
                link_user_address(user_id, addr_id)
                messages.success(request, "Address added successfully.")
            else:
                messages.error(request, "All address fields are required.")

        elif "delete_address" in request.POST:
            try:
                addr_id = int(request.POST.get("delete_address"))
                delete_user_address(user_id, addr_id)
                messages.success(request, "Address deleted successfully.")
            except (TypeError, ValueError):
                messages.error(request, "Invalid address selected.")

    return redirect("myaccount")


# ---------------------------------------------------------------------------
# Payment method
# ---------------------------------------------------------------------------

def manage_payment_method(request):
    _ensure_session_defaults(request)
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "You must be logged in to manage payment methods.")
        return redirect("login")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "").strip()
        if payment_method:
            request.session["preferred_payment_method"] = payment_method
            request.session.modified = True
            messages.success(request, "Preferred payment method updated.")
        else:
            messages.error(request, "Please select a payment method.")

    return redirect("myaccount")


# ---------------------------------------------------------------------------
# Profile update
# ---------------------------------------------------------------------------

def update_profile(request):
    if request.method == "POST":
        _ensure_session_defaults(request)
        user_id = request.session.get("user_id")
        if not user_id:
            messages.error(request, "You must be logged in to update your profile.")
            return redirect("myaccount")

        name  = request.POST.get("username", "").strip() or None
        email = request.POST.get("email", "").strip()    or None
        phone = request.POST.get("phone", "").strip()    or None

        # If the user is changing email, verify it is not already taken
        if email and email != request.session.get("email"):
            existing = get_user_by_email(email)
            if existing and existing.get("user_id") != user_id:
                messages.error(request, "That email address is already in use by another account.")
                return redirect("myaccount")

        updated = update_profile_sql(user_id, name=name, email=email, phone=phone)

        if updated:
            if name:  request.session["username"] = name
            if email: request.session["email"]    = email
            if phone: request.session["phone"]    = phone
            messages.success(request, "Profile updated successfully.")
        else:
            messages.info(request, "No changes were made to your profile.")

    return redirect("myaccount")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def logout_view(request):
    request.session.flush()
    return redirect("index")


# ---------------------------------------------------------------------------
# Register Address (step shown right after sign-up)
# ---------------------------------------------------------------------------

def register_address(request):
    """
    Shown immediately after registration so the user can add their first address.
    GET  → render the address form.
    POST → validate → save address → redirect to myaccount.
    Skip link also redirects to myaccount without saving.
    """
    _ensure_session_defaults(request)
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        if "skip" in request.POST:
            return redirect("myaccount")

        province     = request.POST.get("province", "").strip()
        city         = request.POST.get("city", "").strip()
        area         = request.POST.get("area", "").strip()
        house_number = request.POST.get("houseNumber", "").strip()

        if province and city and area and house_number:
            addr_id = create_address(province, city, area, house_number)
            link_user_address(user_id, addr_id)
            messages.success(request, "Address saved successfully.")
        else:
            messages.error(request, "All address fields are required.")
            return render(request, "webPages/FrontEnd_ClientView/register-address.html",
                          {"user": _session_user_context(request)})

        return redirect("myaccount")

    return render(request, "webPages/FrontEnd_ClientView/register-address.html",
                  {"user": _session_user_context(request)})




# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

def shop(request, current_page=1, category='', subcategory=''):
    user_ctx = _session_user_context(request)
    limit_on_single_page = 12

    search_query = request.GET.get('q', '').strip()

    result = fetch_items(
        category or None,
        subcategory or None,
        search=search_query or None,
    )

    for item in result:
        if item.get("image"):
            item["image_base64"] = base64.b64encode(item["image"]).decode("utf-8")
        else:
            item["image_base64"] = None

    total_pages = max(1, math.ceil(len(result) / limit_on_single_page))
    pages = [i + 1 for i in range(total_pages)]

    current_page = max(1, min(current_page, total_pages))
    start = (current_page - 1) * limit_on_single_page
    end = current_page * limit_on_single_page
    result_selected = result[start:end]

    categories = fetch_categories()

    wishlist_ids = []
    if user_ctx.get("is_authenticated"):
        wishlist_ids = _get_wishlist(request, user_ctx["userID"])

    return render(
        request,
        "webPages/FrontEnd_ClientView/shop.html",
        {
            "products":     result_selected,
            "pages":        pages,
            "user":         user_ctx,
            "current_page": current_page,
            "category":     category,
            "subcategory":  subcategory,
            "search_query": search_query,
            "categories":   categories,
            "wishlist_ids": wishlist_ids,
        },
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def under_construction(request):
    user_ctx = _session_user_context(request)
    return render(
        request,
        "webPages/FrontEnd_ClientView/under-construction.html",
        {"user": user_ctx},
    )


# ---------------------------------------------------------------------------
# Product and Cart
# ---------------------------------------------------------------------------

def product_detail(request, product_id):
    user_ctx = _session_user_context(request)

    product = get_item_by_id(product_id)

    if not product:
        return HttpResponse("Product not found.")

    if product.get("image"):
        product["image_base64"] = base64.b64encode(product["image"]).decode("utf-8")
    else:
        product["image_base64"] = None

    return render(
        request,
        "webPages/FrontEnd_ClientView/product-details.html",
        {
            "product": product,
            "user": user_ctx,
        },
    )


def _get_cart(request):
    """
    Internal helper to read the cart from the session.
    Cart is stored as {item_id: quantity}.
    """
    raw_cart = request.session.get("cart", {})
    # normalise keys to int
    cart = {}
    for k, v in raw_cart.items():
        try:
            item_id = int(k)
            qty = int(v)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            cart[item_id] = qty
    return cart


def _save_cart(request, cart):
    # store with string keys to keep session serialisable
    request.session["cart"] = {str(k): int(v) for k, v in cart.items() if int(v) > 0}
    request.session.modified = True


def add_to_cart(request, product_id):
    """
    Add a product to the cart (or increase its quantity).
    Quantity can optionally be provided via POST or ?qty=.
    """
    cart = _get_cart(request)

    qty = 1
    if request.method == "POST":
        qty_str = request.POST.get("quantity") or request.POST.get("qty")
    else:
        qty_str = request.GET.get("qty")

    if qty_str:
        try:
            qty = max(1, int(qty_str))
        except ValueError:
            qty = 1

    cart[product_id] = cart.get(product_id, 0) + qty
    _save_cart(request, cart)

    # redirect back if a "next" parameter is provided
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("cart")


def cart_view(request):
    """
    Display and manage the shopping cart.
    """
    user_ctx = _session_user_context(request)

    cart = _get_cart(request)

    if request.method == "POST":
        # remove single item
        if "remove" in request.POST:
            try:
                item_id = int(request.POST.get("remove"))
                if item_id in cart:
                    cart.pop(item_id)
                    _save_cart(request, cart)
            except (TypeError, ValueError):
                pass
            return redirect("cart")

        # update all quantities
        if "update_cart" in request.POST:
            new_cart = {}
            for key, value in request.POST.items():
                if not key.startswith("qty_"):
                    continue
                try:
                    item_id = int(key.split("_", 1)[1])
                    qty = int(value)
                except (ValueError, IndexError):
                    continue
                if qty > 0:
                    new_cart[item_id] = qty
            cart = new_cart
            _save_cart(request, cart)
            return redirect("cart")

    item_ids = list(cart.keys())
    items = get_items_by_ids(item_ids)
    items_by_id = {item["item_id"]: item for item in items}

    cart_items = []
    subtotal = 0

    for item_id, qty in cart.items():
        item = items_by_id.get(item_id)
        if not item:
            continue

        if item.get("image"):
            item["image_base64"] = base64.b64encode(item["image"]).decode("utf-8")
        else:
            item["image_base64"] = None

        price = item.get("basePrice") or 0
        line_total = price * qty
        subtotal += line_total

        cart_items.append(
            {
                "item": item,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    context = {
        "user": user_ctx,
        "cart_items": cart_items,
        "subtotal": subtotal,
        "grand_total": subtotal,  # no shipping/tax logic yet
    }

    return render(request, "webPages/FrontEnd_ClientView/cart.html", context)


def checkout(request):
    """
    Simple checkout page based on the current cart.
    Does not persist orders but clears the cart on "place order".
    """
    user_ctx = _session_user_context(request)

    cart = _get_cart(request)
    item_ids = list(cart.keys())
    items = get_items_by_ids(item_ids)
    items_by_id = {item["item_id"]: item for item in items}

    order_lines = []
    subtotal = 0

    for item_id, qty in cart.items():
        item = items_by_id.get(item_id)
        if not item:
            continue
        price = item.get("basePrice") or 0
        line_total = price * qty
        subtotal += line_total
        order_lines.append(
            {
                "item_id": item_id,
                "item": item,
                "quantity": qty,
                "line_total": line_total,
            }
        )

    grand_total = subtotal

    if request.method == "POST" and "place_order" in request.POST:
        # In a real project you would insert into an Orders table here.
        create_order(user_ctx["userID"], datetime.now(), "Processing", grand_total, order_lines)
        _save_cart(request, {})
        messages.success(request, "Your order has been placed successfully.")
        return redirect("index")

    context = {
        "user": user_ctx,
        "order_lines": order_lines,
        "subtotal": subtotal,
        "grand_total": grand_total,
    }
    return render(request, "webPages/FrontEnd_ClientView/checkout.html", context)


def _get_wishlist(request, user_id):
    """
    Internal helper to read the wishlist from the session.
    Wishlist is stored as a list of item_ids.
    """
    raw = get_user_wishlist(user_id)
    wishlist = []
    for v in raw:
        try:
            wishlist.append(int(v["itemQuant_id"]))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(wishlist))  # deduplicate, keep order


def track_order(request):
    user_ctx = _session_user_context(request)
    order = None
    items = []
    order_id = request.GET.get("order_id") or request.POST.get("order_id")
    
    if order_id:
        try:
            from database.data import get_order_details
            details = get_order_details(int(order_id))
            if details:
                # Optionally ensure user owns the order if logged in, but tracking ID can be public if long,
                # Here we just use order_id. If we want it secure we could require user_id match for logged in users.
                order = details[0]
                items = details
        except ValueError:
            pass

    return render(request, "webPages/FrontEnd_ClientView/track.html", {
        "user": user_ctx,
        "order": order,
        "items": items,
        "searched": bool(order_id)
    })


def _save_wishlist(request, wishlist, user_id):
    remove_user_wishlist(user_id)

    for i in wishlist:
        put_item_to_user_wishlist(user_id, int(i))
        
    request.session.modified = True

    

def add_to_wishlist(request, product_id):
    user_ctx = _session_user_context(request)
    
    if not user_ctx.get("is_authenticated"):
        return redirect("login")

    user_id = user_ctx["userID"]
    
    wishlist = _get_wishlist(request, user_id)
    if product_id not in wishlist:
        wishlist.append(product_id)
    else:
        wishlist.remove(product_id)
        
    _save_wishlist(request, wishlist, user_id)

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("wishlist")


def wishlist_view(request):
    user_ctx = _session_user_context(request)
    user_id = user_ctx["userID"]

    wishlist = _get_wishlist(request, user_id)

    if request.method == "POST":
        if "remove" in request.POST:
            try:
                item_id = int(request.POST.get("remove"))
                wishlist = [i for i in wishlist if i != item_id]
                _save_wishlist(request, wishlist, user_id)
            except (TypeError, ValueError):
                pass
            return redirect("wishlist")
        
 
    items = get_items_by_ids(wishlist)
    items_by_id = {item["item_id"]: item for item in items}

    wishlist_items = []
    for item_id in wishlist:
        item = items_by_id.get(item_id)
        if not item:
            continue

        if item.get("image"):
            item["image_base64"] = base64.b64encode(item["image"]).decode("utf-8")
        else:
            item["image_base64"] = None

        wishlist_items.append(item)

    context = {
        "user": user_ctx,
        "wishlist_items": wishlist_items,
    }

    return render(request, "webPages/FrontEnd_ClientView/wishlist.html", context)
