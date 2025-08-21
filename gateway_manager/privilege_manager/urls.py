from . import views
from django.urls import path
urlpatterns = [
    path("list_tools/", view = views.list_tools),
    path("check_tool_privilege/", view = views.check_tool_privilege),
]