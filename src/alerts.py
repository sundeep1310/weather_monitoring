import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.config import settings

class AlertSystem:
    def __init__(self):
        self.temperature_threshold = settings.ALERT_TEMPERATURE_THRESHOLD
        self.consecutive_required = settings.CONSECUTIVE_ALERTS_REQUIRED
        self.alert_counts = {}  # City -> count of consecutive alerts

    def check_temperature_alert(self, city: str, temperature: float) -> bool:
        if temperature > self.temperature_threshold:
            self.alert_counts[city] = self.alert_counts.get(city, 0) + 1
            if self.alert_counts[city] >= self.consecutive_required:
                self.send_alert(city, temperature)
                return True
        else:
            self.alert_counts[city] = 0
        return False

    def send_alert(self, city: str, temperature: float):
        msg = MIMEMultipart()
        msg['Subject'] = f'Weather Alert: High Temperature in {city}'
        msg['From'] = settings.SMTP_USERNAME
        msg['To'] = settings.SMTP_USERNAME  # Send to self for testing
        
        body = f"""
        High Temperature Alert!
        City: {city}
        Current Temperature: {temperature}°C
        Threshold: {self.temperature_threshold}°C
        """
        
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            print(f"Failed to send alert email: {str(e)}")