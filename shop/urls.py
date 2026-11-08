from django.urls import path

from shop import views

app_name = 'shop'

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
]