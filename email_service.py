import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        self.sender_email = "tiagoh736@gmail.com"
        self.app_password = "whmc jkdn csev mpjm"

    def send_email(self, to_email, subject, message):
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(message, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender_email, self.app_password)
            server.send_message(msg)
            server.quit()

            print("Email enviado com sucesso!")
            return True

        except Exception as e:
            print("Erro ao enviar email:", e)
            return False
