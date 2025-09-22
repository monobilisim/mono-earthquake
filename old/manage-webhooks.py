#!/usr/bin/env python3
import sys
from datetime import datetime
from pathlib import Path
from database import EarthquakeDatabase
from webhooks import discord, zulip, whatsapp, generic

# Define valid webhook types
VALID_WEBHOOK_TYPES = [
    # "whatsapp", # i did not test it, counted as not implemented
    "zulip",
    "discord",
    "generic" # just sends the json object looks like {count: n, data: [{}, {}]}
]

def add_webhook(webhook_type, url, name):
    """Add a new webhook to the database."""
    if webhook_type not in VALID_WEBHOOK_TYPES:
        print(f"Error: Invalid webhook type '{webhook_type}'")
        print(f"Valid types are: {', '.join(VALID_WEBHOOK_TYPES)}")
        sys.exit(1)

    db = EarthquakeDatabase()
    try:
        webhook_id = db.register_webhook(name, url, webhook_type)
        print(f"Successfully added webhook '{name}' with ID {webhook_id}")
    except Exception as e:
        print(f"Error adding webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def remove_webhook(name):
    """Remove a webhook from the database by name."""
    db = EarthquakeDatabase()
    try:
        # First find the webhook by name
        webhooks = db.get_webhooks()
        webhook_to_delete = None
        for webhook in webhooks:
            if webhook['name'] == name:
                webhook_to_delete = webhook
                break

        if not webhook_to_delete:
            print(f"Error: No webhook found with name '{name}'")
            sys.exit(1)

        if db.delete_webhook(webhook_to_delete['id']):
            print(f"Successfully removed webhook '{name}'")
        else:
            print(f"Error: Failed to remove webhook '{name}'")
            sys.exit(1)
    except Exception as e:
        print(f"Error removing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def list_webhooks(webhook_type=None):
    """List webhooks, optionally filtered by type."""
    db = EarthquakeDatabase()
    try:
        if webhook_type and webhook_type not in VALID_WEBHOOK_TYPES:
            print(f"Error: Invalid webhook type '{webhook_type}'")
            print(f"Valid types are: {', '.join(VALID_WEBHOOK_TYPES)}")
            sys.exit(1)

        webhooks = db.get_webhooks()

        if webhook_type:
            webhooks = [w for w in webhooks if w.get('type') == webhook_type]

        if not webhooks:
            message = f"No webhooks found of type '{webhook_type}'" if webhook_type else "No webhooks found"
            print(message)
            return

        if webhook_type:
            print(f"{'ID':<5} {'Name':<20} {'Last Sent':<30} {'URL':<50}")
            print("-" * 100)

            for webhook in webhooks:
                last_sent = webhook.get('last_sent_at', 'Never') or "Never"
                if last_sent and last_sent != 'Never':
                    try:
                        last_sent_dt = datetime.fromisoformat(last_sent)
                        last_sent = last_sent_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                print(f"{webhook['id']:<5} {webhook['name']:<20} {last_sent:<30} {webhook['url']:<50}")
        else:
            print(f"{'ID':<5} {'Name':<20} {'Type':<10} {'Last Sent':<30} {'URL':<50}")
            print("-" * 110)

            for webhook in webhooks:
                last_sent = webhook.get('last_sent_at', 'Never') or "Never"
                if last_sent and last_sent != 'Never':
                    try:
                        last_sent_dt = datetime.fromisoformat(last_sent)
                        last_sent = last_sent_dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                print(f"{webhook['id']:<5} {webhook['name']:<20} {webhook['type']:<10} {last_sent:<30} {webhook['url']:<50}")

    except Exception as e:
        print(f"Error listing webhooks: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def fetch_latest_earthquake():
    """Fetch the latest earthquake data from the database."""
    db = EarthquakeDatabase()
    try:
        earthquakes = db.get_latest_earthquakes(limit=1)
        if earthquakes:
            return earthquakes[0]
        else:
            print("No earthquake data found in the database.")
            return None
    except Exception as e:
        print(f"Error fetching latest earthquake data: {e}", file=sys.stderr)
        return None
    finally:
        db.close()

def test_webhook(name):
    """Test a webhook by sending a test message."""
    db = EarthquakeDatabase()
    try:
        # Find webhook by name
        webhooks = db.get_webhooks()
        webhook = None
        for w in webhooks:
            if w['name'] == name:
                webhook = w
                break

        if not webhook:
            print(f"Error: No webhook found with name '{name}'")
            sys.exit(1)

        webhook_type = webhook['type']
        webhook_url = webhook['url']

        print(f"Testing webhook '{name}' of type '{webhook_type}'...")

        success = False
        if webhook_type == 'discord':
            # Create a simple test message for Discord
            test_payload = {
                "content": "🔔 **Test Notification from Earthquake API**",
                "embeds": [
                    {
                        "title": "This is a test message",
                        "description": "Your webhook is configured correctly!",
                        "color": 3066993,  # Green color
                        "footer": {
                            "text": f"Sent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    }
                ]
            }
            success = discord(webhook_url, None)  # Pass None to trigger test message
        elif webhook_type == 'zulip':
            success = zulip(webhook_url, None)  # Pass None to trigger test message
        elif webhook_type == 'whatsapp':
            success = whatsapp(webhook_url, None)  # Pass None to trigger test message
        elif webhook_type == 'generic':
            # For generic webhook, we pass a simple test JSON payload
            test_payload = {
                "message": "Test notification from Earthquake API",
                "timestamp": datetime.now().isoformat(),
                "status": "test"
            }
            success = generic(webhook_url, test_payload)
        else:
            print(f"Testing for webhook type '{webhook_type}' is not implemented yet")
            sys.exit(1)

        if success:
            # Update last_sent_at timestamp
            db.update_webhook_last_sent(webhook['id'])
            print("Webhook test successful! Updated last sent timestamp.")
        else:
            print("Test webhook failed. Please check URL and network connection.")

    except Exception as e:
        print(f"Error testing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def send_latest_earthquake(name=None):
    """Send the latest earthquake data to a webhook or all webhooks if name is None."""
    latest_earthquake = fetch_latest_earthquake()
    if not latest_earthquake:
        print("No earthquake data available to send.")
        sys.exit(1)

    # Format the data as the API would return it
    earthquake_data = {
        "count": 1,
        "data": [latest_earthquake]
    }

    db = EarthquakeDatabase()
    try:
        if name:
            # Send to a specific webhook
            webhooks = db.get_webhooks()
            webhook = None
            for w in webhooks:
                if w['name'] == name:
                    webhook = w
                    break

            if not webhook:
                print(f"Error: No webhook found with name '{name}'")
                sys.exit(1)

            process_webhook_send(webhook, earthquake_data, db)
        else:
            # Send to all webhooks
            webhooks = db.get_webhooks()

            if not webhooks:
                print("No webhooks found.")
                sys.exit(1)

            for webhook in webhooks:
                process_webhook_send(webhook, earthquake_data, db)

    except Exception as e:
        print(f"Error sending earthquake data to webhook(s): {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def process_webhook_send(webhook, earthquake_data, db):
    """Process sending earthquake data to a single webhook."""
    webhook_type = webhook['type']
    webhook_url = webhook['url']
    webhook_name = webhook['name']

    print(f"Sending latest earthquake data to '{webhook_name}' ({webhook_type})...")

    success = False
    if webhook_type == 'discord':
        success = discord(webhook_url, earthquake_data)
    elif webhook_type == 'zulip':
        success = zulip(webhook_url, earthquake_data)
    elif webhook_type == 'whatsapp':
        success = whatsapp(webhook_url, earthquake_data)
    elif webhook_type == 'generic':
        success = generic(webhook_url, earthquake_data)
    else:
        print(f"Sending for webhook type '{webhook_type}' is not implemented yet")
        return

    if success:
        # Update last_sent_at timestamp
        db.update_webhook_last_sent(webhook['id'])
        print(f"Successfully sent latest earthquake data to '{webhook_name}'")
    else:
        print(f"Failed to send earthquake data to '{webhook_name}'")

def show_help():
    """Display help information about this tool."""
    print("Earthquake API Webhook Management Tool")
    print("\nCommands:")
    print("  help                                      - Show this help message")
    print("  add <type> <url> <name>                   - Add a new webhook")
    print("  remove <name>                             - Remove a webhook by name")
    print("  list                                      - List all webhooks")
    print("  list <type>                               - List webhooks of a specific type")
    print("  test <name>                               - Test a webhook by sending a test message")
    print("  send <name>                               - Send latest earthquake data to a specific webhook")
    print("  send                                      - Send latest earthquake data to all webhooks")
    print("  remove-last-earthquake                    - Remove the last earthquake from the database")
    print("  create-user <name> <password> <poll_name> - Create a new user with optional poll name")
    print("\nValid webhook types:")
    for t in VALID_WEBHOOK_TYPES:
        print(f"  - {t}")
    print("\nExamples:")
    print("  python manage-webhooks.py add discord https://discord.com/api/webhooks/... my-discord")
    print("  python manage-webhooks.py test my-discord")
    print("  python manage-webhooks.py send my-discord")

def main():
    """Parse arguments and dispatch to appropriate function."""
    if len(sys.argv) < 2 or sys.argv[1] == "help":
        show_help()
        sys.exit(0)

    command = sys.argv[1]

    if command == "add" and len(sys.argv) == 5:
        webhook_type = sys.argv[2]
        url = sys.argv[3]
        name = sys.argv[4]
        add_webhook(webhook_type, url, name)

    elif command == "remove" and len(sys.argv) == 3:
        name = sys.argv[2]
        remove_webhook(name)

    elif command == "list":
        if len(sys.argv) == 3:
            webhook_type = sys.argv[2]
            list_webhooks(webhook_type)
        elif len(sys.argv) == 2:
            list_webhooks()
        else:
            show_help()

    elif command == "test" and len(sys.argv) == 3:
        name = sys.argv[2]
        test_webhook(name)

    elif command == "send":
        if len(sys.argv) == 3:
            name = sys.argv[2]
            send_latest_earthquake(name)
        elif len(sys.argv) == 2:
            send_latest_earthquake()
        else:
            show_help()

    elif command == "remove-last-earthquake":
        db = None

        try:
            db = EarthquakeDatabase()

            db.delete_last_earthquake()
        except Exception as e:
            print(f"Error removing last earthquake: {e}", file=sys.stderr)
            sys.exit(1)

        finally:
            if db:
                db.close()

    elif command == "create-user":
        if len(sys.argv) < 3:
            print("Error: create-user command requires a name and password and poll name (optional)")
            sys.exit(1)

        db = None
        try:
            db = EarthquakeDatabase()
            name = sys.argv[2]
            password = sys.argv[3]
            poll_name = None
            if len(sys.argv) > 4:
                poll_name = sys.argv[4]

            db.create_user(name, password, poll_name)
            print(f"User '{name}' with password '{password}' created successfully.")
        except Exception as e:
            print(f"Error creating user: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            if db:
                db.close()

    else:
        print("Error: Invalid command or arguments")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
