import logging
import smtplib
from email.message import EmailMessage

from ..core.config import get_settings
from ..models.user import CoachInvite

logger = logging.getLogger(__name__)


def send_invite_email(invite: CoachInvite) -> None:
    subject = "Nueva invitación de entrenador"
    cta = _build_cta_url("/register")
    body = (
        f"Hola!\n\n{invite.coach.name} te invitó a entrenar en la plataforma Athletics.\n"
        f"Ingresa con tu cuenta o regístrate usando este correo para aceptar la invitación.\n\n"
    )
    if cta:
        body += f"Comienza aquí: {cta}\n\n"
    _send_email(recipient=invite.athlete_email, subject=subject, body=body)


def send_invite_reminder(invite: CoachInvite) -> None:
    subject = "Recordatorio: tienes una invitación pendiente"
    cta = _build_cta_url("/login")
    body = (
        f"Hola! {invite.coach.name} está esperando que confirmes tu invitación en Athletics.\n"
        f"Ingresa para aceptarla y sincronizar tus planes.\n"
    )
    if cta:
        body += f"Accede aquí: {cta}\n"
    _send_email(recipient=invite.athlete_email, subject=subject, body=body)


def send_invite_accepted(invite: CoachInvite) -> None:
    if not invite.coach or not invite.coach.email:
        return
    subject = "Un atleta aceptó tu invitación"
    athlete_name = invite.athlete.name if invite.athlete else invite.athlete_email
    body = (
        f"{athlete_name} aceptó tu invitación en Athletics.\n"
        f"Ya puedes asignarle planes y comenzar a registrar su progreso."
    )
    _send_email(recipient=invite.coach.email, subject=subject, body=body)


def _build_cta_url(path: str) -> str | None:
    settings = get_settings()
    if not settings.notification_app_base_url:
        return None
    return f"{settings.notification_app_base_url.rstrip('/')}{path}"


def _send_email(recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.email_sender:
        logger.warning("SMTP not configured, skipping email to %s", recipient)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_sender
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - network failures
        logger.error("Failed to send email to %s: %s", recipient, exc)
