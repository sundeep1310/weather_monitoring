import pytest
from unittest.mock import Mock, patch
from src.alerts import AlertSystem
from src.config import settings

def test_temperature_alert_threshold():
    alert_system = AlertSystem()
    
    # Test below threshold
    assert not alert_system.check_temperature_alert("Delhi", settings.ALERT_TEMPERATURE_THRESHOLD - 1)
    
    # Test at threshold
    assert not alert_system.check_temperature_alert("Delhi", settings.ALERT_TEMPERATURE_THRESHOLD)
    
    # Test above threshold but not consecutive
    assert not alert_system.check_temperature_alert("Delhi", settings.ALERT_TEMPERATURE_THRESHOLD + 1)
    
    # Test consecutive alerts
    assert alert_system.check_temperature_alert("Delhi", settings.ALERT_TEMPERATURE_THRESHOLD + 1)

@patch('smtplib.SMTP')
def test_send_alert(mock_smtp):
    alert_system = AlertSystem()
    mock_server = Mock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    alert_system.send_alert("Delhi", 36.5)
    
    assert mock_server.starttls.called
    assert mock_server.login.called
    assert mock_server.send_message.called