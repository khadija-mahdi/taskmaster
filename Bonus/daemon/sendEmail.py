import smtplib
from email.message import EmailMessage
from email_config import get_email_config

class EmailAlerter:
    def __init__(self):
        config = get_email_config()
        self.smtp_server = config['smtp_server']
        self.smtp_port = config['smtp_port']
        self.username = config['username']
        self.password = config['password']
        self.recipients = config['recipients']
    
    def send_alert(self, subject, message, severity="INFO"):
        try:
            msg = EmailMessage()
            msg.set_content(f"[{severity}] {message}")
            msg["Subject"] = f"TASKMASTER ALERT: {subject}"
            msg["From"] = self.username
            msg["To"] = ", ".join(self.recipients)
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as smtp:
                smtp.login(self.username, self.password)
                smtp.send_message(msg)
                
        except Exception as e:
            print(f"Failed to send email alert: {e}")