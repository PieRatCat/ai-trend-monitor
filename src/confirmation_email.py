"""
Confirmation Email Module
Sends double opt-in confirmation emails for GDPR compliance
"""
import os
import logging
from azure.communication.email import EmailClient

def send_confirmation_email(email: str, confirmation_token: str) -> bool:
    """
    Send confirmation email for double opt-in
    GDPR: Explicit consent required
    """
    try:
        connection_string = os.getenv('AZURE_COMMUNICATION_CONNECTION_STRING')
        sender_email = os.getenv('EMAIL_SENDER')
        
        if not connection_string or not sender_email:
            logging.error("Email configuration missing")
            return False
        
        email_client = EmailClient.from_connection_string(connection_string)
        
        # Confirmation URL (update domain to your actual Streamlit URL)
        # For local testing: http://localhost:8501/?confirm=...
        # For production: https://your-domain.com/?confirm=...
        confirmation_url = f"http://localhost:8501/?confirm={confirmation_token}&email={email}"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #000000;
            background-color: #ffffff;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 30px;
            border: 1px solid #cccccc;
        }}
        h1 {{
            color: #000000;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background-color: #0066cc;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #cccccc;
            font-size: 12px;
            color: #666666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Confirm Your Subscription</h1>
        
        <p>Thank you for subscribing to the AI Trend Monitor newsletter!</p>
        
        <p>To complete your subscription and start receiving weekly AI news digests, please confirm your email address by clicking the button below:</p>
        
        <p style="text-align: center;">
            <a href="{confirmation_url}" class="button">Confirm Subscription</a>
        </p>
        
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #0066cc;">{confirmation_url}</p>
        
        <p><strong>This link will expire in 48 hours.</strong></p>
        
        <p>If you didn't sign up for this newsletter, you can safely ignore this email.</p>
        
        <div class="footer">
            <p><strong>Your Privacy Rights (GDPR)</strong></p>
            <p>We only send newsletters to subscribers who explicitly confirm their email address. Your email will only be used for this newsletter and will never be shared with third parties.</p>
            <p>You can unsubscribe at any time using the link at the bottom of every newsletter.</p>
            <p><strong>Data Storage:</strong> Your email address is stored securely in Microsoft Azure (Sweden region) and will be deleted immediately upon unsubscription if you request it.</p>
        </div>
    </div>
</body>
</html>
"""
        
        message = {
            "senderAddress": f"AI Trend Monitor <{sender_email}>",
            "recipients": {
                "to": [{"address": email}]
            },
            "content": {
                "subject": "Confirm your AI Trend Monitor subscription",
                "html": html_content
            }
        }
        
        poller = email_client.begin_send(message)
        result = poller.result()
        
        logging.info(f"Confirmation email sent to {email}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending confirmation email: {str(e)}")
        return False


def send_welcome_email(email: str, unsubscribe_token: str) -> bool:
    """
    Send welcome email after successful confirmation
    """
    try:
        connection_string = os.getenv('AZURE_COMMUNICATION_CONNECTION_STRING')
        sender_email = os.getenv('EMAIL_SENDER')
        
        if not connection_string or not sender_email:
            return False
        
        email_client = EmailClient.from_connection_string(connection_string)
        
        unsubscribe_url = f"http://localhost:8501/?unsubscribe={unsubscribe_token}&email={email}"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #000000;
            background-color: #ffffff;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 30px;
        }}
        h1 {{
            color: #000000;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #cccccc;
            font-size: 12px;
            color: #666666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to AI Trend Monitor!</h1>
        
        <p>Your subscription is now confirmed. Thank you for joining!</p>
        
        <p><strong>What to expect:</strong></p>
        <ul>
            <li>Weekly digest every Friday morning</li>
            <li>AI news from top sources (The Guardian, VentureBeat, TechCrunch, and more)</li>
            <li>Focus on AI development, models, and research</li>
            <li>No spam, no ads, just quality content</li>
        </ul>
        
        <p>Your first newsletter will arrive next Friday at 9:00 AM UTC (10:00 AM CET / 11:00 AM CEST).</p>
        
        <div class="footer">
            <p>You can unsubscribe at any time by clicking <a href="{unsubscribe_url}">this link</a>.</p>
            <p><strong>GDPR Notice:</strong> Your data is stored securely in Azure (Sweden). We only use your email for this newsletter. You have the right to access, correct, or delete your data at any time.</p>
        </div>
    </div>
</body>
</html>
"""
        
        message = {
            "senderAddress": f"AI Trend Monitor <{sender_email}>",
            "recipients": {
                "to": [{"address": email}]
            },
            "content": {
                "subject": "Welcome to AI Trend Monitor!",
                "html": html_content
            }
        }
        
        poller = email_client.begin_send(message)
        result = poller.result()
        
        logging.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logging.error(f"Error sending welcome email: {str(e)}")
        return False
