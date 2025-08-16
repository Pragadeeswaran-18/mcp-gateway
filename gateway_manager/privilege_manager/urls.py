from . import views
from django.urls import path
urlpatterns = [
    path("list_tools", view = views.list_tools)
]