# twiliotest.py
from twilio.rest import Client

# Use your Twilio credentials
ACCOUNT_SID = "AC9b8a0e9eae4e3bc14a539ff7bd46b7c9"
AUTH_TOKEN = "3914edbaeb967838c56309427136c630"
FROM_NUMBER = "+18556127806"   # your Twilio number
TO_NUMBER = "+18777804236"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_high_temp_alert(temp_c, temp_f):
    message_body = (
        f"You are being notified because your Smart Thermometer temperature "
        f"has exceeded 32° Celcius / 89.6°F. "
        f"Current reading: {temp_c:.1f}°C / {temp_f:.1f}°F."
    )
    _send_to_all(message_body)

def send_low_temp_alert(temp_c, temp_f):
    message_body = (
        f"You are being notified because your Smart Thermometer temperature "
        f"has gone below 18° Celcius / 64.4°F. "
        f"Current reading: {temp_c:.1f}°C / {temp_f:.1f}°F."
    )
    _send_to_all(message_body)

def _send_to_all(body):
    for number in TO_NUMBER:
        client.messages.create(
            to=number,
            from_=FROM_NUMBER,
            body=body
        )
