# app/urls.py
from django.urls import path
from .views import IncomingSmsAPIView

urlpatterns = [
    path("incoming-sms/", IncomingSmsAPIView.as_view(), name="incoming-sms"),
]
