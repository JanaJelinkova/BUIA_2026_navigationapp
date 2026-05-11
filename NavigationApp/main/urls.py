from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('api/route/', views.api_route, name='api_route'),
]