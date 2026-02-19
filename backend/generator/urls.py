from django.urls import path
from .views import generate_document

urlpatterns = [
    path("generate/", generate_document),
]
