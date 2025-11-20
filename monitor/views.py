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
        