import json
import hmac
import hashlib
import logging
import requests
from datetime import datetime
from threading import Thread

from models import Webhook, WebhookEvent
from app import db

# Configure logging
logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages webhook triggers and dispatching"""
    
    @staticmethod
    def trigger_webhook_async(user_id, event_type, payload):
        """Trigger webhooks asynchronously for a specific event type"""
        thread = Thread(
            target=WebhookManager._trigger_webhook,
            args=(user_id, event_type, payload)
        )
        thread.daemon = True
        thread.start()
    
    @staticmethod
    def _trigger_webhook(user_id, event_type, payload):
        """Trigger webhooks for a specific event type (internal method)"""
        try:
            webhooks = Webhook.query.filter_by(user_id=user_id, is_active=True).all()
            
            for webhook in webhooks:
                try:
                    events = json.loads(webhook.events)
                    if event_type not in events:
                        continue
                    
                    # Create webhook event record
                    event = WebhookEvent(
                        webhook_id=webhook.id,
                        event_type=event_type,
                        payload=json.dumps(payload),
                        status='pending'
                    )
                    
                    db.session.add(event)
                    db.session.commit()
                    
                    # Send the webhook request
                    WebhookManager._send_webhook_request(webhook, event, payload, event_type)
                    
                except Exception as e:
                    logger.error(f"Error processing webhook {webhook.id}: {str(e)}")
                    
                    # Update webhook failure stats
                    webhook.failure_count += 1
                    db.session.commit()
        except Exception as e:
            logger.error(f"Error triggering webhooks for event {event_type}: {str(e)}")
    
    @staticmethod
    def _send_webhook_request(webhook, event, payload, event_type):
        """Send the actual webhook HTTP request"""
        try:
            # Calculate signature if secret is provided
            signature = None
            timestamp = str(int(datetime.utcnow().timestamp()))
            
            if webhook.secret:
                payload_string = json.dumps(payload)
                signature_base = f"{timestamp}.{payload_string}"
                signature = hmac.new(
                    webhook.secret.encode(),
                    signature_base.encode(),
                    hashlib.sha256
                ).hexdigest()
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-HACF-Event': event_type,
                'X-HACF-Timestamp': timestamp,
                'User-Agent': 'HACF-Webhook-Service/1.0'
            }
            
            if signature:
                headers['X-HACF-Signature'] = f"sha256={signature}"
            
            # Send request
            response = requests.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=5
            )
            
            # Update event record
            event.status = 'sent' if response.ok else 'failed'
            event.response_code = response.status_code
            event.response_body = response.text[:1000]  # Limit response size
            event.processed_at = datetime.utcnow()
            
            # Update webhook stats
            webhook.last_triggered_at = datetime.utcnow()
            if not response.ok:
                webhook.failure_count += 1
            
            db.session.commit()
            
            logger.info(f"Webhook {webhook.id} triggered with status: {event.status}, code: {response.status_code}")
            
        except requests.RequestException as e:
            logger.error(f"Request error sending webhook {webhook.id}: {str(e)}")
            
            # Update event as failed
            event.status = 'failed'
            event.response_body = str(e)[:1000]
            event.processed_at = datetime.utcnow()
            
            # Update webhook failure stats
            webhook.failure_count += 1
            webhook.last_triggered_at = datetime.utcnow()
            
            db.session.commit()
        except Exception as e:
            logger.error(f"Unexpected error sending webhook {webhook.id}: {str(e)}")
            
            # Update webhook failure stats
            webhook.failure_count += 1
            db.session.commit()
    
    @staticmethod
    def retry_failed_webhooks():
        """Retry failed webhook events with retry count < 3"""
        try:
            # Find failed webhook events with retry count < 3
            events = WebhookEvent.query.filter_by(status='failed')\
                .filter(WebhookEvent.retry_count < 3)\
                .all()
            
            for event in events:
                try:
                    webhook = Webhook.query.get(event.webhook_id)
                    if not webhook or not webhook.is_active:
                        continue
                    
                    # Parse payload
                    payload = json.loads(event.payload)
                    
                    # Increment retry count
                    event.retry_count += 1
                    db.session.commit()
                    
                    # Send the webhook request again
                    WebhookManager._send_webhook_request(webhook, event, payload, event.event_type)
                    
                except Exception as e:
                    logger.error(f"Error retrying webhook event {event.id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in retry_failed_webhooks: {str(e)}")

# Event type constants
class WebhookEvents:
    """Constants for webhook event types"""
    PROJECT_CREATED = 'project.created'
    PROJECT_UPDATED = 'project.updated'
    PROJECT_DELETED = 'project.deleted'
    PROJECT_COMPLETED = 'project.completed'
    
    USER_REGISTERED = 'user.registered'
    USER_UPDATED = 'user.updated'
    
    TEAM_CREATED = 'team.created'
    TEAM_UPDATED = 'team.updated'
    TEAM_DELETED = 'team.deleted'
    TEAM_MEMBER_ADDED = 'team.member.added'
    TEAM_MEMBER_UPDATED = 'team.member.updated'
    TEAM_MEMBER_REMOVED = 'team.member.removed'
    
    TEMPLATE_CREATED = 'template.created'
    TEMPLATE_UPDATED = 'template.updated'
    TEMPLATE_DELETED = 'template.deleted'
    TEMPLATE_USED = 'template.used'
    
    API_KEY_GENERATED = 'api.key.generated'
    API_QUOTA_EXCEEDED = 'api.quota.exceeded'
    
    # Get all available event types
    @classmethod
    def get_all_events(cls):
        """Get a list of all webhook event types"""
        events = []
        for attr in dir(cls):
            if not attr.startswith('__') and not callable(getattr(cls, attr)):
                events.append(getattr(cls, attr))
        return events