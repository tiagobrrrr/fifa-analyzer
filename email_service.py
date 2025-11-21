import smtplib
from email.mime.text import MIMEText

class EmailService:
    def __init__(self):
        self.sender_email = "tiagoandrade070310@gmail.com"
        self.sender_password = "uqgchmrxvptytwan"

    def send_email(self, recipient_email, subject, message):
        try:
            msg = MIMEText(message)
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = recipient_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())

            print("Email enviado com sucesso!")

        except Exception as e:
            print(f"Erro ao enviar email: {e}")
