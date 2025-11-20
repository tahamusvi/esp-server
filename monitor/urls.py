# app/urls.py
from django.urls import path
from .views import IncomingSmsAPIView,IncomingMessageListAPIView,SimEndpointListCreateAPIView

urlpatterns = [
    path("incoming-sms/", IncomingSmsAPIView.as_view(), name="incoming-sms"),
    path('messages/', IncomingMessageListAPIView.as_view(), name='incoming-message-list'),
    path('sim-endpoints/', SimEndpointListCreateAPIView.as_view(), name='sim-endpoint-list-create'),
]
