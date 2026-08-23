from django.urls import path
from . import views
app_name = "control"
urlpatterns = [
    path("approvals/", views.approval_center, name="approvals"),
    path("audit/", views.audit_log, name="audit"),
    path("notifications/", views.notifications, name="notifications"),
]
