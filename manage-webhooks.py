#!/usr/bin/env python3
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from webhooks import discord, zulip, whatsapp

# Define valid webhook types
VALID_WEBHOOK_TYPES = [
    "whatsapp",
    "zulip",
    "discord",
    "generic" # just sends the json object looks like {count: n, data: [{}, {}]}
]

# Database path
DB_PATH = "./data/earthquakes.db"

def connect_db():
    """Connect to the SQLite database and ensure the webhook table exists."""
    try:
        # Ensure the directory exists
        Path(DB_PATH).parent.mkdir(exist_ok=True, parents=True)

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries

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
        print(f"{'ID':<5} {'Name':<20} {'Type':<10} {'Last Sent':<25} {'URL':<50}")
        print("-" * 110)

        for webhook in webhooks:
            last_sent = webhook['last_sent_at'] or "Never"
            print(f"{webhook['id']:<5} {webhook['name']:<20} {webhook['type']:<10} {last_sent:<25} {webhook['url']:<50}")

    except sqlite3.Error as e:
        print(f"Error listing webhooks: {e}", file=sys.stderr)
        sys.exit(1)
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
            success = discord(webhook_url)
        elif webhook_type == 'zulip':
            success = zulip(webhook_url)
        elif webhook_type == 'whatsapp':
            success = whatsapp(webhook_url)
        else:
            print(f"Testing for webhook type '{webhook_type}' is not implemented yet")
            sys.exit(1)

        if success:
            # Update last_sent_at timestamp
            now = datetime.now().isoformat()
            cursor.execute('UPDATE webhooks SET last_sent_at = ? WHERE name = ?', (now, name))
            conn.commit()
            print("Webhook test successful! Updated last sent timestamp.")

    except sqlite3.Error as e:
        print(f"Error testing webhook: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def show_help():
    """Display help information about this tool."""
    print("Earthquake API Webhook Management Tool")
    print("\nCommands:")
    print("  help                           - Show this help message")
    print("  add <type> <url> <name>        - Add a new webhook")
    print("  remove <name>                  - Remove a webhook by name")
    print("  list                           - List all webhooks")
    print("  list <type>                    - List webhooks of a specific type")
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

    else:
        print("Error: Invalid command or arguments")
        show_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
