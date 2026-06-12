from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('api/classify/', views.api_classify, name='api_classify'),
    path('api/reload-model/', views.api_reload_model, name='api_reload_model'),
]