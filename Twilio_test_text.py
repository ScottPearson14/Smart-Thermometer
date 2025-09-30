import requests

# === Twilio Account Credentials ===
ACCOUNT_SID = "AC9b8a0e9eae4e3bc14a539ff7bd46b7c9"
AUTH_TOKEN = "3914edbaeb967838c56309427136c630"

# === Phone Numbers ===
TO_NUMBER = "+17123103373"   # Destination phone number (your virtual number)
FROM_NUMBER = "+18556127806" # Your Twilio number

# === Twilio API URL ===
BASE_URL = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"


def send_message(body: str):
    """Send an SMS message using Twilio API with hardcoded credentials."""
    payload = {
        "To": TO_NUMBER,
        "From": FROM_NUMBER,
        "Body": body,
    }
    response = requests.post(BASE_URL, data=payload, auth=(ACCOUNT_SID, AUTH_TOKEN))

    if response.status_code == 201:
        print(f"✅ Sent message: {body}")
    else:
        print(f"❌ Failed to send. Status {response.status_code}")
        print(response.text)


def fetch_messages(limit: int = 5):
    """Fetch the most recent messages from Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json?PageSize={limit}"
    response = requests.get(url, auth=(ACCOUNT_SID, AUTH_TOKEN))

    if response.status_code == 200:
        messages = response.json().get("messages", [])
        print("\n📩 Recent Messages:")
        for msg in messages:
            print(f"- From {msg['from']} to {msg['to']}: {msg['body']}")
    else:
        print(f"❌ Failed to fetch messages. Status {response.status_code}")
        print(response.text)


def main():
    print("=== Twilio Virtual Phone Messenger ===")
    user_msg = input("Type the message you want to send: ")
    send_message(user_msg)
    fetch_messages()


if __name__ == "__main__":
    main()
