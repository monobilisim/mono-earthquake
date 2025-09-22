#!/usr/bin/env python3
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from load_dotenv import load_dotenv
from database import EarthquakeDatabase

load_dotenv()

VALID_POLL_TYPES = ["whatsapp"]
WA_NUMBER_ID = os.getenv('WA_NUMBER_ID')
WA_API_TOKEN = os.getenv('WA_API_TOKEN')
TEMPLATE_NAME = os.getenv('TEMPLATE_NAME')
TEMPLATE_LANGUAGE = os.getenv('TEMPLATE_LANGUAGE')

def add_poll(poll_type, name, min_magnitude=1.7):
    """Add a new poll to the database."""
    if poll_type not in VALID_POLL_TYPES:
        print(f"Error: Invalid poll type '{poll_type}'")
        print(f"Valid types are: {', '.join(VALID_POLL_TYPES)}")
        sys.exit(1)

    db = EarthquakeDatabase()
    try:
        poll_id = db.create_poll(name, poll_type, min_magnitude)
        print(f"Successfully added poll '{name}' with ID {poll_id}")
    except Exception as e:
        print(f"Error adding poll: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def remove_poll(name):
    """Remove a poll from the database by name."""
    db = EarthquakeDatabase()
    try:
        poll = db.get_poll_by_name(name)
        if not poll:
            print(f"Error: No poll found with name '{name}'")
            sys.exit(1)

        if db.delete_poll(poll['id']):
            print(f"Successfully removed poll '{name}'")
        else:
            print(f"Error: Failed to remove poll '{name}'")
            sys.exit(1)
    except Exception as e:
        print(f"Error removing poll: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def list_polls():
    """List all polls in the database."""
    db = EarthquakeDatabase()
    try:
        polls = db.get_polls()

        if not polls:
            print("No polls found")
            return

        print(f"{'ID':<5} {'Name':<20} {'Type':<15} {'Min Magnitude':<15} {'Created':<20}")
        print("-" * 80)

        for poll in polls:
            created_at = poll.get('created_at', 'N/A')
            if created_at != 'N/A':
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    created_at = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            print(f"{poll['id']:<5} {poll['name']:<20} {poll['type']:<15} {poll['min_magnitude']:<15} {created_at:<20}")

    except Exception as e:
        print(f"Error listing polls: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def add_wa_user(name, phone_number, poll_name=None):
    """Add a new WhatsApp user to the database."""
    db = EarthquakeDatabase()
    try:
        user_id = db.create_wa_user(name, phone_number, poll_name)
        print(f"Successfully added WhatsApp user '{name}' with ID {user_id}")
    except Exception as e:
        print(f"Error adding WhatsApp user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def remove_wa_user(phone_number):
    """Remove a WhatsApp user from the database by phone number."""
    db = EarthquakeDatabase()
    try:
        # Note: The database class doesn't have a delete_wa_user method,
        # so we'll need to use direct SQL for this operation
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM wa_users WHERE phone_number = ?', (phone_number,))
        user = cursor.fetchone()

        if not user:
            print(f"Error: No WhatsApp user found with phone number '{phone_number}'")
            sys.exit(1)

        cursor.execute('DELETE FROM wa_users WHERE phone_number = ?', (phone_number,))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"Successfully removed WhatsApp user with phone number '{phone_number}'")
        else:
            print(f"Error: Failed to remove WhatsApp user with phone number '{phone_number}'")
            sys.exit(1)

    except Exception as e:
        print(f"Error removing WhatsApp user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def list_wa_users():
    """List all WhatsApp users in the database."""
    db = EarthquakeDatabase()
    try:
        users = db.get_wa_users()

        if not users:
            print("No WhatsApp users found")
            return

        print(f"{'ID':<5} {'Name':<20} {'Phone Number':<20} {'Poll':<20} {'Last Sent':<20} {'Created':<20}")
        print("-" * 90)

        for user in users:
            last_sent = user.get('last_sent_at', 'Never') or "Never"
            created_at = user.get('created_at') or "N/A"

            if created_at != 'N/A':
                try:
                    created_dt = datetime.fromisoformat(created_at)
                    created_at = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            print(f"{user['id']:<5} {user['name']:<20} {user['phone_number']:<20} {user['poll_name']:<20} {last_sent:<20} {created_at:<20}")

    except Exception as e:
        print(f"Error listing WhatsApp users: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def send_wa_template(poll_name, earthquake_data=None):
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

        if earthquake_data is None:
            earthquake_data = fetch_latest_earthquake(db)
            if not earthquake_data:
                print("No earthquake data available")
                sys.exit(1)

        magnitude = earthquake_data.get("magnitude", 0)
        if magnitude < poll['min_magnitude']:
            print(f"Earthquake magnitude {magnitude} is below poll threshold {poll['min_magnitude']}")
            return

        # Get all WhatsApp users
        users = db.get_wa_users(poll['name'])
        if not users:
            print("No WhatsApp users found")
            return

        success_count = 0
        for user in users:
            if send_earthquake_template_to_user(db, user, poll, earthquake_data):
                success_count += 1

        print(f"Successfully sent templates to {success_count} out of {len(users)} users")

    except Exception as e:
        print(f"Error sending WhatsApp templates: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def send_earthquake_template_to_user(db, user, poll, earthquake_data):
    """Send earthquake template to a specific user."""
    try:
        phone_number = user['phone_number']
        user_name = user['name']

        # Format earthquake data
        magnitude = earthquake_data.get('magnitude', 'N/A')
        location = earthquake_data.get('location', 'Unknown location')
        depth = earthquake_data.get('depth', 'N/A')
        timestamp = earthquake_data.get('timestamp', datetime.now().isoformat())

        # Create WhatsApp template message
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
                                "text": user_name
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

def fetch_latest_earthquake(db):
    """Fetch the latest earthquake data from the database."""
    try:
        earthquakes = db.get_latest_earthquakes(limit=1)
        if earthquakes:
            return earthquakes[0]
        return None
    except Exception as e:
        print(f"Error fetching latest earthquake data: {e}", file=sys.stderr)
        return None

def show_help():
    """Display help information about this tool."""
    print("Earthquake API Poll Management Tool")
    print("\nCommands:")
    print("  help                                    - Show this help message")
    print("  add-poll <type> <name> [min_magnitude] - Add a new poll")
    print("  remove-poll <name>                     - Remove a poll by name")
    print("  list-polls                             - List all polls")
    print("  add-wa-user <name> <phone_number> <poll_name>     - Add a WhatsApp user")
    print("  remove-wa-user <phone_number>          - Remove a WhatsApp user")
    print("  list-wa-users                          - List all WhatsApp users")
    print("  send-template <poll_name>              - Send WhatsApp template for a poll")
    print("\nValid poll types:")
    for t in VALID_POLL_TYPES:
        print(f"  - {t}")
    print("\nExamples:")
    print("  python manage-polls.py add-poll whatsapp company1 2.5")
    print("  python manage-polls.py add-wa-user \"John Doe\" 905554444 company1")
    print("  python manage-polls.py send-template company1")

def main():
    """Parse arguments and dispatch to appropriate function."""
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        show_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "add-poll":
        if len(sys.argv) == 4:
            poll_type = sys.argv[2]
            name = sys.argv[3]
            add_poll(poll_type, name)
        elif len(sys.argv) == 5:
            poll_type = sys.argv[2]
            name = sys.argv[3]
            min_magnitude = float(sys.argv[4])
            add_poll(poll_type, name, min_magnitude)
        else:
            print("Error: Invalid arguments for add-poll")
            show_help()
            sys.exit(1)

    elif command == "remove-poll" and len(sys.argv) == 3:
        name = sys.argv[2]
        remove_poll(name)

    elif command == "list-polls" and len(sys.argv) == 2:
        list_polls()

    elif command == "add-wa-user" and len(sys.argv) == 4 or len(sys.argv) == 5:
        name = sys.argv[2]
        phone_number = sys.argv[3]
        poll_name = None
        if sys.argv[4] is not None:
            poll_name = sys.argv[4]

        add_wa_user(name, phone_number, poll_name)

    elif command == "remove-wa-user" and len(sys.argv) == 3:
        phone_number = sys.argv[2]
        remove_wa_user(phone_number)

    elif command == "list-wa-users" and len(sys.argv) == 2:
        list_wa_users()

    elif command == "send-template" and len(sys.argv) == 3:
        poll_name = sys.argv[2]
        send_wa_template(poll_name)

    else:
        print("Error: Invalid command or arguments")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
