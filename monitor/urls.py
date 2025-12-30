# app/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path("incoming-sms/", IncomingSmsAPIView.as_view(), name="incoming-sms"),
    path('messages/', IncomingMessageListAPIView.as_view(), name='incoming-message-list'),
    path('sim-endpoints/', SimEndpointListCreateAPIView.as_view(), name='sim-endpoint-list-create'),
    path('dashboard/sms-traffic/', SmsTrafficAPIView.as_view(), name='sms-traffic-24h'),
    path('deliveries/', DeliveryAttemptListAPIView.as_view(), name='delivery-list'),
    path('add-forward-rule/', AddForwardRuleView.as_view(), name='add-forward-rule'),
    path('delete-forward-rule/<uuid:pk>/', DeleteForwardRuleView.as_view(), name='delete-forward-rule'),
    path('get-forward-rule-list/', GetForwardRuleListView.as_view(), name='get-forward-rule-list'),
    path('add-destination-Channel/', AddDestinationChannelView.as_view(), name='add-destination-Channel'),
    path('get-destination-Channel-list/', GetDestinationChannelListView.as_view(), name='get-destination-Channel-list'),
    path('delete-destination-Channel/<uuid:pk>/', DisableDestinationChannelView.as_view(), name='delete-destination-Channel'),
    path('add-management-destination-Channel/', AddManagementDestinationChannelView.as_view(), name='add-management-destination-Channel'),
]
