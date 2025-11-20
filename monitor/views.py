# app/views.py
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SimEndpoint, IncomingMessage,Project
from .serializers import IncomingSmsPayloadSerializer, IncomingMessageSerializer,SimEndpointSerializer
# from .services import process_incoming_message


class IncomingSmsAPIView(APIView):
    """
    Public endpoint for devices (ESP32/SIM800) to push incoming SMS.
    Authentication is done via API token in the Authorization header:
        Authorization: Token <api_token>
    """

    authentication_classes = []  # custom token-based, not DRF auth
    permission_classes = []      # can be customized later
    serializer_class = IncomingSmsPayloadSerializer  # for Swagger / DRF tooling

    @transaction.atomic
    def post(self, request, *args, **kwargs):


        # Validate request payload with serializer
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        token = validated["token"]

        try:
            endpoint = SimEndpoint.objects.get(api_token=token, is_active=True)
        except SimEndpoint.DoesNotExist:
            return Response(
                {"detail": "Invalid or missing API token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        from_number = validated["from_number"]
        to_number = validated["to_number"]

        body = validated["body"]
        received_at = validated.get("received_at") or timezone.now()

        # Create IncomingMessage
        msg = IncomingMessage.objects.create(
            project=endpoint.project,
            endpoint=endpoint,
            from_number=from_number,
            to_number=to_number,
            body=body,
            received_at=received_at,
            raw_payload=request.data,
        )

        # Delegate business logic to service layer
        # deliveries_created = process_incoming_message(msg)

        out = IncomingMessageSerializer(msg)
        return Response(
            {
                "message": out.data,
            },
            status=status.HTTP_201_CREATED,
        )



from rest_framework import generics

class IncomingMessageListAPIView(generics.ListAPIView):
    """
    Returns a list of all incoming messages.
    Access must be restricted to authenticated users/projects.
    """
    serializer_class = IncomingMessageSerializer

    def get_queryset(self):
        """
        Filters the queryset to only include messages related to the authenticated user's project.
        (This part assumes a standard DRF authentication mechanism is in place,
         e.g., a custom authentication class sets request.user to an object with a 'project' attribute.)
        """
        return IncomingMessage.objects.all().order_by('-received_at')
        


class SimEndpointListCreateAPIView(generics.ListCreateAPIView):
    """
    Handles GET (List Endpoints) and POST (Create New Endpoint).
    """
    serializer_class = SimEndpointSerializer

    def get_queryset(self):
        """
        Filters Endpoints based on the authenticated user's project(s).
        """
        project_ids = Project.objects.all()
        return SimEndpoint.objects.filter(project_id__in=project_ids).order_by('name')
        

from django.db.models.functions import TruncHour
from django.db.models import Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta

# فرض بر این است که مدل IncomingMessage و Project در دسترس هستند

class SmsTrafficAPIView(APIView):
    """
    Calculates and returns the SMS traffic (incoming messages) 
    count for the last 24 hours, grouped by hour.
    """

    def get(self, request, *args, **kwargs):
        
        project_ids = Project.objects.all().values_list('id', flat=True)

        if not project_ids:
            return Response({"detail": "No active project found for this user."}, status=status.HTTP_404_NOT_FOUND)

        end_time = timezone.now()
        start_time = end_time - timedelta(hours=24)
        
        traffic_data = (
            IncomingMessage.objects.filter(
                project_id__in=project_ids,
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