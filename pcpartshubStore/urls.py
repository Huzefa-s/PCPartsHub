from django.urls import path
from . import views
from django.http import HttpResponse

from django.urls import path, include



urlpatterns = [
    path('admin', include('pcpartshubAdmin.urls')),

    path("", views.index, name="index"),

    path("about/<str:complain>/", views.about, name="about"),
    path("about/", views.about, name="about"),

    # ---------- Auth ----------
    # Login: GET → show page, POST → login_submit handles form
    path("login/", views.login, name="login"),
    path("login/submit/", views.login_submit, name="login_submit"),

    # Register: GET → show page, POST → register_submit handles form
    path("register/", views.register, name="register"),
    path("register/submit/", views.register_submit, name="register_submit"),

    path("logout/", views.logout_view, name="logout"),
    path("register/address/", views.register_address, name="register_address"),
    path("track/", views.track_order, name="track_order"),

    # ---------- My Account ----------
    path("myaccount/", views.myaccount, name="myaccount"),
    path("myaccount/addresses/", views.manage_addresses, name="manage_addresses"),
    path("myaccount/payment/", views.manage_payment_method, name="manage_payment_method"),
    path("update_profile/", views.update_profile, name="update_profile"),
    path("complaint/submit/", views.submit_complaint, name="submit_complaint"),

    # ---------- Utility ----------
    path("under-construction/", views.under_construction, name="under_construction"),

   
    path("shop/<int:current_page>/<str:category>/<str:subcategory>/", views.shop, name="shop"),
    path("shop/<int:current_page>/<str:category>/", views.shop, name="shop"),
    path("shop/<int:current_page>/", views.shop, name="shop"),
    path("shop/", views.shop, name="shop"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),

    
    path("product/<int:product_id>/", views.product_detail, name="product_detail"),
    path("checkout/", views.checkout, name="checkout"),

    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist, name="add_to_wishlist"),

    # =====================================================================
    # TO DO IN FUTURE
    # =====================================================================

#     path("shop/<int:current_page>/<str:category>/<str:subcategory>/",
#          lambda request, current_page, category, subcategory:
#          HttpResponse(f"<h1>shop</h1><p>page={current_page}, category={category}, subcategory={subcategory}</p>"),
#          name="shop"),

#     path("shop/<int:current_page>/<str:category>/",
#          lambda request, current_page, category:
#          HttpResponse(f"<h1>shop</h1><p>page={current_page}, category={category}</p>"),
#          name="shop"),

#     path("shop/<int:current_page>/",
#          lambda request, current_page:
#          HttpResponse(f"<h1>shop</h1><p>page={current_page}</p>"),
#          name="shop"),

#     path("shop/",
#          lambda request: HttpResponse("<h1>shop</h1>"),
#          name="shop"),

#     path("cart/",
#          lambda request: HttpResponse("<h1>cart</h1>"),
#          name="cart"),

#     path("cart/add/<int:product_id>/",
#          lambda request, product_id:
#          HttpResponse(f"<h1>add_to_cart</h1><p>product_id={product_id}</p>"),
#          name="add_to_cart"),

#     path("product/<int:product_id>/",
#          lambda request, product_id:
#          HttpResponse(f"<h1>product_detail</h1><p>product_id={product_id}</p>"),
#          name="product_detail"),

    # path("wishlist/",
    #      lambda request: HttpResponse("<h1>wishlist</h1>"),
    #      name="wishlist"),

    # path("wishlist/add/<int:product_id>/",
    #      lambda request, product_id:
    #      HttpResponse(f"<h1>add_to_wishlist</h1><p>product_id={product_id}</p>"),
    #      name="add_to_wishlist"),

#     path("checkout/",
#          lambda request: HttpResponse("<h1>checkout</h1>"),
#          name="checkout"),
]
