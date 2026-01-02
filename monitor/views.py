# app/views.py
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from django.db.models.functions import TruncHour
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from rest_framework import generics
from .serializers import ForwardRuleSerializer
from drf_spectacular.utils import extend_schema
from .services import process_incoming_message
from .serializers import DestinationChannelCreateSerializer
from django.shortcuts import get_object_or_404
from .serializers import RuleDestinationCreateSerializer
#--------------------------------------------------------------------
class IncomingMessageListAPIView(generics.ListAPIView):
    """
    Returns a list of all incoming messages related to the authenticated user's projects.
    """
    serializer_class = IncomingMessageSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        """
        Filters the queryset to only include messages related to the authenticated user's project IDs.
        """
        return IncomingMessage.objects.all().order_by('-received_at')

#--------------------------------------------------------------------
class SmsTrafficAPIView(APIView):
    """
    Calculates and returns the SMS traffic (incoming messages) 
    count for the last 24 hours, grouped by hour, only for the authenticated user's projects.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        end_time = timezone.now()
        start_time = end_time - timedelta(hours=24)
        
        traffic_data = (
            IncomingMessage.objects.filter(
                received_at__range=(start_time, end_time)
            )
            .annotate(hour=TruncHour('received_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )

        hourly_traffic = {}
        current_time = start_time
        while current_time <= end_time:
            hourly_traffic[current_time.strftime("%Y-%m-%dT%H:00:00")] = 0
            current_time += timedelta(hours=1)
            
        for item in traffic_data:
            time_key = item['hour'].strftime("%Y-%m-%dT%H:00:00")
            if time_key in hourly_traffic:
                hourly_traffic[time_key] = item['count']

        chart_data = [
            {"time": key, "sms_count": value}
            for key, value in sorted(hourly_traffic.items())
        ]
        
        return Response(chart_data, status=status.HTTP_200_OK)
#--------------------------------------------------------------------
class DeliveryAttemptListAPIView(generics.ListAPIView):
    """
    API endpoint to list delivery attempts (Simple Version).
    Only includes attempts related to the authenticated user's projects.
    """
    serializer_class = DeliveryAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = DeliveryAttempt.objects.all().select_related('channel', 'rule', 'message')

        return queryset
#--------------------------------------------------------------------
class AddForwardRuleView(APIView):
    @extend_schema(
        request=ForwardRuleSerializer,
        responses={201: ForwardRuleSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = ForwardRuleSerializer(data=request.data)

        if serializer.is_valid():
            rule = serializer.save()
            return Response(
                {
                    "message": "قانون جدید با موفقیت ذخیره شد",
                    "data": ForwardRuleSerializer(rule).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#--------------------------------------------------------------------
class GetForwardRuleListView(APIView):

    @extend_schema(
        responses={200: ForwardRuleSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        queryset = ForwardRule.objects.all().select_related("project")
        serializer = ForwardRuleSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
#--------------------------------------------------------------------    
class DeleteForwardRuleView(APIView):
    def delete(self, request, pk, *args, **kwargs):
        try:
            rule = ForwardRule.objects.get(pk=pk)
            rule.is_enabled = False
            rule.save()
            return Response({"message": "Rule disabled successfully"}, status=200)
        except ForwardRule.DoesNotExist:
            return Response({"error": "Rule not found"}, status=404)
#--------------------------------------------------------------------  
class AddDestinationChannelView(APIView):

    @extend_schema(
        request=DestinationChannelCreateSerializer,
        responses={201: DestinationChannelCreateSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = DestinationChannelCreateSerializer(data=request.data)

        if serializer.is_valid():
            channel = serializer.save()

            return Response(
                {
                    "message": "کانال مقصد با موفقیت ایجاد شد",
                    "data": DestinationChannelCreateSerializer(channel).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#--------------------------------------------------------------------
class GetDestinationChannelListView(APIView):

    def get(self, request, *args, **kwargs):

        channels = DestinationChannel.objects.all().order_by("-created_at")

        serializer = DestinationChannelCreateSerializer(channels, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)  
#--------------------------------------------------------------------    
class DisableDestinationChannelView(APIView):

    def delete(self, request, pk, *args, **kwargs):
        channel = get_object_or_404(DestinationChannel, pk=pk)

        if not channel.is_enabled:
            return Response(
                {"message": "کانال از قبل غیرفعال شده است"},
                status=status.HTTP_200_OK
            )

        channel.is_enabled = False
        channel.save(update_fields=["is_enabled"])

        return Response(
            {"message": "کانال مقصد با موفقیت غیرفعال شد"},
            status=status.HTTP_200_OK
        )
#--------------------------------------------------------------------
class ManagementDestinationChannelView(APIView):

    @extend_schema(
        request=RuleDestinationCreateSerializer,
        responses={201: RuleDestinationCreateSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = RuleDestinationCreateSerializer(data=request.data)

        if serializer.is_valid():
            destination = serializer.save()
            return Response(
                {
                    "message": "Destination channel successfully assigned to rule",
                    "data": {
                        "id": destination.id,
                        "rule": destination.rule.id,
                        "channel": destination.channel.id,
                        "is_enabled": destination.is_enabled,
                    },
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   
    
    def delete(self, request, destination_id, *args, **kwargs):
        destination = get_object_or_404(
            RuleDestination,
            id=destination_id,
            is_enabled=True
        )

        destination.is_enabled = False
        destination.save(update_fields=["is_enabled"])

        return Response(
            {"message": "Destination channel disabled successfully"},
            status=status.HTTP_204_NO_CONTENT
        )  
#--------------------------------------------------------------------
       