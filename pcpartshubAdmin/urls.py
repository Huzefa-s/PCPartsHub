from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path("login/",  views.admin_login_view,  name="admin_login"),
    path("logout/", views.admin_logout_view, name="admin_logout"),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path("", views.dashboard, name="admin_dashboard"),

    # ── Orders ────────────────────────────────────────────────────────────────
    path(
        "orders/update-status/",
        views.admin_update_order_status,
        name="admin_update_order_status",
    ),
    path(
        "orders/<int:order_id>/invoice/",
        views.admin_order_invoice,
        name="admin_order_invoice",
    ),

    # ── Products  (image served from BLOB column) ──────────────────────────────
    path(
        "products/save/",
        views.admin_save_product,
        name="admin_save_product",
    ),
    path(
        "products/<int:item_id>/delete/",
        views.admin_delete_product,
        name="admin_delete_product",
    ),
    path(
        "products/<int:item_id>/image/",
        views.get_product_image_view,
        name="admin_product_image",
    ),

    # ── Users ─────────────────────────────────────────────────────────────────
    path(
        "users/add/",
        views.admin_add_user,
        name="admin_add_user",
    ),
    path(
        "users/save/",
        views.admin_save_user,
        name="admin_save_user",
    ),
    path(
        "users/<int:user_id>/delete/",
        views.admin_delete_user,
        name="admin_delete_user",
    ),
    path(
        "users/<int:user_id>/details/",
        views.get_user_details,
        name="admin_get_user_details",
    ),
]
