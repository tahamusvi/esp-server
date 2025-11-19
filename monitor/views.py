# app/views.py
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SimEndpoint, IncomingMessage
from .serializers import IncomingSmsPayloadSerializer, IncomingMessageSerializer
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
                "deliveries_created": deliveries_created,
            },
            status=status.HTTP_201_CREATED,
        )
