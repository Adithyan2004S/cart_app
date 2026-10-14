from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),

    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('account/', views.account, name='account'),

    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:id>/', views.remove_from_cart, name='remove_from_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('order/success/<int:id>/', views.order_success, name='order_success'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:id>/', views.order_detail, name='order_detail'),
]
