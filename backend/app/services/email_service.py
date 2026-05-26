from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings


async def send_verification_email(recipient: str, token: str) -> None:
    verification_url = f"{settings.app_base_url}/api/auth/verify?token={token}"
    message = EmailMessage()
    message["From"] = settings.smtp_sender
    message["To"] = recipient
    message["Subject"] = "Confirme seu cadastro"
    message.set_content(
        "Olá!\n\n"
        "Para confirmar seu cadastro, acesse o link abaixo:\n"
        f"{verification_url}\n\n"
        "Se você não solicitou este cadastro, ignore este email."
    )

    await aiosmtplib.send(message, hostname=settings.smtp_host, port=settings.smtp_port)
