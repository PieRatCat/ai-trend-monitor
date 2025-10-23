"""
Subscriber Management Module
Handles newsletter subscriptions with GDPR compliance
Uses Azure Table Storage for subscriber data
"""
import os
import logging
import secrets
from datetime import datetime, timezone
from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

class SubscriberManager:
    """
    Manages newsletter subscribers in Azure Table Storage
    GDPR-compliant with explicit consent tracking
    """
    
    def __init__(self):
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.table_name = 'newslettersubscribers'
        
        if not self.connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING not found in environment")
        
        # Initialize table service
        self.table_service = TableServiceClient.from_connection_string(self.connection_string)
        self.table_client = self._get_or_create_table()
    
    def _get_or_create_table(self) -> TableClient:
        """Create table if it doesn't exist"""
        try:
            self.table_service.create_table(self.table_name)
            logging.info(f"Created table: {self.table_name}")
        except ResourceExistsError:
            logging.debug(f"Table already exists: {self.table_name}")
        
        return self.table_service.get_table_client(self.table_name)
    
    def create_subscription(self, email: str) -> dict:
        """
        Create a new subscription (pending confirmation)
        Returns confirmation token for double opt-in
        """
        # Generate unique confirmation token
        confirmation_token = secrets.token_urlsafe(32)
        
        # Email becomes the RowKey for easy lookup
        subscriber = {
            'PartitionKey': 'subscriber',
            'RowKey': email.lower(),  # Case-insensitive
            'email': email,
            'subscribed_date': datetime.now(timezone.utc).isoformat(),
            'confirmed': False,  # GDPR: Requires explicit confirmation
            'confirmation_token': confirmation_token,
            'active': False,  # Only active after confirmation
            'consent_ip': '',  # Optional: Store IP for GDPR audit trail
            'unsubscribe_token': secrets.token_urlsafe(32)
        }
        
        try:
            self.table_client.create_entity(subscriber)
            logging.info(f"Created pending subscription for: {email}")
            return {
                'success': True,
                'confirmation_token': confirmation_token,
                'message': 'Subscription created. Confirmation required.'
            }
        except ResourceExistsError:
            # Check if already confirmed
            existing = self.get_subscriber(email)
            if existing and existing.get('confirmed'):
                return {
                    'success': False,
                    'message': 'Email address already subscribed.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Confirmation email already sent. Please check your inbox.'
                }
        except Exception as e:
            logging.error(f"Error creating subscription: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def resend_confirmation(self, email: str) -> dict:
        """
        Resend confirmation email for pending subscriptions
        """
        try:
            subscriber = self.table_client.get_entity(
                partition_key='subscriber',
                row_key=email.lower()
            )
            
            # Only resend if not yet confirmed
            if subscriber.get('confirmed'):
                return {
                    'success': False,
                    'message': 'Email already confirmed'
                }
            
            # Get existing confirmation token
            confirmation_token = subscriber.get('confirmation_token')
            
            # Import here to avoid circular dependency
            from .confirmation_email import send_confirmation_email
            
            # Resend confirmation email
            if send_confirmation_email(email, confirmation_token):
                logging.info(f"Resent confirmation email to: {email}")
                return {
                    'success': True,
                    'message': 'Confirmation email resent! Please check your inbox.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Error sending confirmation email'
                }
                
        except ResourceNotFoundError:
            return {
                'success': False,
                'message': 'Email not found in subscribers'
            }
        except Exception as e:
            logging.error(f"Error resending confirmation: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def confirm_subscription(self, email: str, token: str) -> bool:
        """
        Confirm subscription with token (double opt-in)
        GDPR: Explicit consent through confirmation
        """
        try:
            subscriber = self.table_client.get_entity(
                partition_key='subscriber',
                row_key=email.lower()
            )
            
            if subscriber.get('confirmation_token') == token:
                subscriber['confirmed'] = True
                subscriber['active'] = True
                subscriber['confirmed_date'] = datetime.now(timezone.utc).isoformat()
                
                self.table_client.update_entity(subscriber, mode='replace')
                logging.info(f"Confirmed subscription for: {email}")
                return True
            else:
                logging.warning(f"Invalid confirmation token for: {email}")
                return False
                
        except ResourceNotFoundError:
            logging.warning(f"Subscriber not found: {email}")
            return False
        except Exception as e:
            logging.error(f"Error confirming subscription: {str(e)}")
            return False
    
    def unsubscribe(self, email: str, token: str) -> bool:
        """
        Unsubscribe user with token validation
        GDPR: Right to withdraw consent
        """
        try:
            subscriber = self.table_client.get_entity(
                partition_key='subscriber',
                row_key=email.lower()
            )
            
            if subscriber.get('unsubscribe_token') == token:
                subscriber['active'] = False
                subscriber['unsubscribed_date'] = datetime.now(timezone.utc).isoformat()
                
                self.table_client.update_entity(subscriber, mode='replace')
                logging.info(f"Unsubscribed: {email}")
                return True
            else:
                logging.warning(f"Invalid unsubscribe token for: {email}")
                return False
                
        except ResourceNotFoundError:
            logging.warning(f"Subscriber not found: {email}")
            return False
        except Exception as e:
            logging.error(f"Error unsubscribing: {str(e)}")
            return False
    
    def get_subscriber(self, email: str) -> dict:
        """Get subscriber details"""
        try:
            return self.table_client.get_entity(
                partition_key='subscriber',
                row_key=email.lower()
            )
        except ResourceNotFoundError:
            return None
    
    def get_active_subscribers(self) -> list:
        """
        Get all active, confirmed subscribers for newsletter delivery
        GDPR: Only send to users who gave explicit consent
        """
        try:
            query_filter = "PartitionKey eq 'subscriber' and active eq true and confirmed eq true"
            subscribers = self.table_client.query_entities(query_filter)
            
            active_list = [
                {
                    'email': sub['email'],
                    'unsubscribe_token': sub.get('unsubscribe_token', '')
                }
                for sub in subscribers
            ]
            
            logging.info(f"Retrieved {len(active_list)} active subscribers")
            return active_list
            
        except Exception as e:
            logging.error(f"Error retrieving subscribers: {str(e)}")
            return []
    
    def delete_subscriber(self, email: str) -> bool:
        """
        Permanently delete subscriber data
        GDPR: Right to erasure (right to be forgotten)
        """
        try:
            self.table_client.delete_entity(
                partition_key='subscriber',
                row_key=email.lower()
            )
            logging.info(f"Deleted subscriber data: {email}")
            return True
        except ResourceNotFoundError:
            logging.warning(f"Subscriber not found for deletion: {email}")
            return False
        except Exception as e:
            logging.error(f"Error deleting subscriber: {str(e)}")
            return False
    
    def get_subscriber_count(self) -> dict:
        """Get statistics about subscribers"""
        try:
            all_subscribers = list(self.table_client.query_entities(
                "PartitionKey eq 'subscriber'"
            ))
            
            stats = {
                'total': len(all_subscribers),
                'active': sum(1 for s in all_subscribers if s.get('active') and s.get('confirmed')),
                'pending': sum(1 for s in all_subscribers if not s.get('confirmed')),
                'unsubscribed': sum(1 for s in all_subscribers if not s.get('active') and s.get('confirmed'))
            }
            
            return stats
        except Exception as e:
            logging.error(f"Error getting subscriber count: {str(e)}")
            return {'total': 0, 'active': 0, 'pending': 0, 'unsubscribed': 0}
