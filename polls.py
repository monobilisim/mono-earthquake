import os
import sys
import requests
from datetime import datetime
from database import EarthquakeDatabase

WA_NUMBER_ID = os.getenv('WA_NUMBER_ID')
WA_API_TOKEN = os.getenv('WA_API_TOKEN')
TEMPLATE_NAME = os.getenv('TEMPLATE_NAME')
TEMPLATE_LANGUAGE = os.getenv('TEMPLATE_LANGUAGE')

def send_wa_template(poll_name, earthquake_data):
    """Send WhatsApp template to users based on poll configuration."""

    if not WA_NUMBER_ID or not WA_API_TOKEN:
        print("Error: WA_NUMBER_ID and WA_API_TOKEN environment variables must be set")
        sys.exit(1)

    db = EarthquakeDatabase()

    try:
        poll = db.get_poll_by_name(poll_name)
        if not poll:
            print(f"Error: No poll found with name '{poll_name}'")
            sys.exit(1)

        poll_name = poll['name']

        earthquake = earthquake_data["data"][0]

        minimum_magnitude = poll['min_magnitude']
        magnitude = earthquake["magnitude"]

        if minimum_magnitude > magnitude:
            print(f"Earthquake magnitude {magnitude} is below the minimum threshold of {minimum_magnitude}. No template will be sent in {poll_name}.")
            return

        print(f"Sending template for earthquake magnitude {magnitude} (poll threshold: {poll['min_magnitude']})")

        users = db.get_wa_users()
        if not users:
            print("No WhatsApp users found")
            return

        success_count = 0
        for user in users:
            if send_earthquake_template_to_user(db, user, poll, earthquake_data):
                success_count += 1

        print(f"Successfully sent templates to {success_count} out of {len(users)} users")

    except Exception as e:
        print(f"Error sending WhatsApp flows: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if db:
            db.close()

def send_earthquake_template_to_user(db, user, poll, earthquake_data):
    """Send earthquake template to a specific user."""
    try:
        phone_number = user['phone_number']
        user_name = user['name']

        earthquake = earthquake_data["data"][0]

        magnitude = earthquake['magnitude'] if earthquake_data else 'N/A'
        location = earthquake['location'] if earthquake_data else 'Unknown location'
        depth = earthquake['depth'] if earthquake_data else 'N/A'
        timestamp = earthquake['timestamp'] if earthquake_data else datetime.now().isoformat()

        template_data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": TEMPLATE_NAME,
                "language": {
                    "code": TEMPLATE_LANGUAGE
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": user_name  # {{1}} parameter
                            }
                        ]
                    }
                ]
            }
        }

        # Send to WhatsApp API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {WA_API_TOKEN}"
        }

        url = f"https://graph.facebook.com/v18.0/{WA_NUMBER_ID}/messages"
        response = requests.post(url, json=template_data, headers=headers)

        if response.status_code == 200:

            db.update_wa_user_last_sent(phone_number)
            db.create_wa_message(phone_number, response.json()['messages'][0]['id'], poll['name'])

            print(f"Successfully sent template to {user_name} ({phone_number})")
            return True
        else:
            print(f"Failed to send template to {user_name} ({phone_number}): {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error sending template to {user['name']}: {str(e)}")
        return False
