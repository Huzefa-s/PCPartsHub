from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from functools import wraps
from django.db import connection

from database import data as admin_data


# ─── Auth decorator ──────────────────────────────────────────────────────────

def admin_staff_required(view_func):
    """Ensure the user is logged in and has admin or staff role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("login_status", False):
            return redirect("admin_login")
        role = request.session.get("role", "").lower()
        if role == "customer":
            return redirect("/")
        if role in ["admin", "staff"]:
            return view_func(request, *args, **kwargs)
        return redirect("admin_login")
    return wrapper


# ─── Login / Logout ──────────────────────────────────────────────────────────

@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """
    Staff / admin login page.

    Accepts either email address or a plain username string as the
    identifier field.  Tries email lookup first; falls back to
    matching against the `name` column so employee IDs or usernames
    stored in `name` also work.

    On GET: renders the login form, pre-filling the identifier if
    'remember_me' was set on a previous session.

    On POST: validates credentials, sets session keys, and redirects
    to the dashboard.  Customers are rejected.
    """
    # Already logged in → go straight to dashboard
    if request.session.get("login_status") and request.session.get("role") in ("admin", "staff"):
        return redirect("admin_dashboard")

    # Pre-fill identifier from cookie if Remember Me was used before
    remembered_identifier = request.COOKIES.get("admin_remember_identifier", "")

    if request.method == "GET":
        return render(request, "admin_login.html", {
            "identifier_value": remembered_identifier,
            "remember_checked":  bool(remembered_identifier),
        })

    # ── POST ──
    identifier  = request.POST.get("identifier", "").strip()
    password    = request.POST.get("password", "").strip()
    remember_me = bool(request.POST.get("remember_me"))

    if not identifier or not password:
        messages.error(request, "Please enter your username/ID and password.")
        return render(request, "admin_login.html", {
            "identifier_value": identifier,
            "remember_checked":  remember_me,
        })

    # Try email first, then name/username column
    user = admin_data.login_sql_select(identifier, password)       # email + password
    if not user:
        user = admin_data.login_by_username(identifier, password)  # name + password

    if not user:
        messages.error(request, "Invalid credentials. Please try again.")
        return render(request, "admin_login.html", {
            "identifier_value": identifier,
            "remember_checked":  remember_me,
        })

    role = (user.get("role") or "").lower()
    if role not in ("admin", "staff"):
        messages.error(request, "Access denied. This portal is for staff and admins only.")
        return render(request, "admin_login.html", {
            "identifier_value": identifier,
            "remember_checked":  remember_me,
        })

    # ── Set session ──
    request.session["login_status"] = True
    request.session["user_id"]      = user["user_id"]
    request.session["username"]     = user["name"]
    request.session["role"]         = role

    if remember_me:
        # Keep session for 30 days
        request.session.set_expiry(60 * 60 * 24 * 30)
    else:
        request.session.set_expiry(0)   # expires when browser closes

    response = redirect("admin_dashboard")

    # Persist identifier in a cookie for the Remember Me pre-fill
    if remember_me:
        response.set_cookie(
            "admin_remember_identifier",
            identifier,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="Lax",
        )
    else:
        response.delete_cookie("admin_remember_identifier")

    return response


def admin_logout_view(request):
    """Clear session and redirect to login."""
    request.session.flush()
    response = redirect("admin_login")
    response.delete_cookie("admin_remember_identifier")
    return response


# ─── Dashboard ───────────────────────────────────────────────────────────────

@admin_staff_required
def dashboard(request):
    """
    Admin / staff dashboard.  Serves the unified admin_ui.html template.

    Images are NOT embedded as base64 in the page.  The template
    references {% url 'admin_product_image' p.item_id %} directly, so the
    browser fetches each image on demand via get_product_image_view().
    We only need a boolean has_image flag per product.
    """
    user_role = request.session.get("role", "").lower()
    user_id   = request.session.get("user_id")

    products_raw = admin_data.list_products()

    # Strip raw BLOB bytes; add has_image boolean flag for the template.
    products = []
    for p in products_raw:
        products.append({
            **{k: v for k, v in p.items() if k != "image"},
            "has_image": bool(p.get("image")),
        })

    context = {
        "inventory":       admin_data.get_inventory_snapshot(),
        "orders":          admin_data.get_all_orders(),
        "products":        products,
        "users":           admin_data.list_users(),
        "categories":      admin_data.list_categories(),
        "pending_count":   admin_data.get_pending_orders_count(),
        "low_stock_count": admin_data.get_low_stock_count(threshold=10),
        "custom_count":    admin_data.get_custom_requests_count(),
        "todays_sales":    admin_data.get_todays_sales(),
        "sales_summary":   admin_data.get_sales_summary(),
        "inventory_value": admin_data.get_inventory_value(),
        "complaints":      admin_data.get_complaints(),
        "user_role":       user_role,
        "user_id":         user_id,
        "username":        request.session.get("username", ""),
    }
    return render(request, "admin_ui.html", context)


    return render(request, "admin_ui.html", context)


# ─── Reports ─────────────────────────────────────────────────────────────────
import csv

@admin_staff_required
def admin_export_sales(request):
    """Export monthly sales report as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="monthly_sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Date', 'Customer ID', 'Total Price', 'Status', 'Payment Method'])

    orders = admin_data.get_all_orders()
    for order in orders:
        writer.writerow([
            order.get('order_id'),
            order.get('order_date'),
            order.get('user_id'),
            order.get('totalPrice'),
            order.get('order_status'),
            order.get('paymentMethod')
        ])

    return response

# ─── Orders ──────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_update_order_status(request):
    """Update order status from the Orders tab."""
    order_id = request.POST.get("order_id")
    status   = request.POST.get("status")
    staff_id = request.session.get("user_id")

    if order_id and status:
        admin_data.update_order_status(order_id, status)
        if staff_id:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE Orders SET staff_id = %s WHERE order_id = %s",
                    [staff_id, order_id],
                )

    messages.success(request, f"Order #{order_id} updated to {status}.")
    return redirect("admin_dashboard")


@admin_staff_required
def admin_order_invoice(request, order_id):
    """Printable invoice view for a single order."""
    details = admin_data.get_order_details(order_id)
    if not details:
        return redirect("admin_dashboard")

    return render(request, "order_invoice.html", {
        "order": details[0],
        "items":  details,
    })


    return render(request, "order_invoice.html", {
        "order": details[0],
        "items":  details,
    })


# ─── Complaints ──────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_update_complaint(request):
    """Update complaint status (e.g. mark as resolved)."""
    complaint_id = request.POST.get("complaint_id")
    status = request.POST.get("status")
    if complaint_id and status:
        admin_data.update_complaint_status(complaint_id, status)
        messages.success(request, f"Complaint #{complaint_id} marked as {status}.")
    return redirect("admin_dashboard")


# ─── Products ────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_save_product(request):
    """
    Create or update a product.

    The form uses enctype="multipart/form-data" so the image file arrives
    in request.FILES.  Raw bytes are written to the BLOB column via
    admin_data.save_product().  Passing image=None means "keep existing".
    """
    if request.session.get("role", "").lower() not in ("admin", "staff"):
        return redirect("admin_dashboard")

    item_id = request.POST.get("item_id") or None
    if item_id:
        try:
            item_id = int(item_id)
        except ValueError:
            item_id = None

    name       = request.POST.get("name",       "").strip()
    short_desc = request.POST.get("short_desc", "").strip()
    full_desc  = request.POST.get("full_desc",  "").strip()
    category   = request.POST.get("category",   "").strip()

    try:
        price_val = float(request.POST.get("price") or 0)
    except ValueError:
        price_val = 0.0

    try:
        stock_val = int(request.POST.get("stock") or 0)
    except ValueError:
        stock_val = 0

    image_file  = request.FILES.get("image")
    image_bytes = image_file.read() if image_file else None

    if image_bytes and len(image_bytes) > 5 * 1024 * 1024:
        messages.error(request, "Image must be under 5 MB.")
        return redirect("admin_dashboard")

    saved_id = admin_data.save_product(
        item_id    = item_id,
        name       = name,
        price      = price_val,
        stock      = stock_val,
        short_desc = short_desc,
        full_desc  = full_desc,
        image      = image_bytes,
    )

    if category and saved_id:
        admin_data.assign_product_to_category(saved_id, category)

    messages.success(request, f'Product "{name}" saved successfully.')
    return redirect("admin_dashboard")


@admin_staff_required
@require_POST
def admin_delete_product(request, item_id):
    """Delete a product and all its dependent rows."""
    if request.session.get("role", "").lower() not in ("admin", "staff"):
        return redirect("admin_dashboard")

    admin_data.delete_product(item_id)
    messages.success(request, "Product deleted.")
    return redirect("admin_dashboard")


@admin_staff_required
def get_product_image_view(request, item_id):
    """
    Stream a product's BLOB image as an HTTP response.
    Returns a 1×1 transparent PNG when no image exists so <img> tags never break.
    """
    image_blob = admin_data.get_product_image(item_id)

    if not image_blob:
        BLANK_PNG = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return HttpResponse(BLANK_PNG, content_type="image/png")

    if image_blob[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = "image/png"
    elif image_blob[:3] == b'\xff\xd8\xff':
        content_type = "image/jpeg"
    elif image_blob[:6] in (b'GIF87a', b'GIF89a'):
        content_type = "image/gif"
    elif image_blob[:4] == b'RIFF' and image_blob[8:12] == b'WEBP':
        content_type = "image/webp"
    else:
        content_type = "image/jpeg"

    response = HttpResponse(image_blob, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


# ─── Users ───────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_save_user(request):
    """
    Update an existing user's profile fields from the Users edit modal.
    Role changes are only applied when the caller is an admin.
    """
    caller_role = request.session.get("role", "").lower()
    user_id     = request.POST.get("user_id")
    name        = request.POST.get("name",  "").strip()
    email       = request.POST.get("email", "").strip()
    phone       = request.POST.get("phone") or None
    notes       = request.POST.get("notes") or None
    role        = request.POST.get("role")  or "customer"

    if not user_id:
        return redirect("admin_dashboard")

    try:
        user_id_int = int(user_id)
    except ValueError:
        return redirect("admin_dashboard")

    if caller_role == "admin":
        admin_data.update_user(
            user_id = user_id_int,
            name    = name,
            email   = email,
            role    = role,
            phone   = phone,
            notes   = notes,
        )
    else:
        admin_data.update_profile_sql(
            user_id = user_id_int,
            name    = name,
            email   = email,
            phone   = phone,
        )

    messages.success(request, "User profile updated.")
    return redirect("admin_dashboard")


@admin_staff_required
@require_POST
def admin_add_user(request):
    """
    Create a brand-new user account from the Add User modal.
    Admin only.

    Validates:
    - Email uniqueness
    - Password confirmation match (belt-and-suspenders; JS also checks)
    - Role is one of customer / staff / admin
    """
    if request.session.get("role", "").lower() != "admin":
        messages.error(request, "Only admins can create users.")
        return redirect("admin_dashboard")

    name             = request.POST.get("name",             "").strip()
    email            = request.POST.get("email",            "").strip()
    password         = request.POST.get("password",         "").strip()
    password_confirm = request.POST.get("password_confirm", "").strip()
    phone            = request.POST.get("phone")   or None
    notes            = request.POST.get("notes")   or None
    role             = request.POST.get("role",    "customer").strip().lower()

    # ── Validation ──
    if not name or not email or not password:
        messages.error(request, "Name, email, and password are required.")
        return redirect("admin_dashboard")

    if password != password_confirm:
        messages.error(request, "Passwords do not match.")
        return redirect("admin_dashboard")

    if len(password) < 8:
        messages.error(request, "Password must be at least 8 characters.")
        return redirect("admin_dashboard")

    if role not in ("customer", "staff", "admin"):
        role = "customer"

    # Check for duplicate email
    if admin_data.get_user_by_email(email):
        messages.error(request, f'A user with the email "{email}" already exists.')
        return redirect("admin_dashboard")

    # ── Create ──
    new_id = admin_data.register_sql_insert(name, email, password, role=role)

    # Persist optional fields that register_sql_insert doesn't handle
    if (phone or notes) and new_id:
        admin_data.update_profile_sql(
            user_id = new_id,
            phone   = phone,
        )
        if notes:
            # update_user handles notes
            admin_data.update_user(
                user_id = new_id,
                name    = name,
                email   = email,
                role    = role,
                phone   = phone,
                notes   = notes,
            )

    messages.success(request, f'User "{name}" ({role}) created successfully.')
    return redirect("admin_dashboard")


@admin_staff_required
@require_POST
def admin_delete_user(request, user_id):
    """Delete a user and their non-order data. Admin only."""
    if request.session.get("role", "").lower() != "admin":
        messages.error(request, "Only admins can delete users.")
        return redirect("admin_dashboard")

    admin_data.delete_user(user_id)
    messages.success(request, "User deleted.")
    return redirect("admin_dashboard")


@admin_staff_required
def get_user_details(request, user_id):
    """AJAX endpoint — returns user details + order history as JSON."""
    user = admin_data.get_user_by_id(user_id)
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({
        "user":          user,
        "order_history": admin_data.get_user_order_history(user_id),
        "order_stats":   admin_data.get_user_order_stats(user_id),
    })
