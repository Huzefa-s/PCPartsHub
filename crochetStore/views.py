from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
import base64
import math

from .database.data import (
    custom_sql_select,
    fetch_items,
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
)

# Create your views here.


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
    """
    Guarantee all user-related keys exist in the session.
    """
    for key, value in SESSION_DEFAULTS.items():
        request.session.setdefault(key, value)


def _session_user_context(request):
    """
    Build a per-request user context dictionary from the session.
    """
    _ensure_session_defaults(request)

    # If we have a logged-in user, refresh their data from the database
    user_id = request.session.get("user_id")
    if request.session.get("login_status") and user_id:
        latest_user = get_user_by_id(user_id)
        if latest_user:
            _populate_session_from_user(request, latest_user)
        else:
            # User no longer exists; clear login-related session data
            request.session["login_status"] = False
            request.session["user_id"] = 0
            request.session["username"] = ""
            request.session["email"] = ""
            request.session["phone"] = ""
            request.session["role"] = ""
            request.session["created_at"] = ""

    return {
        "is_authenticated": request.session["login_status"],
        "userID": request.session["user_id"],
        "username": request.session["username"],
        "email": request.session["email"],
        "phone": request.session["phone"],
        "role": request.session["role"],
        "created_at": request.session["created_at"],
    }


def _populate_session_from_user(request, user_row):
    """
    Persist database user fields into the session.
    """
    request.session["login_status"] = True
    request.session["user_id"] = user_row.get("user_id", 0)
    request.session["username"] = user_row.get("name", "")
    request.session["email"] = user_row.get("email", "")
    request.session["phone"] = user_row.get("phone", "")
    request.session["role"] = user_row.get("role", "")
    request.session["created_at"] = str(user_row.get("created_at", ""))


def index(request):
    user_ctx = _session_user_context(request)
    # Load a small set of featured products for the homepage
    products = fetch_items()[:6]

    for item in products:
        if item.get("image"):
            item["image_base64"] = base64.b64encode(item["image"]).decode("utf-8")
        else:
            item["image_base64"] = None

    return render(
        request,
        "webPages/FrontEnd_ClientView/index.html",
        {
            "user": user_ctx,
            "featured_products": products,
        },
    )





def about(request, complain = ''):
    user_ctx = _session_user_context(request)

    if complain != '':
        result = custom_sql_select(f'''
                                   
            SELECT * FROM Complaint
        
        ''')
        return HttpResponse(str(result))
    else:
        return render(request, "webPages/FrontEnd_ClientView/about.html", {
            "user": user_ctx
        })




def login(request):
    user_ctx = _session_user_context(request)
    return render(
        request,
        "webPages/FrontEnd_ClientView/login-register.html",
        {
            "user": user_ctx,
        },
    )

def myaccount(request):
    if request.method == "POST":
        if "login_submit" in request.POST:
            email = request.POST.get("login_email", "").strip()
            password = request.POST.get("login_password", "").strip()

            login_data = login_sql_select(email, password)

            if login_data and isinstance(login_data, dict):
                _populate_session_from_user(request, login_data)
                messages.success(request, "Logged in successfully.")
                return redirect("myaccount")

            messages.error(request, "Invalid email or password.")
            return redirect("login")

        elif "register_submit" in request.POST:
            name = request.POST.get("reg_name", "").strip()
            email = request.POST.get("reg_email", "").strip()
            password = request.POST.get("reg_password", "").strip()
            confirm_password = request.POST.get("reg_confirm_password", "").strip()
            phone = request.POST.get("reg_phone", "").strip()

            if password != confirm_password:
                messages.error(request, "Password and confirm password do not match.")
                return redirect("login")

            user_id = register_user_if_new(name, email, password, phone or None)
            if user_id is None:
                messages.error(request, "An account with this email already exists.")
                return redirect("login")

            login_data = login_sql_select(email, password)
            if login_data and isinstance(login_data, dict):
                _populate_session_from_user(request, login_data)
                messages.success(request, "Account created and logged in.")
                return redirect("myaccount")

            messages.error(request, "Registration failed, please try again.")
            return redirect("login")

    user_ctx = _session_user_context(request)
    addresses = []
    orders = []
    if user_ctx["is_authenticated"] and user_ctx["userID"]:
        addresses = get_user_addresses(user_ctx["userID"])
        orders = get_user_orders(user_ctx["userID"])

    context = {
        "user": user_ctx,
        "addresses": addresses,
        "preferred_payment_method": request.session.get("preferred_payment_method", ""),
        "orders": orders,
    }

    return render(request, "webPages/FrontEnd_ClientView/my-account.html", context)


def manage_addresses(request):
    """
    Handle add/remove of user addresses from the My Account page.
    Uses Address and UserAddress tables as defined in schema.txt.
    """
    _ensure_session_defaults(request)
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "You must be logged in to manage addresses.")
        return redirect("login")

    if request.method == "POST":
        if "add_address" in request.POST:
            province = request.POST.get("province", "").strip()
            city = request.POST.get("city", "").strip()
            area = request.POST.get("area", "").strip()
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


def manage_payment_method(request):
    """
    Store a user's preferred payment method in the session.
    This will later be used as a default when creating Orders.paymentMethod.
    """
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


def under_construction(request):
    """
    Simple view to render the under-construction page.
    Useful for sections defined in the schema but not yet implemented.
    """
    user_ctx = _session_user_context(request)
    return render(
        request,
        "webPages/FrontEnd_ClientView/under-construction.html",
        {"user": user_ctx},
    )


def logout_view(request):
    request.session.flush()  # clears all session data
    return redirect('index')  # redirect to home or login page

def update_profile(request):
    if request.method == "POST":
        _ensure_session_defaults(request)
        user_id = request.session.get("user_id")
        if not user_id:
            messages.error(request, "You must be logged in to update your profile.")
            return redirect("myaccount")

        name = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        updated = update_profile_sql(user_id, name=name, email=email, phone=phone)

        if updated:
            # Update session data to reflect new profile
            if name: request.session["username"] = name
            if email: request.session["email"] = email
            if phone: request.session["phone"] = phone

            messages.success(request, "Profile updated successfully.")
        else:
            messages.info(request, "No changes were made to your profile.")

        return redirect("myaccount")

    # If GET request, just redirect to account page
    return redirect("myaccount")


