# Backend Setup Notes

The FastAPI service reads configuration from `.env`. In addition to `DATABASE_URL` and JWT settings, email notifications rely on the following optional variables:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `EMAIL_SENDER`: standard SMTP configuration used to send invitation and alert emails.
- `NOTIFICATION_APP_BASE_URL`: base URL for the mobile/web client used to build CTA links inside the emails (for example `https://app.athletics.com`).

When these values are not provided the API will log a warning and skip the email delivery, but the endpoints will still respond successfully so the mobile clients can behave consistently.

## backend README
