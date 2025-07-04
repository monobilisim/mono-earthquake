import os
import json
import logging
from datetime import datetime
from pathlib import Path
from database import EarthquakeDatabase
from load_dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WA_NUMBER_ID = os.getenv('WA_NUMBER_ID')
WA_API_TOKEN = os.getenv('WA_API_TOKEN')
TEMPLATE_NAME = os.getenv('TEMPLATE_NAME')
TEMPLATE_LANGUAGE = os.getenv('TEMPLATE_LANGUAGE')

def process_whatsapp_webhook(webhook_data):
    """
    Process incoming WhatsApp webhook data.

    Args:
        webhook_data: The webhook payload from WhatsApp

    Returns:
        bool: True if processed successfully, False otherwise
    """
    try:
        if not webhook_data:
            logger.warning("Empty webhook data received")
            return False

        logger.info(f"Processing WhatsApp webhook: {json.dumps(webhook_data, indent=2)}")

        if not is_polls_related_webhook(webhook_data):
            logger.info("Webhook is not polls-related, skipping")
            return True

        db = EarthquakeDatabase()
        try:
            if 'entry' in webhook_data:
                for entry in webhook_data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if change.get('field') == 'messages':
                                value = change.get('value', {})

                                # Process message statuses
                                if 'statuses' in value:
                                    for status in value['statuses']:
                                        process_message_status(status, db)

                                # Process incoming messages
                                if 'messages' in value:
                                    for message in value['messages']:
                                        process_message(message, db)

            return True

        except Exception as e:
            logger.error(f"Error processing webhook data: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in process_whatsapp_webhook: {e}")
        return False

def process_message(message, db):
    """
    Process an incoming WhatsApp message.

    Args:
        message: Message data from webhook
        db: Database instance
    """
    try:
        message_type = message.get('type')
        phone_number = message.get('from')
        message_time = message.get('timestamp')

        logger.info(f"Processing message from {phone_number} of type {message_type}")

        # Handle different message types
        if message_type == 'text':
            text_content = message.get('text', {}).get('body', '')
            logger.info(f"Text message received: {text_content}")

        elif message_type == 'interactive':
            interactive = message.get('interactive', {})
            interactive_type = interactive.get('type')

            if interactive_type == 'button_reply':
                button_reply = interactive.get('button_reply', {})
                button_id = button_reply.get('id')
                button_title = button_reply.get('title')
                logger.info(f"Button reply received: {button_id} - {button_title}")

            elif interactive_type == 'list_reply':
                list_reply = interactive.get('list_reply', {})
                list_id = list_reply.get('id')
                list_title = list_reply.get('title')
                logger.info(f"List reply received: {list_id} - {list_title}")

        # Update user's last activity
        if phone_number:
            db.update_wa_user_last_sent(phone_number)

    except Exception as e:
        logger.error(f"Error processing message: {e}")

def process_message_status(status, db):
    """
    Process a WhatsApp message status update.

    Args:
        status: Status data from webhook
        db: Database instance
    """
    try:
        message_id = status.get('id')
        recipient_id = status.get('recipient_id')
        status_type = status.get('status')
        timestamp = status.get('timestamp')

        logger.info(f"Message status update: {message_id} - {status_type} for {recipient_id}")

        # Update template message status if applicable
        if status_type in ['delivered', 'read', 'failed']:
            update_template_response(recipient_id, status_type, timestamp, db)

    except Exception as e:
        logger.error(f"Error processing message status: {e}")

def update_template_response(phone_number, status, timestamp, db):
    """
    Update template message response status.

    Args:
        phone_number: Phone number of recipient
        status: Status type (delivered, read, failed)
        timestamp: Status timestamp
        db: Database instance
    """
    try:
        logger.info(f"Template status update for {phone_number}: {status} at {timestamp}")

        # Update user's last activity
        db.update_wa_user_last_sent(phone_number)

    except Exception as e:
        logger.error(f"Error updating template response: {e}")

def get_template_statistics():
    """
    Get statistics about template messages.

    Returns:
        dict: Template statistics
    """
    try:
        db = EarthquakeDatabase()
        try:
            # Get basic statistics about WhatsApp users
            users = db.get_wa_users()

            total_users = len(users)
            active_users = len([u for u in users if u.get('last_sent_at')])

            return {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users,
                'template_messages_sent': 0,
                'template_messages_delivered': 0,
                'template_messages_read': 0,
                'recent_templates': 0
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting template statistics: {e}")
        return {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'template_messages_sent': 0,
            'template_messages_delivered': 0,
            'template_messages_read': 0,
            'recent_templates': 0
        }

def is_polls_related_webhook(webhook_data):
    """
    Check if a webhook is related to polls functionality.

    Args:
        webhook_data: The webhook payload

    Returns:
        bool: True if polls-related, False otherwise
    """
    try:
        # Check if webhook contains WhatsApp message data
        if 'entry' in webhook_data:
            for entry in webhook_data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if change.get('field') == 'messages':
                            return True

        # Check for other WhatsApp webhook indicators
        if 'object' in webhook_data and webhook_data['object'] == 'whatsapp_business_account':
            return True

        return False

    except Exception as e:
        logger.error(f"Error checking if webhook is polls-related: {e}")
        return False

def has_recent_template(phone_number, hours=24):
    """
    Check if a phone number has received a template recently.

    Args:
        phone_number: Phone number to check
        hours: Number of hours to look back

    Returns:
        bool: True if recent template found, False otherwise
    """
    try:
        db = EarthquakeDatabase()
        try:
            # Get user by phone number
            users = db.get_wa_users()
            user = None
            for u in users:
                if u.get('phone_number') == phone_number:
                    user = u
                    break

            if not user or not user.get('last_sent_at'):
                return False

            # Check if last sent was within the specified hours
            last_sent = datetime.fromisoformat(user['last_sent_at'])
            now = datetime.now()
            time_diff = now - last_sent

            return time_diff.total_seconds() < (hours * 3600)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error checking recent template: {e}")
        return False

def create_test_poll_data():
    """
    Create test poll data for development purposes.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = EarthquakeDatabase()
        try:
            # Create a test poll
            poll_id = db.create_poll("test_poll", "whatsapp", 2.0)
            logger.info(f"Created test poll with ID: {poll_id}")

            # Create a test user
            user_id = db.create_wa_user("Test User", "+1234567890")
            logger.info(f"Created test user with ID: {user_id}")

            return True

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error creating test poll data: {e}")
        return False
