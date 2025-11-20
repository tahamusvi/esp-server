# app/urls.py
from django.urls import path
from .views import IncomingSmsAPIView,IncomingMessageListAPIView

urlpatterns = [
    path("incoming-sms/", IncomingSmsAPIView.as_view(), name="incoming-sms"),
    path('messages/', IncomingMessageListAPIView.as_view(), name='incoming-message-list'),
]
