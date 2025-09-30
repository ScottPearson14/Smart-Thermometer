import requests
from requests.auth import HTTPBasicAuth

# Twilio account credentials
ACCOUNT_SID = "AC9b8a0e9eae4e3bc14a539ff7bd46b7c9"
AUTH_TOKEN = "e2b5931e050d222126cbe0fc7d98e87e"

# Twilio API endpoints
BASE_URL = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}"
MESSAGES_URL = f"{BASE_URL}/Messages.json"

# Phone numbers
FROM_NUMBER = "+18556127806"   # Your Twilio trial number
TO_NUMBER = "+18777804236"     # Virtual Phone number


def send_message(body: str):
    """
    Sends an SMS message using Twilio.
    """
    payload = {
        "To": TO_NUMBER,
        "From": FROM_NUMBER,
        "Body": body
    }

    response = requests.post(
        MESSAGES_URL,
        data=payload,
        auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
    )

    if response.status_code == 201:
        data = response.json()
        print("✅ Message accepted by Twilio!")
        print(f"SID: {data['sid']}, Status: {data['status']}, Body: {data['body']}")
    else:
        print(f"❌ Failed to send. Status {response.status_code}")
        print(response.text)


def fetch_messages(limit: int = 5):
    """
    Fetches the most recent messages from Twilio and prints them.
    """
    response = requests.get(
        MESSAGES_URL,
        params={"PageSize": limit},
        auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
    )

    if response.status_code == 200:
        messages = response.json().get("messages", [])
        print(f"\n📩 Last {len(messages)} messages:")
        for msg in messages:
            print(f"- To: {msg['to']}, From: {msg['from']}, "
                  f"Status: {msg['status']}, Body: {msg['body']}")
    else:
        print(f"❌ Failed to fetch messages. Status {response.status_code}")
        print(response.text)


def main():
    """
    Lets the user type a custom message in the terminal and sends it.
    """
    print("=== Twilio Virtual Phone Messenger ===")
    body = input("Type the message you want to send: ").strip()
    if body:
        send_message(body)
        fetch_messages(limit=5)
    else:
        print("⚠️ No message entered. Nothing sent.")


if __name__ == "__main__":
    main()
