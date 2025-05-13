import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

def discord(webhook_url, earthquake_data=None):
    """
    Send earthquake data to a Discord webhook.

    Args:
        webhook_url: The Discord webhook URL
        earthquake_data: Optional dictionary containing earthquake data.
                        If None, sends a test message.
    """
    if earthquake_data is None:
        # Send a test message if no earthquake data is provided
        payload = {
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
        
        # Send the webhook
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)
            
            if response.status_code == 204:  # Discord returns 204 No Content on success
                print(f"Successfully sent test message to Discord webhook")
                return True
            else:
                print(f"Error sending to Discord webhook: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error sending to Discord webhook: {str(e)}")
            return False

    # Extract individual earthquake records if the data is in API response format
    if isinstance(earthquake_data, dict) and "data" in earthquake_data and isinstance(earthquake_data["data"], list):
        # API response format - process each earthquake
        earthquakes = earthquake_data["data"]
        success = True

        # Send a message for each earthquake (or just the first one to avoid spam)
        for earthquake in earthquakes[:1]:  # Limit to first record to avoid spam
            if not send_single_earthquake(webhook_url, earthquake):
                success = False

        return success
    else:
        # Single earthquake record format
        return send_single_earthquake(webhook_url, earthquake_data)

def send_single_earthquake(webhook_url, earthquake):
    """Send a single earthquake record to Discord webhook."""
    # Format actual earthquake data for Discord
    magnitude = earthquake.get("magnitude", "N/A")
    location = earthquake.get("location", "Unknown location")
    depth = earthquake.get("depth", "N/A")
    timestamp = earthquake.get("timestamp", datetime.now().isoformat())
    lat = earthquake.get("latitude", "N/A")
    lon = earthquake.get("longitude", "N/A")

    # Determine color based on magnitude
    color = 16711680  # Red for high magnitude
    if isinstance(magnitude, (int, float)):
        if magnitude < 4.0:
            color = 3066993  # Green
        elif magnitude < 5.5:
            color = 16776960  # Yellow

    # Create a Google Maps link
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    payload = {
        "content": f"🚨 **Earthquake Alert: Magnitude {magnitude}**",
        "embeds": [
            {
                "title": f"Earthquake in {location}",
                "description": f"A magnitude **{magnitude}** earthquake has been detected.",
                "color": color,
                "fields": [
                    {"name": "Location", "value": location, "inline": True},
                    {"name": "Depth", "value": f"{depth} km", "inline": True},
                    {"name": "Coordinates", "value": f"[{lat}, {lon}]({maps_url})", "inline": True}
                ],
                "footer": {"text": "Data from Kandilli Observatory and Earthquake Research Institute"},
                "timestamp": timestamp
            }
        ]
    }

    # Send the webhook
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers)

        if response.status_code == 204:  # Discord returns 204 No Content on success
            print(f"Successfully sent earthquake in {location} to Discord webhook")
            return True
        else:
            print(f"Error sending to Discord webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to Discord webhook: {str(e)}")
        return False

def zulip(webhook_url, earthquake_data=None):
    """
    Send earthquake data to a Zulip webhook.

    Args:
        webhook_url: The Zulip webhook URL (includes bot email & API key)
        earthquake_data: Optional dictionary containing earthquake data.
                        If None, sends a test message.
    """
    if earthquake_data is None:
        # Send a test message if no earthquake data is provided
        payload = {
            "type": "stream",
            "to": "general",
            "topic": "Earthquake API Test",
            "content": "🔔 **Test Notification from Earthquake API**\n\nYour webhook is configured correctly!"
        }
        return send_zulip_message(webhook_url, payload)

    # Extract individual earthquake records if the data is in API response format
    if isinstance(earthquake_data, dict) and "data" in earthquake_data and isinstance(earthquake_data["data"], list):
        # API response format - process each earthquake
        earthquakes = earthquake_data["data"]
        success = True

        # Send a message for each earthquake (or just the first one to avoid spam)
        for earthquake in earthquakes[:1]:  # Limit to first record to avoid spam
            if not send_single_earthquake_to_zulip(webhook_url, earthquake):
                success = False

        return success
    else:
        # Single earthquake record format
        return send_single_earthquake_to_zulip(webhook_url, earthquake_data)

def send_single_earthquake_to_zulip(webhook_url, earthquake):
    """Send a single earthquake record to Zulip webhook."""
    # Format actual earthquake data for Zulip
    magnitude = earthquake.get("magnitude", "N/A")
    location = earthquake.get("location", "Unknown location")
    depth = earthquake.get("depth", "N/A")
    timestamp = earthquake.get("timestamp", datetime.now().isoformat())
    lat = earthquake.get("latitude", "N/A")
    lon = earthquake.get("longitude", "N/A")

    # Create a Google Maps link
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    # Format message as markdown
    content = f"""
🚨 **Earthquake Alert: Magnitude {magnitude}**

**Location**: {location}
**Depth**: {depth} km
**Coordinates**: [{lat}, {lon}]({maps_url})
**Time**: {timestamp}

Data provided by Kandilli Observatory and Earthquake Research Institute
"""

    payload = {
        "type": "stream",
        "to": "earthquakes",  # Stream name - can be configured
        "topic": f"M{magnitude} - {location}",  # Topic for the message
        "content": content
    }

    return send_zulip_message(webhook_url, payload)

def send_zulip_message(webhook_url, payload):
    """Send a message to Zulip webhook."""
    try:
        # Zulip webhooks include the bot email and API key in the URL
        # Example: https://yourzulip.zulipchat.com/api/v1/messages
        # The webhook_url should include the full URL

        # Extract email and API key if they're provided in the URL
        # Format expected: https://yourzulip.zulipchat.com|bot-email|api-key
        parts = webhook_url.split('|')

        if len(parts) == 3:
            # URL contains credentials
            base_url = parts[0]
            email = parts[1]
            api_key = parts[2]

            headers = {"Content-Type": "application/json"}
            response = requests.post(
                base_url,
                auth=(email, api_key),
                json=payload
            )
        else:
            # Assume URL is complete
            headers = {"Content-Type": "application/json"}
            response = requests.post(webhook_url, json=payload)

        if response.status_code == 200:  # Zulip returns 200 OK on success
            result = response.json()
            if result.get('result') == 'success':
                print(f"Successfully sent to Zulip webhook")
                return True
            else:
                print(f"Error from Zulip API: {result}")
                return False
        else:
            print(f"Error sending to Zulip webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to Zulip webhook: {str(e)}")
        return False

def whatsapp(webhook_url, earthquake_data=None):
    """
    Send earthquake data to WhatsApp using Cloud API.

    Args:
        webhook_url: The WhatsApp webhook URL including token
                    Format: https://graph.facebook.com/v17.0/PHONE_NUMBER_ID|ACCESS_TOKEN
        earthquake_data: Optional dictionary containing earthquake data.
                        If None, sends a test message.
    """
    if earthquake_data is None:
        # Send a test message if no earthquake data is provided
        message_body = "🔔 *Test Notification from Earthquake API*\n\nYour webhook is configured correctly!"
        return send_whatsapp_message(webhook_url, message_body)

    # Extract individual earthquake records if the data is in API response format
    if isinstance(earthquake_data, dict) and "data" in earthquake_data and isinstance(earthquake_data["data"], list):
        # API response format - process each earthquake
        earthquakes = earthquake_data["data"]
        success = True

        # Send a message for each earthquake (or just the first one to avoid spam)
        for earthquake in earthquakes[:1]:  # Limit to first record to avoid spam
            if not send_single_earthquake_to_whatsapp(webhook_url, earthquake):
                success = False

        return success
    else:
        # Single earthquake record format
        return send_single_earthquake_to_whatsapp(webhook_url, earthquake_data)

def send_single_earthquake_to_whatsapp(webhook_url, earthquake):
    """Send a single earthquake record to WhatsApp."""
    # Format actual earthquake data for WhatsApp
    magnitude = earthquake.get("magnitude", "N/A")
    location = earthquake.get("location", "Unknown location")
    depth = earthquake.get("depth", "N/A")
    timestamp = earthquake.get("timestamp", datetime.now().isoformat())
    lat = earthquake.get("latitude", "N/A")
    lon = earthquake.get("longitude", "N/A")

    # Create a Google Maps link
    maps_url = f"https://www.google.com/maps?q={lat},{lon}"

    # Format message for WhatsApp (using WhatsApp formatting)
    message_body = f"""🚨 *Earthquake Alert: Magnitude {magnitude}*

*Location*: {location}
*Depth*: {depth} km
*Coordinates*: {lat}, {lon}
*Time*: {timestamp}

Maps: {maps_url}

Data provided by Kandilli Observatory and Earthquake Research Institute"""

    return send_whatsapp_message(webhook_url, message_body)

def send_whatsapp_message(webhook_url, message_body, recipient=None):
    """Send a message to WhatsApp webhook."""
    try:
        # Parse the webhook URL to extract access token and phone number ID
        # Format expected: https://graph.facebook.com/v17.0/PHONE_NUMBER_ID|ACCESS_TOKEN
        parts = webhook_url.split('|')

        if len(parts) != 2:
            print("Invalid WhatsApp webhook URL format. Expected: BASE_URL|ACCESS_TOKEN")
            return False

        base_url = parts[0]
        access_token = parts[1]

        # If recipient is not specified, send to the default recipient
        # For a real implementation, you should store recipients in your database
        if not recipient:
            recipient = "default_recipient_phone_number"  # This should be replaced with actual recipient

        # Prepare the WhatsApp API payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message_body
            }
        }

        # Send request to WhatsApp Cloud API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.post(
            base_url + "/messages",
            json=payload,
            headers=headers
        )

        if response.status_code == 200:
            print(f"Successfully sent to WhatsApp webhook")
            return True
        else:
            print(f"Error sending to WhatsApp webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to WhatsApp webhook: {str(e)}")
        return False


def generic(webhook_url, earthquake_data=None):
    """
    Send earthquake data to a generic webhook endpoint.
    
    Args:
        webhook_url: The webhook URL
        earthquake_data: Optional dictionary containing earthquake data.
                        If None, sends a test message.
    """
    if earthquake_data is None:
        # Create a test message
        test_data = {
            "message": "Test notification from Earthquake API",
            "timestamp": datetime.now().isoformat(),
            "status": "test"
        }
        payload = test_data
    else:
        # Send the raw data
        payload = earthquake_data
    
    # Send to the webhook
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, json=payload, headers=headers)
        
        if 200 <= response.status_code < 300:  # Any 2XX status code is success
            print(f"Successfully sent to generic webhook (status {response.status_code})")
            return True
        else:
            print(f"Error sending to generic webhook: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending to generic webhook: {str(e)}")
        return False
