# email_service.py
import os
import smtplib
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("EMAIL_ADDRESS", "tiagoh736@gmail.com")
SMTP_PASS = os.getenv("whmc jkdn csev mpjm")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)

def send_report(to_address, file_path, subject="FIFA Analyzer Report", body_html=None):
    if not SMTP_USER or not SMTP_PASS:
        print("❌ ERRO: Credenciais SMTP não configuradas. Verifique seu arquivo .env.")
        return False
    if body_html is None:
        body_html = "<p>Attached daily report.</p>"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    if file_path:
        if not os.path.exists(file_path):
            print(f"⚠️ Arquivo não encontrado: {file_path}")
        else:
            ctype, encoding = mimetypes.guess_type(file_path)
            if ctype is None or encoding is not None:
                ctype = "application/octet-stream"
            maintype, subtype = ctype.split('/', 1)
            with open(file_path, 'rb') as f:
                part = MIMEBase(maintype, subtype)
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file_path))
                msg.attach(part)
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"✅ Email enviado para {to_address}")
        return True
    except Exception as e:
        print(f"❌ Falha ao enviar email: {e}")
        return False
