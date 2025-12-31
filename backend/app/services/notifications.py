import logging
import smtplib
from email.message import EmailMessage

from ..core.config import get_settings
from ..models.user import CoachInvite, User
from ..schemas.dashboard import AthleteAlert, CoachAlert

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
    html = _compose_html_email(
        title="Te invitaron a Athletics",
        body_lines=[
            f"<strong>{invite.coach.name}</strong> quiere que te unas a su equipo en Athletics.",
            "Acepta la invitación para sincronizar tus planes y registrar tus sesiones.",
        ],
        cta_text="Ir a la invitación",
        cta_url=_build_invite_url(invite),
    )
    _send_email(recipient=invite.athlete_email, subject=subject, body=body, html_body=html)


def send_invite_reminder(invite: CoachInvite) -> None:
    subject = "Recordatorio: tienes una invitación pendiente"
    cta = _build_cta_url("/login")
    body = (
        f"Hola! {invite.coach.name} está esperando que confirmes tu invitación en Athletics.\n"
        f"Ingresa para aceptarla y sincronizar tus planes.\n"
    )
    if cta:
        body += f"Accede aquí: {cta}\n"
    html = _compose_html_email(
        title="Tu coach sigue esperando",
        body_lines=[
            f"{invite.coach.name} aún no recibió respuesta a la invitación.",
            "Confirma para recibir tus planes y mantener tu progreso actualizado.",
        ],
        cta_text="Ver invitación",
        cta_url=_build_invite_url(invite),
    )
    _send_email(recipient=invite.athlete_email, subject=subject, body=body, html_body=html)


def send_invite_accepted(invite: CoachInvite) -> None:
    if not invite.coach or not invite.coach.email:
        return
    subject = "Un atleta aceptó tu invitación"
    athlete_name = invite.athlete.name if invite.athlete else invite.athlete_email
    body = (
        f"{athlete_name} aceptó tu invitación en Athletics.\n"
        f"Ya puedes asignarle planes y comenzar a registrar su progreso."
)
    html = _compose_html_email(
        title="¡Nuevo atleta confirmado!",
        body_lines=[
            f"{athlete_name} aceptó tu invitación.",
            "Asigna un plan o revisa su agenda para comenzar a entrenar.",
        ],
        cta_text="Abrir panel de coach",
        cta_url=_build_cta_url("/coach"),
    )
    _send_email(recipient=invite.coach.email, subject=subject, body=body, html_body=html)


def send_coach_alerts_email(coach: User, alerts: list[CoachAlert]) -> None:
    if not coach.email or not alerts:
        return
    subject = "Alertas de tus atletas"
    body = "Resumen de alertas activas:\n\n"
    for alert in alerts:
        body += f"- {alert.athlete_name}: {alert.message}\n"
    cta = _build_cta_url("/coach")
    if cta:
        body += f"\nAdministra a tus atletas aquí: {cta}\n"
    alert_list = [
        f"<strong>{alert.athlete_name}</strong>: {alert.message}" for alert in alerts
    ]
    html = _compose_html_email(
        title="Hay alertas que requieren tu atención",
        body_lines=alert_list,
        cta_text="Ver dashboard",
        cta_url=cta,
    )
    _send_email(recipient=coach.email, subject=subject, body=body, html_body=html)


def send_athlete_alerts_email(athlete: User, alerts: list[AthleteAlert]) -> None:
    if not athlete.email or not alerts:
        return
    subject = "Recordatorio de entrenamiento"
    body = f"Hola {athlete.name},\n\n"
    body += "Esto es lo que tienes pendiente:\n"
    for alert in alerts:
        body += f"- {alert.message}\n"
    cta = _build_cta_url("/athlete")
    if cta:
        body += f"\nRevisa tu agenda aquí: {cta}\n"
    html = _compose_html_email(
        title="Mantén tu streak activo",
        body_lines=[alert.message for alert in alerts],
        cta_text="Abrir agenda",
        cta_url=cta,
    )
    _send_email(recipient=athlete.email, subject=subject, body=body, html_body=html)


def _build_cta_url(path: str) -> str | None:
    settings = get_settings()
    if not settings.notification_app_base_url:
        return None
    return f"{settings.notification_app_base_url.rstrip('/')}{path}"


def _build_invite_url(invite: CoachInvite) -> str | None:
    settings = get_settings()
    base = settings.notification_app_base_url
    if not base:
        return None
    return f"{base.rstrip('/')}/invite?email={invite.athlete_email}"


def _send_email(recipient: str, subject: str, body: str, html_body: str | None = None) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.email_sender:
        logger.warning("SMTP not configured, skipping email to %s", recipient)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_sender
    message["To"] = recipient
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    logger.warning("Sending email via SMTP to %s with subject '%s'", recipient, subject)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        logger.warning("Email delivered to %s", recipient)
    except Exception as exc:  # pragma: no cover - network failures
        logger.error("Failed to send email to %s: %s", recipient, exc)


def _compose_html_email(
    title: str,
    body_lines: list[str],
    cta_text: str | None = None,
    cta_url: str | None = None,
) -> str:
    paragraphs = "".join(
        f"<p style='margin:0 0 12px;color:#1f2933;font-size:15px;line-height:1.5'>{line}</p>"
        for line in body_lines
    )
    cta_button = ""
    if cta_text and cta_url:
        cta_button = f"""
        <div style="margin-top:20px">
            <a href="{cta_url}" style="display:inline-block;padding:12px 20px;background:#2563eb;color:#ffffff;
                text-decoration:none;border-radius:999px;font-weight:600;font-size:15px">
                {cta_text}
            </a>
        </div>
        """
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <title>{title}</title>
    </head>
    <body style="margin:0;padding:24px;background-color:#0b1220;font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:18px;padding:32px;">
                        <tr>
                            <td>
                                <p style="color:#38bdf8;font-size:12px;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px;">Athletics</p>
                                <h1 style="margin:0 0 18px;color:#0f172a;font-size:24px;">{title}</h1>
                                {paragraphs}
                                {cta_button}
                                <p style="margin-top:32px;color:#94a3b8;font-size:12px;">
                                    Recibiste este mensaje porque tu usuario está registrado en Athletics.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
