#!/usr/bin/env python3
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from load_dotenv import load_dotenv
from database import EarthquakeDatabase
from webhooks import discord, zulip, whatsapp, generic
from polls import send_wa_template

load_dotenv()

# Configuration
VALID_POLL_TYPES = ["whatsapp"]
VALID_WEBHOOK_TYPES = ["zulip", "discord", "generic"]

# =============================================================================
# USER MANAGEMENT COMMANDS
# =============================================================================

def user_create(name, password, poll_name=None):
    """Create a new user with optional poll name."""
    db = EarthquakeDatabase()
    try:
        db.create_user(name, password, poll_name)
        poll_msg = f" with poll '{poll_name}'" if poll_name else ""
        print(f"Successfully created user '{name}'{poll_msg}")
    except Exception as e:
        print(f"Error creating user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def user_help():
    """Show help for user commands."""
    print("User Management Commands")
    print("\nUsage: manage.py user <command> [arguments]")
    print("\nCommands:")
    print("  create <name> <password> [poll_name]  - Create a new application user")
    print("\nExamples:")
    print("  manage.py user create john secret123 company1")

# =============================================================================
# WEBHOOK MANAGEMENT COMMANDS
# =============================================================================

def webhook_add(webhook_type, url, name):
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

def webhook_remove(name):
    """Remove a webhook from the database by name."""
    db = EarthquakeDatabase()
    try:
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

def webhook_list(webhook_type=None):
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
            print("-" * 105)
        else:
            print(f"{'ID':<5} {'Name':<20} {'Type':<10} {'Last Sent':<30} {'URL':<50}")
            print("-" * 115)

        for webhook in webhooks:
            last_sent = webhook.get('last_sent_at', 'Never') or "Never"
            if last_sent and last_sent != 'Never':
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent)
                    last_sent = last_sent_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            if webhook_type:
                print(f"{webhook['id']:<5} {webhook['name']:<20} {last_sent:<30} {webhook['url']:<50}")
            else:
                print(f"{webhook['id']:<5} {webhook['name']:<20} {webhook['type']:<10} {last_sent:<30} {webhook['url']:<50}")

    except Exception as e:
        print(f"Error listing webhooks: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def webhook_test(name):
    """Test a webhook by sending a test message."""
    db = EarthquakeDatabase()
    try:
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
            success = discord(webhook_url, None)
        elif webhook_type == 'zulip':
            success = zulip(webhook_url, None)
        elif webhook_type == 'whatsapp':
            success = whatsapp(webhook_url, None)
        elif webhook_type == 'generic':
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
            db.update_webhook_last_sent(webhook['id'])
            print("Webhook test successful! Updated last sent timestamp.")
        else:
            print("Test webhook failed. Please check URL and network connection.")

    except Exception as e:
        print(f"Error testing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def webhook_send(name=None):
    """Send the latest earthquake data to a webhook or all webhooks if name is None."""
    db = EarthquakeDatabase()
    try:
        earthquakes = db.get_latest_earthquakes(limit=1)
        if not earthquakes:
            print("No earthquake data available to send.")
            sys.exit(1)

        earthquake_data = {
            "count": 1,
            "data": earthquakes
        }

        if name:
            webhooks = db.get_webhooks()
            webhook = None
            for w in webhooks:
                if w['name'] == name:
                    webhook = w
                    break

            if not webhook:
                print(f"Error: No webhook found with name '{name}'")
                sys.exit(1)

            _process_webhook_send(webhook, earthquake_data, db)
        else:
            webhooks = db.get_webhooks()
            if not webhooks:
                print("No webhooks found.")
                sys.exit(1)

            for webhook in webhooks:
                _process_webhook_send(webhook, earthquake_data, db)

    except Exception as e:
        print(f"Error sending earthquake data to webhook(s): {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def _process_webhook_send(webhook, earthquake_data, db):
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
        db.update_webhook_last_sent(webhook['id'])
        print(f"Successfully sent latest earthquake data to '{webhook_name}'")
    else:
        print(f"Failed to send earthquake data to '{webhook_name}'")

def webhook_help():
    """Show help for webhook commands."""
    print("Webhook Management Commands")
    print("\nUsage: manage.py webhook <command> [arguments]")
    print("\nCommands:")
    print("  add <type> <url> <name>     - Add a new webhook")
    print("  remove <name>               - Remove a webhook by name")
    print("  list [type]                 - List all webhooks or filter by type")
    print("  test <name>                 - Test a webhook by sending a test message")
    print("  send [name]                 - Send latest earthquake data to webhook(s)")
    print(f"\nValid webhook types: {', '.join(VALID_WEBHOOK_TYPES)}")
    print("\nExamples:")
    print("  manage.py webhook add discord https://discord.com/api/webhooks/... my-discord")
    print("  manage.py webhook list discord")
    print("  manage.py webhook test my-discord")
    print("  manage.py webhook send my-discord")
    print("  manage.py webhook send")

# =============================================================================
# POLL MANAGEMENT COMMANDS
# =============================================================================

def poll_add(poll_type, name, min_magnitude=1.7):
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

def poll_remove(name):
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

def poll_list():
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

def poll_send_template(poll_name, earthquake_data=None):
    """Send WhatsApp template to users based on poll configuration."""
    db = EarthquakeDatabase()
    try:
        if earthquake_data is None:
            earthquakes = db.get_latest_earthquakes(limit=1)
            if not earthquakes:
                print("No earthquake data available")
                sys.exit(1)
            # Format as expected by polls.send_wa_template
            earthquake_data = {
                "count": 1,
                "data": earthquakes
            }

        # Use the function from polls.py
        send_wa_template(poll_name, earthquake_data)

    except Exception as e:
        print(f"Error sending WhatsApp templates: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
def poll_add_wa_user(name, phone_number, poll_name=None):
    """Add a new WhatsApp user to the database."""
    db = EarthquakeDatabase()
    try:
        user_id = db.create_wa_user(name, phone_number, poll_name)
        poll_msg = f" for poll '{poll_name}'" if poll_name else ""
        print(f"Successfully added WhatsApp user '{name}' with ID {user_id}{poll_msg}")
    except Exception as e:
        print(f"Error adding WhatsApp user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def poll_remove_wa_user(phone_number, poll_name=None):
    """Remove a WhatsApp user from the database by phone number."""
    db = EarthquakeDatabase()
    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM wa_users WHERE phone_number = ?', (phone_number,))
        user = cursor.fetchone()

        if not user:
            print(f"Error: No WhatsApp user found with phone number '{phone_number}'")
            sys.exit(1)

        cursor.execute('DELETE FROM wa_users WHERE phone_number = ? AND poll_name = ?', (phone_number, poll_name))

        conn.commit()

        if cursor.rowcount > 0:
            if poll_name:
                print(f"Successfully removed WhatsApp user with phone number '{phone_number}' from poll '{poll_name}'")
            else:
                print(f"Successfully removed WhatsApp user with phone number '{phone_number}'")
        else:
            print(f"Error: Failed to remove WhatsApp user with phone number '{phone_number}'")
            sys.exit(1)

    except Exception as e:
        print(f"Error removing WhatsApp user: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def poll_list_wa_users():
    """List all WhatsApp users in the database."""
    db = EarthquakeDatabase()
    try:
        users = db.get_wa_users()

        if not users:
            print("No WhatsApp users found")
            return

        print(f"{'ID':<5} {'Name':<20} {'Phone Number':<20} {'Poll':<20} {'Last Sent':<20} {'Created':<20}")
        print("-" * 110)

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

def poll_help():
    """Show help for poll commands."""
    print("Poll Management Commands")
    print("\nUsage: manage.py poll <command> [arguments]")
    print("\nCommands:")
    print("  add <type> <name> [min_magnitude]         - Add a new poll")
    print("  remove <name>                             - Remove a poll by name")
    print("  list                                      - List all polls")
    print("  send-template <poll_name>                 - Send WhatsApp template for a poll")
    print("  add-wa-user <name> <phone> [poll_name]    - Add a WhatsApp user")
    print("  remove-wa-user <phone_number> [poll_name] - Remove a WhatsApp user")
    print("  list-wa-users                             - List all WhatsApp users")
    print(f"\nValid poll types: {', '.join(VALID_POLL_TYPES)}")
    print("\nExamples:")
    print("  manage.py poll add whatsapp company1 2.5")
    print("  manage.py poll add-wa-user \"John Doe\" 905554444 company1")
    print("  manage.py poll list")
    print("  manage.py poll send-template company1")

# =============================================================================
# SYSTEM COMMANDS
# =============================================================================

def system_remove_last_earthquake():
    """Remove the last earthquake from the database."""
    db = EarthquakeDatabase()
    try:
        db.delete_last_earthquake()
        print("Successfully removed the last earthquake from the database")
    except Exception as e:
        print(f"Error removing last earthquake: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

def system_help():
    """Show help for system commands."""
    print("System Management Commands")
    print("\nUsage: manage.py system <command>")
    print("\nCommands:")
    print("  remove-last-earthquake  - Remove the last earthquake from the database")
    print("\nExamples:")
    print("  manage.py system remove-last-earthquake")

# =============================================================================
# MAIN COMMAND DISPATCHER
# =============================================================================

def show_main_help():
    """Display main help information."""
    print("Earthquake API Management Tool")
    print("\nUsage: manage.py <category> <command> [arguments]")
    print("\nCategories:")
    print("  user     - Manage application users")
    print("  webhook  - Manage webhooks for notifications")
    print("  poll     - Manage polling configurations and WhatsApp users")
    print("  system   - System maintenance commands")
    print("\nFor detailed help on a category, use:")
    print("  manage.py <category>")
    print("\nExamples:")
    print("  manage.py user")
    print("  manage.py webhook add discord https://... my-webhook")
    print("  manage.py poll add-wa-user \"John Doe\" 905554444 company1")
    print("  manage.py poll list")

def main():
    """Parse arguments and dispatch to appropriate function."""
    if len(sys.argv) < 2:
        show_main_help()
        sys.exit(0)

    category = sys.argv[1]

    # Handle help for main categories
    if category in ["help", "--help", "-h"]:
        show_main_help()
        sys.exit(0)

    # USER COMMANDS
    elif category == "user":
        if len(sys.argv) < 3:
            user_help()
            sys.exit(0)

        command = sys.argv[2]

        if command == "create":
            if len(sys.argv) < 5:
                print("Error: create command requires name and password")
                user_help()
                sys.exit(1)
            name = sys.argv[3]
            password = sys.argv[4]
            poll_name = sys.argv[5] if len(sys.argv) > 5 else None
            user_create(name, password, poll_name)

        else:
            print(f"Error: Unknown user command '{command}'")
            user_help()
            sys.exit(1)

    # WEBHOOK COMMANDS
    elif category == "webhook":
        if len(sys.argv) < 3:
            webhook_help()
            sys.exit(0)

        command = sys.argv[2]

        if command == "add":
            if len(sys.argv) < 6:
                print("Error: add command requires type, url, and name")
                webhook_help()
                sys.exit(1)
            webhook_type = sys.argv[3]
            url = sys.argv[4]
            name = sys.argv[5]
            webhook_add(webhook_type, url, name)

        elif command == "remove":
            if len(sys.argv) < 4:
                print("Error: remove command requires name")
                webhook_help()
                sys.exit(1)
            name = sys.argv[3]
            webhook_remove(name)

        elif command == "list":
            webhook_type = sys.argv[3] if len(sys.argv) > 3 else None
            webhook_list(webhook_type)

        elif command == "test":
            if len(sys.argv) < 4:
                print("Error: test command requires name")
                webhook_help()
                sys.exit(1)
            name = sys.argv[3]
            webhook_test(name)

        elif command == "send":
            name = sys.argv[3] if len(sys.argv) > 3 else None
            webhook_send(name)

        else:
            print(f"Error: Unknown webhook command '{command}'")
            webhook_help()
            sys.exit(1)

    # POLL COMMANDS
    elif category == "poll":
        if len(sys.argv) < 3:
            poll_help()
            sys.exit(0)

        command = sys.argv[2]

        if command == "add":
            if len(sys.argv) < 5:
                print("Error: add command requires type and name")
                poll_help()
                sys.exit(1)
            poll_type = sys.argv[3]
            name = sys.argv[4]
            min_magnitude = float(sys.argv[5]) if len(sys.argv) > 5 else 1.7
            poll_add(poll_type, name, min_magnitude)

        elif command == "remove":
            if len(sys.argv) < 4:
                print("Error: remove command requires name")
                poll_help()
                sys.exit(1)
            name = sys.argv[3]
            poll_remove(name)

        elif command == "list":
            poll_list()

        elif command == "send-template":
            if len(sys.argv) < 4:
                print("Error: send-template command requires poll name")
                poll_help()
                sys.exit(1)
            poll_name = sys.argv[3]
            poll_send_template(poll_name)

        elif command == "add-wa-user":
            if len(sys.argv) < 5:
                print("Error: add-wa-user command requires name and phone number")
                poll_help()
                sys.exit(1)
            name = sys.argv[3]
            phone_number = sys.argv[4]
            poll_name = sys.argv[5] if len(sys.argv) > 5 else None
            poll_add_wa_user(name, phone_number, poll_name)

        elif command == "remove-wa-user":
            if len(sys.argv) < 4:
                print("Error: remove-wa-user command requires phone number")
                poll_help()
                sys.exit(1)

            phone_number = sys.argv[3]

            poll_name = None
            if len(sys.argv) > 4:
                poll_name = sys.argv[4]
            if poll_name:
                poll_remove_wa_user(phone_number, poll_name)
            else:
                poll_remove_wa_user(phone_number)

        elif command == "list-wa-users":
            poll_list_wa_users()

        else:
            print(f"Error: Unknown poll command '{command}'")
            poll_help()
            sys.exit(1)

    # SYSTEM COMMANDS
    elif category == "system":
        if len(sys.argv) < 3:
            system_help()
            sys.exit(0)

        command = sys.argv[2]

        if command == "remove-last-earthquake":
            system_remove_last_earthquake()

        else:
            print(f"Error: Unknown system command '{command}'")
            system_help()
            sys.exit(1)

    else:
        print(f"Error: Unknown category '{category}'")
        show_main_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
