from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from functools import wraps
from django.db import connection

from .database import data as admin_data


# ─── Auth decorator ──────────────────────────────────────────────────────────

def admin_staff_required(view_func):
    """Ensure the user is logged in and has admin or staff role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("login_status", False):
            return redirect("/login/")
        role = request.session.get("role", "").lower()
        if role == "customer":
            return redirect("/")
        if role in ["admin", "staff"]:
            return view_func(request, *args, **kwargs)
        return redirect("/login/")
    return wrapper


# ─── Dashboard ───────────────────────────────────────────────────────────────

@admin_staff_required
def dashboard(request):
    """
    Admin / staff dashboard.  Serves the unified admin_ui.html template.

    Images are NO LONGER embedded as base64 in the page.  The template
    references {% url 'admin_product_image' p.item_id %} directly, so the
    browser fetches each image on demand via get_product_image_view().
    We only need a boolean has_image flag per product.
    """
    user_role = request.session.get("role", "").lower()
    user_id   = request.session.get("user_id")

    products_raw = admin_data.list_products()

    # Annotate products: drop raw BLOB bytes, add has_image flag.
    # This keeps the dashboard context lean and avoids massive HTML pages.
    products = []
    for p in products_raw:
        products.append({
            **{k: v for k, v in p.items() if k != "image"},   # strip BLOB
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
        "user_role":       user_role,
        "user_id":         user_id,
        "username":        request.session.get("username", ""),
    }

    return render(request, "admin_ui.html", context)


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
                    "UPDATE Orders SET staff_id = ? WHERE order_id = ?",
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


# ─── Products ────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_save_product(request):
    """
    Create or update a product.  Only admins may call this.

    The form is submitted as multipart/form-data so that an image file
    can be uploaded.  The raw bytes are written directly to the BLOB
    column in the item table via admin_data.save_product().
    """
    if request.session.get("role", "").lower() != "admin":
        return redirect("admin_dashboard")

    # ── scalar fields ──
    item_id    = request.POST.get("item_id") or None
    if item_id:
        try:
            item_id = int(item_id)
        except ValueError:
            item_id = None

    name       = request.POST.get("name", "").strip()
    short_desc = request.POST.get("short_desc", "").strip()
    full_desc  = request.POST.get("full_desc", "").strip()
    category   = request.POST.get("category", "").strip()

    try:
        price_val = float(request.POST.get("price") or 0)
    except ValueError:
        price_val = 0.0

    try:
        stock_val = int(request.POST.get("stock") or 0)
    except ValueError:
        stock_val = 0

    # ── image file → bytes (None means "keep existing" when editing) ──
    image_file  = request.FILES.get("image")        # InMemoryUploadedFile or None
    image_bytes = image_file.read() if image_file else None

    # Validate file size (5 MB limit)
    if image_bytes and len(image_bytes) > 5 * 1024 * 1024:
        messages.error(request, "Image must be under 5 MB.")
        return redirect("admin_dashboard")

    # ── persist ──
    saved_id = admin_data.save_product(
        item_id    = item_id,
        name       = name,
        price      = price_val,
        stock      = stock_val,
        short_desc = short_desc,
        full_desc  = full_desc,
        image      = image_bytes,   # bytes or None  (None = don't overwrite)
    )

    if category and saved_id:
        admin_data.assign_product_to_category(saved_id, category)

    messages.success(request, f'Product "{name}" saved successfully.')
    return redirect("admin_dashboard")


@admin_staff_required
@require_POST
def admin_delete_product(request, item_id):
    """Delete a product.  Admin only."""
    if request.session.get("role", "").lower() != "admin":
        return redirect("admin_dashboard")

    admin_data.delete_product(item_id)
    messages.success(request, "Product deleted.")
    return redirect("admin_dashboard")


@admin_staff_required
def get_product_image_view(request, item_id):
    """
    Stream a product's BLOB image as an HTTP response.

    Called by every <img src="{% url 'admin_product_image' p.item_id %}">
    in the template.  Returns a 1×1 transparent PNG when no image exists
    so that <img> tags never break.
    """
    image_blob = admin_data.get_product_image(item_id)

    if not image_blob:
        # 1×1 transparent PNG — keeps img tags intact without a 404
        BLANK_PNG = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return HttpResponse(BLANK_PNG, content_type="image/png")

    # Detect content-type from magic bytes
    if image_blob[:8] == b'\x89PNG\r\n\x1a\n':
        content_type = "image/png"
    elif image_blob[:3] == b'\xff\xd8\xff':
        content_type = "image/jpeg"
    elif image_blob[:6] in (b'GIF87a', b'GIF89a'):
        content_type = "image/gif"
    elif image_blob[:4] == b'RIFF' and image_blob[8:12] == b'WEBP':
        content_type = "image/webp"
    else:
        content_type = "image/jpeg"     # safe default

    response = HttpResponse(image_blob, content_type=content_type)
    response["Cache-Control"] = "private, max-age=3600"
    return response


# ─── Users ───────────────────────────────────────────────────────────────────

@admin_staff_required
@require_POST
def admin_save_user(request):
    """
    Update user profile fields from the Users modal.
    Role changes are only applied when the caller is an admin.
    """
    caller_role = request.session.get("role", "").lower()
    user_id     = request.POST.get("user_id")
    name        = request.POST.get("name", "").strip()
    email       = request.POST.get("email", "").strip()
    phone       = request.POST.get("phone") or None
    role        = request.POST.get("role") or "customer"

    if not user_id:
        return redirect("admin_dashboard")

    try:
        user_id_int = int(user_id)
    except ValueError:
        return redirect("admin_dashboard")

    if caller_role == "admin":
        # Admin path: update everything including role
        admin_data.update_user(
            user_id = user_id_int,
            name    = name,
            email   = email,
            role    = role,
            phone   = phone,
        )
    else:
        # Staff path: update profile fields only, leave role untouched
        admin_data.update_profile_sql(
            user_id = user_id_int,
            name    = name,
            email   = email,
            phone   = phone,
        )

    messages.success(request, f"User profile updated.")
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
