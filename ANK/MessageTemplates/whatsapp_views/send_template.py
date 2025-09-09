import logging
from typing import Dict, Any

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated

from MessageTemplates.context_builder import build_registration_context
from Events.models.event_registration_model import EventRegistration
from MessageTemplates.models import MessageTemplate
from MessageTemplates.models import QueuedMessage
from MessageTemplates.utils import render_template_with_vars
from MessageTemplates.services.whatsapp import (
    send_freeform_text,
    send_resume_opener,
    within_24h_window,
)

logger = logging.getLogger(__name__)


class SendTemplateInput(serializers.Serializer):
    # Path includes event_id and registration_id; we still validate body for template + variables
    template_id = serializers.UUIDField()
    variables = serializers.DictField(child=serializers.JSONField(), required=False)


class SendLocalTemplateView(APIView):
    """
    POST /api/events/<event_id>/registrations/<registration_id>/send-template/
    Body: { "template_id": "<uuid>", "variables": { ... } }

    Behavior:
      - Renders the local message (from MessageTemplate + variables).
      - If inside 24h window -> send free-form WhatsApp text immediately.
      - If outside -> queue the rendered message and send an approved 'resume' template with a quick-reply button.
      - Returns JSON indicating 'sent' or 'queued'.
    """

    # permission_classes = [IsAuthenticated]

    def post(self, request, event_id: str, registration_id: str):
        serializer = SendTemplateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        template_id = serializer.validated_data["template_id"]
        variables: Dict[str, Any] = serializer.validated_data.get("variables", {}) or {}

        # Fetch objects
        reg = get_object_or_404(
            EventRegistration.objects.select_related("guest", "event"),
            id=registration_id,
            event_id=event_id,
        )
        tmpl = get_object_or_404(
            MessageTemplate.objects.prefetch_related("variables"), id=template_id
        )

        ctx = build_registration_context(reg)
        try:
            text = render_template_with_vars(tmpl, ctx)
        except Exception as e:
            logger.exception("Template render failed")
            return Response(
                {"ok": False, "error": f"render_failed: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine recipient (digits only E.164 without '+')
        to_wa = getattr(reg.guest, "phone", None)
        if not to_wa:
            return Response(
                {"ok": False, "error": "guest_has_no_phone"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Simple window check: use responded_on as last inbound anchor for now
        in_window = within_24h_window(reg.responded_on)

        if in_window:
            # Send immediately (free-form)
            try:
                msg_id = send_freeform_text(to_wa, text)
                return Response(
                    {"ok": True, "status": "sent", "message_id": msg_id},
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                logger.exception("Free-form send failed")
                return Response(
                    {"ok": False, "error": f"send_failed: {e}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        # Outside 24h: queue + send opener
        try:
            QueuedMessage.objects.create(
                event=reg.event,
                registration=reg,
                template=tmpl,
                rendered_text=text,
            )
        except Exception as e:
            logger.exception("Queue insert failed")
            return Response(
                {"ok": False, "error": f"queue_failed: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            opener_param = (
                variables.get("guest_name") or getattr(reg.guest, "name", "") or "Guest"
            )
            opener_id = send_resume_opener(to_wa, str(reg.id))
            return Response(
                {"ok": True, "status": "queued", "opener_message_id": opener_id},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Opener template send failed")
            return Response(
                {"ok": False, "error": f"opener_failed: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
