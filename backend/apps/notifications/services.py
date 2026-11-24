from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.audit.services import log_event

from .models import Notification, NotificationTemplate


class NotificationError(ValueError):
    pass


def _ensure_scope(actor, notification: Notification) -> None:
    if actor is None or getattr(actor, "is_superuser", False):
        return
    if notification.institution_id != getattr(actor, "institution_id", None):
        raise NotificationError("institution_scope_violation")
    actor_campus_id = getattr(actor, "campus_id", None)
    if notification.campus_id is not None and actor_campus_id not in (None, notification.campus_id):
        raise NotificationError("campus_scope_violation")


def send_notification(*, actor=None, notification: Notification) -> Notification:
    _ensure_scope(actor, notification)
    try:
        if notification.channel == NotificationTemplate.Channel.EMAIL:
            recipient = notification.recipient_email
            if not recipient:
                raise NotificationError("recipient_email_required")
            send_mail(
                notification.subject or "Notification",
                notification.body,
                getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com"),
                [recipient],
                fail_silently=False,
            )
            notification.provider = notification.provider or "email"
        elif notification.channel == NotificationTemplate.Channel.SMS:
            if not notification.recipient_phone:
                raise NotificationError("recipient_phone_required")
            notification.provider = notification.provider or "sms"
        elif notification.channel == NotificationTemplate.Channel.IN_APP:
            notification.provider = notification.provider or "in_app"
        else:
            raise NotificationError("unsupported_channel")
        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.error_message = ""
    except Exception as exc:
        notification.status = Notification.Status.FAILED
        notification.error_message = str(exc)
    notification.save()
    log_event(
        "notification.sent"
        if notification.status == Notification.Status.SENT
        else "notification.failed",
        actor=actor,
        target_type="notifications.Notification",
        target_id=notification.pk,
        institution_id=notification.institution_id,
        campus_id=notification.campus_id,
        metadata={
            "channel": notification.channel,
            "status": notification.status,
            "template": notification.template_code,
        },
    )
    return notification


def create_notification(*, actor=None, send=True, **kwargs) -> Notification:
    notification = Notification.objects.create(**kwargs)
    if send:
        return send_notification(actor=actor, notification=notification)
    return notification
