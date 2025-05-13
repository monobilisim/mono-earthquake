#!/usr/bin/env python3
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from webhooks import discord, zulip, whatsapp, generic

# Define valid webhook types
VALID_WEBHOOK_TYPES = [
    "whatsapp",
    "zulip",
    "discord",
    "generic" # just sends the json object looks like {count: n, data: [{}, {}]}
]

# Database path
DB_PATH = "./data/earthquakes.db"

def ensure_webhooks_table(conn):
    """Ensure the webhooks table exists in the database."""
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS webhooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        url TEXT NOT NULL,
        type VARCHAR(255) NOT NULL,
        last_sent_at DATETIME,
        created_at TEXT NOT NULL,
        UNIQUE(url),
        UNIQUE(name)
    )
    ''')

    # Create index on webhook name for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_webhooks_name ON webhooks(name)')
    conn.commit()

def connect_db():
    """Connect to the SQLite database and ensure the webhook table exists."""
    try:
        # Ensure the directory exists
        Path(DB_PATH).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries

        # Ensure table exists
        ensure_webhooks_table(conn)

        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

def add_webhook(webhook_type, url, name):
    """Add a new webhook to the database."""
    if webhook_type not in VALID_WEBHOOK_TYPES:
        print(f"Error: Invalid webhook type '{webhook_type}'")
        print(f"Valid types are: {', '.join(VALID_WEBHOOK_TYPES)}")
        sys.exit(1)

    conn = connect_db()
    try:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute('''
        INSERT INTO webhooks (name, url, type, created_at)
        VALUES (?, ?, ?, ?)
        ''', (name, url, webhook_type, now))

        conn.commit()
        print(f"Successfully added webhook '{name}' of type '{webhook_type}'")
    except sqlite3.IntegrityError:
        print(f"Error: A webhook with name '{name}' or URL '{url}' already exists")
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"Error adding webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def remove_webhook(name):
    """Remove a webhook from the database by name."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM webhooks WHERE name = ?', (name,))
        webhook = cursor.fetchone()

        if not webhook:
            print(f"Error: No webhook found with name '{name}'")
            sys.exit(1)

        cursor.execute('DELETE FROM webhooks WHERE name = ?', (name,))
        conn.commit()
        print(f"Successfully removed webhook '{name}'")
    except sqlite3.Error as e:
        print(f"Error removing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def list_webhooks(webhook_type=None):
    """List webhooks, optionally filtered by type."""
    conn = connect_db()
    try:
        cursor = conn.cursor()

        if webhook_type:
            if webhook_type not in VALID_WEBHOOK_TYPES:
                print(f"Error: Invalid webhook type '{webhook_type}'")
                print(f"Valid types are: {', '.join(VALID_WEBHOOK_TYPES)}")
                sys.exit(1)

            cursor.execute('''
            SELECT id, name, url, type, last_sent_at, created_at
            FROM webhooks
            WHERE type = ?
            ORDER BY name
            ''', (webhook_type,))
        else:
            cursor.execute('''
            SELECT id, name, url, type, last_sent_at, created_at
            FROM webhooks
            ORDER BY name
            ''')

        webhooks = cursor.fetchall()

        if not webhooks:
            message = f"No webhooks found of type '{webhook_type}'" if webhook_type else "No webhooks found"
            print(message)
            return

        # Print table header
        if webhook_type:
            # If type is provided, omit the Type column
            print(f"{'ID':<5} {'Name':<20} {'Last Sent':<30} {'URL':<50}")
            print("-" * 100)

            for webhook in webhooks:
                last_sent = webhook['last_sent_at'] or "Never"
                print(f"{webhook['id']:<5} {webhook['name']:<20} {last_sent:<30} {webhook['url']:<50}")
        else:
            # If no type is provided, show all columns including Type
            print(f"{'ID':<5} {'Name':<20} {'Type':<10} {'Last Sent':<30} {'URL':<50}")
            print("-" * 110)

            for webhook in webhooks:
                last_sent = webhook['last_sent_at'] or "Never"
                print(f"{webhook['id']:<5} {webhook['name']:<20} {webhook['type']:<10} {last_sent:<30} {webhook['url']:<50}")

    except sqlite3.Error as e:
        print(f"Error listing webhooks: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def fetch_latest_earthquake():
    """Fetch the latest earthquake data from the database."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM earthquakes
        ORDER BY timestamp DESC
        LIMIT 1
        ''')

        earthquake = cursor.fetchone()
        if not earthquake:
            print("No earthquake data found in the database.")
            return None

        return dict(earthquake)
    except sqlite3.Error as e:
        print(f"Error fetching latest earthquake data: {e}", file=sys.stderr)
        return None
    finally:
        conn.close()

def test_webhook(name):
    """Test a webhook by sending a test message."""
    conn = connect_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM webhooks WHERE name = ?', (name,))
        webhook = cursor.fetchone()

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
            now = datetime.now().isoformat()
            cursor.execute('UPDATE webhooks SET last_sent_at = ? WHERE name = ?', (now, name))
            conn.commit()
            print("Webhook test successful! Updated last sent timestamp.")
        else:
            print("Test webhook failed. Please check URL and network connection.")

    except sqlite3.Error as e:
        print(f"Error testing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

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

    conn = connect_db()
    try:
        cursor = conn.cursor()
        if name:
            # Send to a specific webhook
            cursor.execute('SELECT * FROM webhooks WHERE name = ?', (name,))
            webhook = cursor.fetchone()

            if not webhook:
                print(f"Error: No webhook found with name '{name}'")
                sys.exit(1)

            process_webhook_send(webhook, earthquake_data, cursor, conn)
        else:
            # Send to all webhooks
            cursor.execute('SELECT * FROM webhooks')
            webhooks = cursor.fetchall()

            if not webhooks:
                print("No webhooks found.")
                sys.exit(1)

            for webhook in webhooks:
                process_webhook_send(webhook, earthquake_data, cursor, conn)

    except sqlite3.Error as e:
        print(f"Error sending earthquake data to webhook(s): {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def process_webhook_send(webhook, earthquake_data, cursor, conn):
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
        now = datetime.now().isoformat()
        cursor.execute('UPDATE webhooks SET last_sent_at = ? WHERE name = ?', (now, webhook_name))
        conn.commit()
        print(f"Successfully sent latest earthquake data to '{webhook_name}'")
    else:
        print(f"Failed to send earthquake data to '{webhook_name}'")

def show_help():
    """Display help information about this tool."""
    print("Earthquake API Webhook Management Tool")
    print("\nCommands:")
    print("  help                           - Show this help message")
    print("  add <type> <url> <name>        - Add a new webhook")
    print("  remove <name>                  - Remove a webhook by name")
    print("  list                           - List all webhooks")
    print("  list <type>                    - List webhooks of a specific type")
    print("  test <name>                    - Test a webhook by sending a test message")
    print("  send <name>                    - Send latest earthquake data to a webhook")
    print("\nValid webhook types:")
    for t in VALID_WEBHOOK_TYPES:
        print(f"  - {t}")

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
            print("Name is not provided")
        else:
            show_help()

    else:
        print("Error: Invalid command or arguments")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
