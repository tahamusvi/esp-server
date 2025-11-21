# app/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path("incoming-sms/", IncomingSmsAPIView.as_view(), name="incoming-sms"),
    path('messages/', IncomingMessageListAPIView.as_view(), name='incoming-message-list'),
    path('sim-endpoints/', SimEndpointListCreateAPIView.as_view(), name='sim-endpoint-list-create'),
    path('dashboard/sms-traffic/', SmsTrafficAPIView.as_view(), name='sms-traffic-24h'),
    path('deliveries/', DeliveryAttemptListAPIView.as_view(), name='delivery-list'),
]
