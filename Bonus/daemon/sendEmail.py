import smtplib
from email.message import EmailMessage

class EmailAlerter:
    def __init__(self, smtp_server, smtp_port, username, password, recipients):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients
    
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