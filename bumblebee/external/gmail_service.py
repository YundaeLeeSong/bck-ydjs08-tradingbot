import os
import smtplib
import ssl
import mimetypes
from pathlib import Path
from email.message import EmailMessage
from typing import List, Optional, Tuple
from alphavi_util.core import get_env_var

class GmailService:
    """
    Service for sending emails via SMTP (Gmail).
    Designed as a Singleton to configure the SMTP connection parameters once.
    """
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # [Singleton] (1): Allocate instance
        if cls._instance is None:
            cls._instance = super(GmailService, cls).__new__(cls)
        return cls._instance

    def __init__(self, debug: bool = False):
        # [Singleton] (2): Initialize state
        if self.__class__._initialized:
            return
            
        self.smtp_host = get_env_var("SMTP_HOST") or "smtp.gmail.com"
        self.port = int(get_env_var("SMTP_PORT") or "465")
        self.username = get_env_var("SMTP_USERNAME")
        self.password = get_env_var("SMTP_PASSWORD")
        self.sender = get_env_var("SMTP_SENDER") or self.username
        self.security = (get_env_var("SMTP_SECURITY") or "SSL").upper()
        self.timeout = int(get_env_var("EMAIL_TIMEOUT") or "10")
        self.debug = debug
        self.__class__._initialized = True

    def send_email(self, recipients: List[str], subject: str, body_html: str, attachments: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
        if not self.username or not self.password:
            return False, "Missing SMTP_USERNAME or SMTP_PASSWORD in environment."
        if not recipients:
            return False, "No recipients provided"

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.set_content(body_html, subtype="html")

        if attachments:
            for fp in attachments:
                if not os.path.isfile(fp):
                    return False, f"Attachment not found: {fp}"
                ctype, encoding = mimetypes.guess_type(fp)
                if ctype is None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                try:
                    with open(fp, "rb") as f:
                        data = f.read()
                    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(fp))
                except Exception as e:
                    return False, f"Failed to attach {fp}: {e}"

        try:
            if self.security == "STARTTLS":
                with smtplib.SMTP(self.smtp_host, self.port, timeout=self.timeout) as server:
                    if self.debug: server.set_debuglevel(1)
                    server.ehlo()
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                    server.login(self.username, self.password)
                    server.send_message(msg)
            elif self.security == "SSL":
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.port, context=context, timeout=self.timeout) as server:
                    if self.debug: server.set_debuglevel(1)
                    server.login(self.username, self.password)
                    server.send_message(msg)
            else:
                 with smtplib.SMTP(self.smtp_host, self.port, timeout=self.timeout) as server:
                    if self.debug: server.set_debuglevel(1)
                    server.login(self.username, self.password)
                    server.send_message(msg)
            return True, None
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check username/app password."
        except Exception as e:
            return False, f"Email Error: {str(e)}"
