"""
AI Trend Monitor - Interactive Dashboard
A Streamlit web application for exploring AI news trends
"""

import streamlit as st
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from datetime import datetime
from collections import Counter
from wordcloud import WordCloud
from scipy import stats

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag_chatbot import RAGChatbot

# Load environment variables from .env file (local development)
load_dotenv()

# Helper function to get environment variables (supports both .env and Streamlit secrets)
def get_env_var(key: str, default=None):
    """Get environment variable from .env, Streamlit secrets, or Azure App Settings"""
    try:
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

# AI Trend Monitor custom color palette
AITREND_COLOURS = {
    'primary': '#C17D3D',
    'secondary': '#A0917A',
    'accent': '#5D5346',
    'positive': '#5B8FA3',
    'neutral': '#9C8E7A',
    'negative': '#C17D3D',
    'mixed': '#7B6B8F',
    'background': '#F5F3EF',
    'text': '#2D2D2D'
}

# Set seaborn style with AI Trend Monitor theme
sns.set_theme(style="whitegrid", palette=[
    AITREND_COLOURS['primary'], 
    AITREND_COLOURS['secondary'], 
    AITREND_COLOURS['accent'],
    AITREND_COLOURS['positive'],
    AITREND_COLOURS['neutral']
])
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#FEFEFE'
plt.rcParams['text.color'] = AITREND_COLOURS['text']
plt.rcParams['axes.labelcolor'] = AITREND_COLOURS['text']
plt.rcParams['xtick.color'] = AITREND_COLOURS['text']
plt.rcParams['ytick.color'] = AITREND_COLOURS['text']

# Page configuration
st.set_page_config(
    page_title="AI Trend Monitor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Azure AI Search client
@st.cache_resource
def get_search_client():
    """Initialize and cache the Azure Search client"""
    search_endpoint = get_env_var('SEARCH_ENDPOINT')
    search_key = get_env_var('SEARCH_KEY')
    index_name = 'ai-articles-index'
    
    if not search_endpoint or not search_key:
        st.error("⚠️ Azure Search credentials not found. Please check your .env file or Streamlit secrets.")
        st.info("""
        **Required configuration:**
        - `SEARCH_ENDPOINT`: Your Azure AI Search endpoint URL
        - `SEARCH_KEY`: Your Azure AI Search admin key
        
        **For local development:** Add these to `.env` file
        **For Azure deployment:** Configure in App Service → Configuration → Application Settings
        """)
        return None
    
    return SearchClient(
        endpoint=search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(search_key)
    )

def search_articles(query_text, source_filter=None, sentiment_filter=None, top=20):
    """Search articles with optional filters"""
    search_client = get_search_client()
    if not search_client:
        return []
    
    filters = []
    if source_filter and source_filter != "All Sources":
        filters.append(f"source eq '{source_filter}'")
    if sentiment_filter and sentiment_filter != "All Sentiments":
        filters.append(f"sentiment_overall eq '{sentiment_filter}'")
    
    filter_string = " and ".join(filters) if filters else None
    
    try:
        results = search_client.search(
            search_text=query_text if query_text else "*",
            filter=filter_string,
            select=["title", "content", "link", "source", "published_date", 
                   "sentiment_overall", "sentiment_positive_score", 
                   "sentiment_neutral_score", "sentiment_negative_score",
                   "key_phrases", "entities", "indexed_at"],
            top=top
        )
        return list(results)
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []

def get_all_articles():
    """Retrieve all articles filtered to June 1, 2025 onwards"""
    from dateutil import parser as date_parser
    
    all_articles = search_articles("*", top=1000)
    cutoff_date = datetime(2025, 6, 1)
    
    filtered_articles = []
    for article in all_articles:
        date_str = article.get('published_date', '')
        if date_str:
            try:
                article_date = date_parser.parse(date_str)
                if article_date.tzinfo:
                    article_date = article_date.replace(tzinfo=None)
                if article_date >= cutoff_date:
                    filtered_articles.append(article)
            except:
                pass
    
    return filtered_articles

def display_article_card(article):
    """Display a single article in a card format"""
    sentiment = article.get('sentiment_overall', 'neutral')
    sentiment_emoji = {
        'positive': '✨',
        'neutral': '�',
        'negative': '⚠️',
        'mixed': '�'
    }
    
    sentiment_colors = {
        'positive': AITREND_COLOURS['positive'],
        'neutral': AITREND_COLOURS['neutral'],
        'negative': AITREND_COLOURS['negative'],
        'mixed': AITREND_COLOURS['mixed']
    }
    
    with st.container():
        st.markdown(f"### {article['title']}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
        with col2:
            sentiment_color = sentiment_colors.get(sentiment, AITREND_COLOURS['neutral'])
            st.markdown(
                f"**Sentiment:** {sentiment_emoji.get(sentiment, '�')} "
                f"<span style='color: {sentiment_color}; font-weight: 600;'>{sentiment.title()}</span>",
                unsafe_allow_html=True
            )
        with col3:
            date_str = article.get('published_date', 'Unknown')
            if date_str != 'Unknown':
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    st.markdown(f"**Date:** {date_obj.strftime('%Y-%m-%d')}")
                except:
                    st.markdown(f"**Date:** {date_str}")
            else:
                st.markdown(f"**Date:** Unknown")
        
        content = article.get('content', '')
        # Escape dollar signs to prevent LaTeX rendering issues
        content = content.replace('$', r'\$')
        if len(content) > 300:
            st.markdown(f"{content[:300]}...")
        else:
            st.markdown(content)
        
        key_phrases = article.get('key_phrases', [])
        if key_phrases:
            st.markdown(f"**Key Topics:** {', '.join(key_phrases[:5])}")
        
        st.markdown(f"[Read Full Article]({article['link']})")
        st.markdown("---")

def get_responsive_figsize(base_width, base_height, container_fraction=1.0):
    """Return original figure size - CSS handles responsive scaling"""
    return (base_width, base_height)

def show_subscribe_page():
    """Newsletter subscription page with GDPR compliance"""
    from src.subscriber_manager import SubscriberManager
    from src.confirmation_email import send_confirmation_email, send_welcome_email
    
    st.header("Subscribe to Newsletter")
    
    # Handle URL parameters for confirmation/unsubscribe
    query_params = st.query_params
    
    # Handle confirmation
    if 'confirm' in query_params and 'email' in query_params:
        confirmation_token = query_params['confirm']
        email = query_params['email']
        
        try:
            manager = SubscriberManager()
            success = manager.confirm_subscription(email, confirmation_token)
            
            if success:
                st.success("**Subscription Confirmed!**")
                st.balloons()
                st.markdown("""
                Thank you for confirming your subscription to the AI Trend Monitor newsletter!
                
                **What happens next:**
                - You'll receive your first newsletter next Friday at 9:00 AM UTC
                - Weekly digests covering AI news, research, and developments
                - You can unsubscribe anytime using the link in each email
                """)
                
                # Send welcome email
                subscriber = manager.get_subscriber(email)
                if subscriber:
                    send_welcome_email(email, subscriber.get('unsubscribe_token', ''))
            else:
                st.error("Invalid or expired confirmation link.")
                st.info("Please try subscribing again or contact support if the problem persists.")
        except Exception as e:
            st.error(f"Error confirming subscription: {str(e)}")
        
        # Clear query params
        st.query_params.clear()
        return
    
    # Handle unsubscribe
    if 'unsubscribe' in query_params and 'email' in query_params:
        unsubscribe_token = query_params['unsubscribe']
        email = query_params['email']
        
        try:
            manager = SubscriberManager()
            success = manager.unsubscribe(email, unsubscribe_token)
            
            if success:
                st.success("**Unsubscribed Successfully**")
                st.markdown("""
                You have been unsubscribed from the AI Trend Monitor newsletter.
                
                We're sorry to see you go! If you change your mind, you can always subscribe again.
                
                **Your Data Rights (GDPR):**
                - Your email is now marked as inactive
                - You can request complete data deletion below
                """)
                
                # Offer complete data deletion
                if st.button("Delete My Data Completely (GDPR Right to Erasure)"):
                    if manager.delete_subscriber(email):
                        st.success("All your data has been permanently deleted from our systems.")
                    else:
                        st.error("Error deleting data. Please contact support.")
            else:
                st.error("Invalid unsubscribe link.")
        except Exception as e:
            st.error(f"Error unsubscribing: {str(e)}")
        
        # Clear query params
        st.query_params.clear()
        return
    
    # Normal subscription form
    st.markdown("""
    Stay updated with the latest AI trends, research, and developments delivered to your inbox every Friday.
    
    **What you'll get:**
    - Weekly digest of AI news from trusted sources
    - Focus on AI development, models, and research
    - Analysis of trends and key developments
    - No spam, no ads, just quality content
    
    ---
    """)
    
    # Subscription form
    with st.form("subscribe_form"):
        email = st.text_input(
            "Email Address",
            placeholder="your.email@example.com",
            help="We'll send you a confirmation email"
        )
        
        st.markdown("### GDPR Consent")
        gdpr_consent = st.checkbox(
            "I consent to receiving the AI Trend Monitor newsletter and understand that:",
            help="Required for GDPR compliance"
        )
        
        with st.expander("Read Full Privacy Notice"):
            st.markdown("""
            **Data Controller:** AI Trend Monitor
            
            **Data Stored:**
            - Your email address
            - Subscription date and confirmation timestamp
            - Email delivery status (for technical purposes only)
            
            **Data Location:** Microsoft Azure, Sweden region
            
            **Purpose:** Sending weekly AI news digest newsletter
            
            **Legal Basis:** Consent (GDPR Art. 6(1)(a))
            
            **Your Rights:**
            - Right to access your data
            - Right to rectification (correct your email)
            - Right to erasure (be forgotten)
            - Right to withdraw consent (unsubscribe)
            - Right to data portability
            - Right to object
            
            **Data Retention:**
            - Active subscriptions: Indefinitely while subscription is active
            - After unsubscribe: Email kept as "inactive" unless you request deletion
            - Complete deletion: Available on request (GDPR right to erasure)
            
            **Data Sharing:** We never share your email with third parties
            
            **Security:** Data encrypted at rest and in transit using Azure security standards
            
            **Contact:** For data requests, email support via the About page
            """)
        
        submitted = st.form_submit_button("Subscribe", type="primary")
        
        if submitted:
            if not email:
                st.error("Please enter your email address")
            elif '@' not in email or '.' not in email:
                st.error("Please enter a valid email address")
            elif not gdpr_consent:
                st.error("You must consent to receiving the newsletter (GDPR requirement)")
            else:
                try:
                    manager = SubscriberManager()
                    result = manager.create_subscription(email)
                    
                    if result['success']:
                        # Send confirmation email
                        email_sent = send_confirmation_email(
                            email,
                            result['confirmation_token']
                        )
                        
                        if email_sent:
                            st.success("**Subscription Initiated!**")
                            st.info(f"""
                            **Next Step:** Please check your email inbox at `{email}`
                            
                            We've sent you a confirmation email with a link to complete your subscription.
                            
                            **Note:** The confirmation link expires in 48 hours.
                            
                            *If you don't see the email, please check your spam/junk folder.*
                            """)
                        else:
                            st.error("Error sending confirmation email. Please try again later.")
                    else:
                        # Check if this is a pending confirmation
                        if 'already sent' in result['message'].lower():
                            st.warning(result['message'])
                            # Store email in session state to show resend button outside form
                            st.session_state['pending_email'] = email
                        else:
                            st.warning(result['message'])
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Please try again later or contact support.")
    
    # Resend confirmation button (outside form)
    if 'pending_email' in st.session_state:
        st.info("**Didn't receive the confirmation email?**")
        if st.button("Resend Confirmation Email", key="resend_conf"):
            try:
                manager = SubscriberManager()
                resend_result = manager.resend_confirmation(st.session_state['pending_email'])
                if resend_result['success']:
                    st.success(resend_result['message'])
                    # Clear the session state
                    del st.session_state['pending_email']
                else:
                    st.error(resend_result['message'])
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Subscriber statistics (admin view - optional)
    with st.expander("Subscriber Statistics", expanded=False):
        try:
            manager = SubscriberManager()
            stats = manager.get_subscriber_count()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Subscribers", stats['total'])
            col2.metric("Active", stats['active'])
            col3.metric("Pending Confirmation", stats['pending'])
            col4.metric("Unsubscribed", stats['unsubscribed'])
        except Exception as e:
            st.info("Statistics not available")

def main():
    """Main application"""
    
    # Load custom CSS from external file
    css_file = Path(__file__).parent / "styles.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Hide sidebar completely and reduce header spacing
    st.html("""
    <style>
    [data-testid="stSidebar"] {
        display: none;
    }
    .main .block-container {
        padding-left: 3rem !important;
        padding-top: 0rem !important;
    }
    /* Remove extra space above first element */
    .main .block-container > div:first-child {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    /* Compact title spacing */
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.25rem !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0 !important;
    }
    /* Compact paragraph spacing after title */
    h1 + div p {
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
    }
    /* Reduce hr spacing */
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 1rem !important;
    }
    </style>
    """)
    
    # Add site title and subtitle at the top
    st.title("AI Trend Monitor")
    st.markdown("*Exploring AI news trends with advanced analytics and search*")
    st.markdown("---")
    
    # Define pages for navigation
    news_page = st.Page(show_news_page, title="News")
    analytics_page = st.Page(show_analytics_page, title="Analytics")
    chatbot_page = st.Page(show_chatbot_page, title="Chatbot")
    subscribe_page = st.Page(show_subscribe_page, title="Subscribe")
    about_page = st.Page(show_about_page, title="About")
    
    # Create navigation at top
    pg = st.navigation([news_page, analytics_page, chatbot_page, subscribe_page, about_page], position="top")
    
    # Run the selected page
    pg.run()

def show_news_page():
    """News page with search and curated sections"""
    st.header("AI News & Updates")
    
    col_curated, col_search = st.columns([1.6, 1], gap="medium")
    
    with col_curated:
        show_curated_sections()
    
    with col_search:
        st.subheader("Search Articles")
        show_search_interface()

def show_search_interface():
    """Search interface component"""
    
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    if 'last_source' not in st.session_state:
        st.session_state.last_source = "All Sources"
    if 'last_sentiment' not in st.session_state:
        st.session_state.last_sentiment = "All Sentiments"
    
    query = st.text_input(
        "Search keywords",
        placeholder="e.g., machine learning, ChatGPT, AI ethics...",
        help="Enter keywords to search articles"
    )
    
    sources = ["All Sources", "The Guardian", "techcrunch.com", "venturebeat.com", 
              "arstechnica.com", "gizmodo.com", "spectrum.ieee.org", "www.theregister.com",
              "www.theverge.com", "www.eu-startups.com"]
    source_filter = st.selectbox("Source", sources, key="search_source")
    
    sentiments = ["All Sentiments", "positive", "neutral", "negative", "mixed"]
    sentiment_filter = st.selectbox("Sentiment", sentiments, key="search_sentiment")
    
    date_ranges = ["All Time", "Last 7 days", "Last 30 days", "Last 90 days", "Last 6 months", "Last year"]
    date_filter = st.selectbox("Date Range", date_ranges, key="search_date")
    
    if 'last_date_filter' not in st.session_state:
        st.session_state.last_date_filter = "All Time"
    
    if (query != st.session_state.last_query or 
        source_filter != st.session_state.last_source or 
        sentiment_filter != st.session_state.last_sentiment or
        date_filter != st.session_state.last_date_filter):
        st.session_state.page_number = 0
        st.session_state.last_query = query
        st.session_state.last_source = source_filter
        st.session_state.last_sentiment = sentiment_filter
        st.session_state.last_date_filter = date_filter
    
    if st.button("Search", type="primary") or query:
        with st.spinner("Searching articles..."):
            results = search_articles(
                query if query else "*",
                source_filter=source_filter if source_filter != "All Sources" else None,
                sentiment_filter=sentiment_filter if sentiment_filter != "All Sentiments" else None
            )
            
            if results:
                # Sort by date (newest first) - parse dates properly
                from datetime import timezone, timedelta
                from email.utils import parsedate_to_datetime
                
                def parse_date(article):
                    date_str = article.get('published_date', '')
                    if not date_str:
                        return datetime.min.replace(tzinfo=timezone.utc)  # Make timezone-aware
                    try:
                        # Try ISO format first
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        # Ensure timezone-aware
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt
                    except:
                        try:
                            # Try RFC 2822 format (e.g., "Tue, 14 Oct 2025 15:32:23 +0000")
                            dt = parsedate_to_datetime(date_str)
                            return dt
                        except:
                            return datetime.min.replace(tzinfo=timezone.utc)
                
                # Apply date filter
                if date_filter != "All Time":
                    now = datetime.now(timezone.utc)
                    if date_filter == "Last 7 days":
                        cutoff_date = now - timedelta(days=7)
                    elif date_filter == "Last 30 days":
                        cutoff_date = now - timedelta(days=30)
                    elif date_filter == "Last 90 days":
                        cutoff_date = now - timedelta(days=90)
                    elif date_filter == "Last 6 months":
                        cutoff_date = now - timedelta(days=180)
                    elif date_filter == "Last year":
                        cutoff_date = now - timedelta(days=365)
                    
                    results = [article for article in results if parse_date(article) >= cutoff_date]
                
                results_sorted = sorted(results, key=parse_date, reverse=True)
                
                # Pagination
                items_per_page = 10
                total_pages = (len(results_sorted) + items_per_page - 1) // items_per_page
                start_idx = st.session_state.page_number * items_per_page
                end_idx = start_idx + items_per_page
                
                st.markdown(f"**Found {len(results_sorted)} articles** (Page {st.session_state.page_number + 1} of {total_pages})")
                
                # Pagination controls at top
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.session_state.page_number > 0:
                            if st.button("← Previous", key="prev_top"):
                                st.session_state.page_number -= 1
                                st.rerun()
                    with col2:
                        st.markdown(f"<p style='text-align: center;'>Page {st.session_state.page_number + 1} of {total_pages}</p>", unsafe_allow_html=True)
                    with col3:
                        if st.session_state.page_number < total_pages - 1:
                            if st.button("Next →", key="next_top"):
                                st.session_state.page_number += 1
                                st.rerun()
                
                st.markdown("---")
                
                # Display results for current page
                for article in results_sorted[start_idx:end_idx]:
                    display_article_card_compact(article)
                
                # Pagination controls at bottom
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.session_state.page_number > 0:
                            if st.button("← Previous", key="prev_bottom"):
                                st.session_state.page_number -= 1
                                st.rerun()
                    with col2:
                        st.markdown(f"<p style='text-align: center;'>Page {st.session_state.page_number + 1} of {total_pages}</p>", unsafe_allow_html=True)
                    with col3:
                        if st.session_state.page_number < total_pages - 1:
                            if st.button("Next →", key="next_bottom"):
                                st.session_state.page_number += 1
                                st.rerun()
            else:
                st.info("No articles found. Try different search terms or filters.")

def display_article_card_compact(article):
    """Display a compact version of an article card for the news page"""
    sentiment = article.get('sentiment_overall', 'neutral')
    sentiment_emoji = {
        'positive': '😊',
        'negative': '😟',
        'neutral': '😐',
        'mixed': '🤔'
    }
    
    sentiment_colors = {
        'positive': AITREND_COLOURS['positive'],
        'neutral': AITREND_COLOURS['neutral'],
        'negative': AITREND_COLOURS['negative'],
        'mixed': AITREND_COLOURS['mixed']
    }
    
    with st.container():
        st.markdown(f"**{article['title']}**")
        
        # Three columns: source, date, sentiment
        col1, col2, col3 = st.columns([2, 1.5, 1.5])
        with col1:
            st.markdown(f"*{article.get('source', 'Unknown')}*", unsafe_allow_html=True)
        with col2:
            # Format date
            from email.utils import parsedate_to_datetime
            import platform
            date_str = article.get('published_date', 'Unknown')
            if date_str != 'Unknown':
                try:
                    # Try ISO format first
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # Format as "January 5, 2025" (full month, no leading zero on day)
                    # Windows uses %#d, Unix uses %-d
                    day_format = '%#d' if platform.system() == 'Windows' else '%-d'
                    formatted_date = date_obj.strftime(f'%B {day_format}, %Y')
                    st.markdown(f"*{formatted_date}*")
                except:
                    try:
                        # Try RFC 2822 format
                        date_obj = parsedate_to_datetime(date_str)
                        day_format = '%#d' if platform.system() == 'Windows' else '%-d'
                        formatted_date = date_obj.strftime(f'%B {day_format}, %Y')
                        st.markdown(f"*{formatted_date}*")
                    except:
                        st.markdown(f"*{date_str}*")
            else:
                st.markdown("*Date unknown*")
        with col3:
            sentiment_color = sentiment_colors.get(sentiment, AITREND_COLOURS['neutral'])
            st.markdown(
                f"<span style='color: {sentiment_color}; font-weight: 600;'>{sentiment_emoji.get(sentiment, '📰')} {sentiment.title()}</span>",
                unsafe_allow_html=True
            )
        
        # Content preview
        content = article.get('content', '')
        # Escape dollar signs to prevent LaTeX rendering issues
        content = content.replace('$', r'\$')
        if len(content) > 400:
            st.markdown(f"{content[:400]}...")
        else:
            st.markdown(content)
        
        st.markdown(f"[Read More]({article['link']})")
        st.markdown("---")

@st.cache_data(ttl=604800)  # Cache for 7 days (weekly refresh on Fridays)
def generate_curated_content(section_type):
    """Generate curated content using RAG chatbot with AI-specific search"""
    from datetime import datetime
    from dateutil import parser as date_parser
    import re
    
    try:
        chatbot = RAGChatbot()
        current_date = datetime.now()
        
        # Use targeted AI keywords to filter at retrieval level
        ai_search_override = "GPT ChatGPT Claude LLM model OpenAI Anthropic machine learning neural network deep learning generative AI"
        
        if section_type == "products":
            # Focus on software, models, tools, APIs
            query = """What are the most recent AI SOFTWARE and MODEL developments mentioned in the articles?

STRICT RULES - Only include if it's about:
- AI models (GPT-5, Claude 4, Gemini updates, new LLMs, model releases)
- AI/ML software tools (ChatGPT features, API updates, ML libraries, frameworks)
- Generative AI applications (image/video/audio generation tools)
- AI development platforms (ML platforms, AI SDKs, developer tools)
- AI model capabilities (new features, performance improvements, fine-tuning)

DO NOT include:
- General business news or company announcements without product details
- AI hardware or chips (save for industry section)
- Funding or investment news without product specifics
- Regulatory or policy news
- Generic tech products

List 5 SOFTWARE/MODEL items in this format:
<li><strong>Product/Model Name:</strong> Brief description of the software or model update</li>

Focus on practical AI tools and models that developers and practitioners use."""
            temperature = 0.5
        else:  # industry
            # Focus on companies, funding, regulations, research
            query = """What are the most recent AI INDUSTRY developments mentioned in the articles?

STRICT RULES - Only include if it's about:
- AI company news (OpenAI, Anthropic, Google AI, DeepMind, etc.)
- AI startup funding, acquisitions, or launches
- AI research breakthroughs or academic papers
- AI regulation, policy, or ethics discussions
- AI chip/hardware manufacturers (NVIDIA, AMD, specialized AI chips)
- Major AI partnerships or collaborations

DO NOT include:
- Specific software or model releases (save for products section)
- General tech news unrelated to AI
- Consumer electronics or vehicles
- Business news from non-AI companies

List 5 INDUSTRY items in this format:
<li><strong>Company/Topic:</strong> Brief description of the industry development</li>

Focus on the AI ecosystem: who's doing what, funding, regulations, and research."""
            temperature = 0.5
        
        # Force specific AI search terms for retrieval (override default broad search)
        result = chatbot.chat(query, top_k=15, temperature=temperature, search_override=ai_search_override)
        
        # Clean up the response
        answer = result["answer"]
        
        # Remove unwanted phrases
        unwanted_phrases = [
            "Based on the provided articles,",
            "here are 5",
            "here are five", 
            "Here are 5",
            "Here are five",
            "Based on the articles,",
            "According to the articles,",
            "```html",
            "```"
        ]
        for phrase in unwanted_phrases:
            answer = answer.replace(phrase, "")
        
        # Remove article citations like [1], [2], [1][2], etc.
        answer = re.sub(r'\s*\[\d+\](\[\d+\])*', '', answer)
        
        # Clean up markdown-style lists (- or *) and convert to HTML if needed
        lines = answer.strip().split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # If line starts with - or *, convert to <li>
                if line.startswith('-') or line.startswith('*'):
                    line = line[1:].strip()
                    if not line.startswith('<li>'):
                        line = f'<li>{line}</li>'
                cleaned_lines.append(line)
        
        answer = '\n'.join(cleaned_lines)
        
        # Wrap in <ul> tags if not already present
        if '<li>' in answer and not answer.strip().startswith('<ul>'):
            answer = f'<ul style="margin-top: 0.5rem; color: #2D2D2D;">\n{answer}\n</ul>'
        
        return answer.strip()
    except Exception as e:
        return None

def show_curated_sections():
    """Display curated 'New' and 'Upcoming' sections with AI-generated content"""
    
    # Add cache clearing button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Refresh", help="Clear cache and regenerate content"):
            generate_curated_content.clear()
            st.rerun()
    
    # AI Products & Models Section
    st.subheader("AI Products & Models")
    
    with st.spinner("Generating AI product and model updates..."):
        products_content = generate_curated_content("products")
    
    if products_content:
        st.markdown(f"""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        {products_content}
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Generated from indexed articles</em></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to static content if generation fails
        st.markdown("""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <ul style='margin-top: 0.5rem; color: #2D2D2D;'>
        <li><strong>ChatGPT Canvas:</strong> OpenAI launches collaborative workspace for writing and coding with AI</li>
        <li><strong>Claude 3.5 Sonnet Updated:</strong> Anthropic releases improved version with better coding capabilities</li>
        <li><strong>Meta Movie Gen:</strong> Meta unveils AI video generation model competing with Runway and Pika</li>
        <li><strong>NotebookLM Audio Overview:</strong> Google's AI podcast feature generates conversational summaries from documents</li>
        <li><strong>OpenAI Advanced Voice Mode:</strong> Rolled out to Plus and Team users with improved natural conversation</li>
        </ul>
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Updated October 2025</em></p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # AI Industry News Section
    st.subheader("AI Industry News")
    
    with st.spinner("Generating AI industry updates..."):
        industry_content = generate_curated_content("industry")
    
    if industry_content:
        st.markdown(f"""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        {industry_content}
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Generated from indexed articles</em></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to static content if generation fails
        st.markdown("""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <ul style='margin-top: 0.5rem; color: #2D2D2D;'>
        <li><strong>OpenAI:</strong> Reportedly raising funds at $150B valuation, restructuring as for-profit company</li>
        <li><strong>Anthropic:</strong> Secures additional funding from Google and Amazon for Claude development</li>
        <li><strong>EU AI Act:</strong> First comprehensive AI regulation framework takes effect, setting global precedent</li>
        <li><strong>NVIDIA:</strong> Announces next-generation AI chips with improved efficiency for large language models</li>
        <li><strong>AI Research:</strong> New benchmarks show rapid progress in mathematical reasoning and code generation</li>
        </ul>
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Based on industry announcements and trends</em></p>
        </div>
        """, unsafe_allow_html=True)

def show_analytics_page():
    """Analytics and visualizations page"""
    st.header("AI News Analytics")
    
    with st.spinner("Loading analytics data..."):
        articles = get_all_articles()
    
    if not articles:
        st.warning("No data available for analytics.")
        return
    
    # Convert to DataFrame for easier analysis
    df_data = []
    for article in articles:
        # Extract meaningful entity names (filtering for key categories)
        entities = article.get('entities', [])
        meaningful_categories = ['Organization', 'Person', 'Product', 'Location', 'Event', 'Skill']
        entity_names = []
        
        # Debug: Check what we're getting
        if entities:
            # If entities is a string (JSON), try to parse it
            if isinstance(entities, str):
                try:
                    import json
                    entities = json.loads(entities)
                except:
                    entities = []
            
            if isinstance(entities, list):
                for entity in entities:
                    # Check if entity is a dict (proper format)
                    if isinstance(entity, dict):
                        category = entity.get('category', '')
                        confidence = entity.get('confidence', 0)
                        text = entity.get('text', '')
                        if category in meaningful_categories and confidence > 0.7 and text:
                            entity_names.append(text)
        
        df_data.append({
            'title': article.get('title', ''),
            'source': article.get('source', 'Unknown'),
            'sentiment': article.get('sentiment_overall', 'neutral'),
            'positive_score': article.get('sentiment_positive_score', 0),
            'neutral_score': article.get('sentiment_neutral_score', 0),
            'negative_score': article.get('sentiment_negative_score', 0),
            'published_date': article.get('published_date', ''),
            'indexed_at': article.get('indexed_at', ''),
            'key_phrases': article.get('key_phrases', []),
            'entities': entity_names  # Use filtered entities instead
        })
    
    df = pd.DataFrame(df_data)
    
    # Calculate date ranges
    df['date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce')
    df['indexed_at_parsed'] = pd.to_datetime(df['indexed_at'], errors='coerce')
    df['date_final'] = df['date_parsed'].fillna(df['indexed_at_parsed'])
    min_date = df['date_final'].min().strftime('%b %d, %Y')
    max_date = df['date_final'].max().strftime('%b %d, %Y')
    
    # Calculate average net sentiment
    df['net_sentiment'] = df['positive_score'] - df['negative_score']
    avg_net_sentiment = df['net_sentiment'].mean()
    delta_label = "Positive lean" if avg_net_sentiment > 0 else "Negative lean" if avg_net_sentiment < 0 else "Neutral"
    
    # Statistics at the top in columns
    st.markdown(f"**Analyzing {len(articles)} articles**")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Articles", len(df))
    with col2:
        st.metric("Data Sources", df['source'].nunique())
    with col3:
        st.metric("Earliest Article", min_date)
    with col4:
        st.metric("Latest Article", max_date)
    with col5:
        st.metric("Avg Net Sentiment", f"{avg_net_sentiment:.3f} ({delta_label})")
    
    st.markdown("---")
    
    # Topic Trend Timeline
    st.subheader("Topic Trend Timeline")
    
    # Get all unique entities and their frequencies
    all_unique_entities = []
    for entities in df['entities']:
        if entities:
            all_unique_entities.extend(entities)
    
    # Fall back to key phrases if no entities
    use_entities = bool(all_unique_entities)
    
    if all_unique_entities:
        # Get top 100 most common entities
        entity_counts = Counter(all_unique_entities)
        top_100_entities = [entity for entity, count in entity_counts.most_common(100)]
        
        # Description
        if not all_unique_entities:
            for phrases in df['key_phrases']:
                if phrases:
                    all_unique_entities.extend(phrases)
            st.markdown("""
            Track how frequently a topic (key phrase) is mentioned over time and how sentiment changes. 
            Select a topic to see its article volume and average sentiment trend.
            """)
        else:
            st.markdown("""
            Track how frequently an entity (organization, person, product, location) is mentioned over time and how sentiment changes. 
            Select an entity to see its article volume and average sentiment trend.
            """)
        
        # Initialize reset counter for forcing text input to clear
        if 'entity_reset_counter' not in st.session_state:
            st.session_state.entity_reset_counter = 0
        
        # Create columns: selection controls, viz mode, date range, and reset button on two rows
        # Row 1: Entity selection and search
        col_select1, col_select2 = st.columns([1.8, 1.2], gap="small")
        
        with col_select1:
            # Dropdown with top 100 entities - use key for state persistence
            # Get the current widget key
            dropdown_key = f"entity_dropdown_{st.session_state.entity_reset_counter}"
            
            # Determine default index: use widget state if it exists, otherwise 0
            if dropdown_key in st.session_state:
                default_index = top_100_entities.index(st.session_state[dropdown_key]) if st.session_state[dropdown_key] in top_100_entities else 0
            else:
                default_index = 0
            
            selected_from_dropdown = st.selectbox(
                "Select entity",
                options=top_100_entities,
                index=default_index,
                key=dropdown_key
            )
        
        with col_select2:
            # Text input for manual entry - key changes when reset is clicked
            manual_entity = st.text_input(
                "Or search",
                placeholder="e.g., Grok, ChatGPT",
                key=f"entity_manual_input_{st.session_state.entity_reset_counter}"
            )
        
        # Row 2: View mode, date range, and reset button
        col_viz, col_date_range, col_clear = st.columns([1.5, 1.5, 0.5], gap="small")
        
        with col_viz:
            # Visualization mode toggle on same row
            viz_mode = st.selectbox(
                "View mode",
                options=["Weekly", "Daily", "Cumulative"],
                key="topic_viz_mode",
                help="Daily Count, Cumulative Count, or Weekly Aggregation"
            )
            # Map short names to full names
            viz_mode_map = {
                "Daily": "Daily Count",
                "Cumulative": "Cumulative Count",
                "Weekly": "Weekly Aggregation"
            }
            viz_mode = viz_mode_map[viz_mode]
        
        with col_date_range:
            # Date range filter
            date_range_option = st.selectbox(
                "Date range",
                options=["All time", "Last 30 days"],
                key="topic_date_range",
                help="Filter articles by date range"
            )
        
        with col_clear:
            # Add some spacing to align with inputs
            st.write("")
            st.write("")
            if st.button("Reset", help="Clear search and reset"):
                # Increment counter to force widget recreation with new key (resets to index 0)
                st.session_state.entity_reset_counter += 1
                st.rerun()
        
        # Use manual input if provided, otherwise use dropdown selection
        selected_entity = manual_entity.strip() if manual_entity.strip() else selected_from_dropdown
        
        # Use Azure AI Search to find articles containing the selected entity/topic
        # This searches across all fields (title, content, entities, key_phrases)
        search_results = search_articles(selected_entity, top=1000)
        
        # Apply date filter: June 1, 2025 onwards
        from dateutil import parser as date_parser
        cutoff_date = datetime(2025, 6, 1)
        
        filtered_results = []
        for article in search_results:
            date_str = article.get('published_date', '')
            if date_str:
                try:
                    article_date = date_parser.parse(date_str)
                    if article_date.tzinfo:
                        article_date = article_date.replace(tzinfo=None)
                    if article_date >= cutoff_date:
                        filtered_results.append(article)
                except:
                    pass
        
        search_results = filtered_results
        
        if search_results:
            # Convert search results to DataFrame for analysis
            topic_articles = pd.DataFrame([
                {
                    'title': article.get('title', ''),
                    'published_date': article.get('published_date', ''),
                    'positive_score': article.get('sentiment_positive_score', 0),
                    'negative_score': article.get('sentiment_negative_score', 0),
                    'sentiment': article.get('sentiment_overall', 'neutral'),
                    'source': article.get('source', ''),
                    'link': article.get('link', '')
                }
                for article in search_results
            ])
            
            # Parse dates using the same format_article_date function (without formatting)
            # This handles both RFC and ISO formats properly
            
            def parse_flexible_date(date_str):
                """Parse date string in various formats, returning timezone-naive datetime"""
                if not date_str:
                    return None
                try:
                    # Use dateutil parser which handles multiple formats
                    parsed = date_parser.parse(date_str)
                    # Remove timezone info to make it timezone-naive for pandas
                    if parsed.tzinfo is not None:
                        parsed = parsed.replace(tzinfo=None)
                    return parsed
                except:
                    return None
            
            topic_articles['date'] = topic_articles['published_date'].apply(parse_flexible_date)
            topic_articles = topic_articles.dropna(subset=['date'])
            # Ensure the date column is datetime type before using .dt accessor
            topic_articles['date'] = pd.to_datetime(topic_articles['date'], utc=False)
            topic_articles['date_only'] = topic_articles['date'].dt.date
        else:
            topic_articles = pd.DataFrame()
        
        if len(topic_articles) > 0:
            # Sort by date for proper chronological display
            topic_articles = topic_articles.sort_values('date')
            
            # Apply date range filter
            if date_range_option == "Last 30 days":
                cutoff_date_30 = datetime.now() - pd.Timedelta(days=30)
                topic_articles = topic_articles[topic_articles['date'] >= cutoff_date_30]
            
            # Check if we still have articles after filtering
            if len(topic_articles) == 0:
                st.info(f"No articles found for '{selected_entity}' in the selected date range.")
            else:
                # Prepare data based on visualization mode
                if viz_mode == "Daily Count":
                    # Group by date for daily article count and average sentiment
                    daily_stats = topic_articles.groupby('date_only').agg({
                        'title': 'count',
                        'positive_score': 'mean',
                        'negative_score': 'mean'
                    }).reset_index()
                    daily_stats.columns = ['date', 'article_count', 'avg_positive', 'avg_negative']
                    daily_stats['net_sentiment'] = daily_stats['avg_positive'] - daily_stats['avg_negative']
                    plot_data = daily_stats
                    count_label = 'Article Count'
                    
                elif viz_mode == "Cumulative Count":
                    # Group by date first, then calculate cumulative sum
                    daily_stats = topic_articles.groupby('date_only').agg({
                        'title': 'count',
                        'positive_score': 'mean',
                        'negative_score': 'mean'
                    }).reset_index()
                    daily_stats.columns = ['date', 'article_count', 'avg_positive', 'avg_negative']
                    daily_stats['article_count'] = daily_stats['article_count'].cumsum()
                    daily_stats['net_sentiment'] = daily_stats['avg_positive'] - daily_stats['avg_negative']
                    plot_data = daily_stats
                    count_label = 'Cumulative Articles'
                    
                elif viz_mode == "Weekly Aggregation":
                    # Add week column
                    topic_articles['week'] = topic_articles['date'].dt.to_period('W').apply(lambda x: x.start_time.date())
                    weekly_stats = topic_articles.groupby('week').agg({
                        'title': 'count',
                        'positive_score': 'mean',
                        'negative_score': 'mean'
                    }).reset_index()
                    weekly_stats.columns = ['date', 'article_count', 'avg_positive', 'avg_negative']
                    weekly_stats['net_sentiment'] = weekly_stats['avg_positive'] - weekly_stats['avg_negative']
                    plot_data = weekly_stats
                    count_label = 'Articles per Week'
                
                # Create Plotly figure with dual y-axes
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Plot 1: Article count (left y-axis) - Line with markers
                fig.add_trace(
                    go.Scatter(
                        x=plot_data['date'], 
                        y=plot_data['article_count'],
                        name=count_label,
                        mode='lines+markers',
                        line=dict(color=AITREND_COLOURS['primary'], width=2.5),
                        marker=dict(
                            size=8, 
                            line=dict(width=1.5, color='white'),
                            color=AITREND_COLOURS['primary']
                        ),
                        hovertemplate='<b>%{x|%b %d, %Y}</b><br>' + count_label + ': %{y}<extra></extra>'
                    ),
                    secondary_y=False
                )
                
                # Plot 2: Net sentiment (right y-axis) - Line with square markers
                fig.add_trace(
                    go.Scatter(
                        x=plot_data['date'],
                        y=plot_data['net_sentiment'],
                        name='Net Sentiment',
                        mode='lines+markers',
                        line=dict(color=AITREND_COLOURS['positive'], width=2.5),
                        marker=dict(
                            size=8, 
                            symbol='square',
                            line=dict(width=1.5, color='white'),
                            color=AITREND_COLOURS['positive']
                        ),
                        hovertemplate='<b>%{x|%b %d, %Y}</b><br>Net Sentiment: %{y:.3f}<extra></extra>'
                    ),
                    secondary_y=True
                )
                
                # Add horizontal line at y=0 for neutral sentiment
                fig.add_hline(
                    y=0, 
                    line_dash="solid", 
                    line_color=AITREND_COLOURS['neutral'], 
                    line_width=2,
                    opacity=0.6,
                    secondary_y=True
                )
                
                # Add shaded regions for positive/negative sentiment (constrained to [-1, 1])
                fig.add_hrect(
                    y0=0, y1=1,
                    fillcolor=AITREND_COLOURS['positive'],
                    opacity=0.05,
                    line_width=0,
                    secondary_y=True
                )
                fig.add_hrect(
                    y0=-1, y1=0,
                    fillcolor=AITREND_COLOURS['negative'],
                    opacity=0.05,
                    line_width=0,
                    secondary_y=True
                )
                
                # Chart title
                mode_text = viz_mode.replace(" Count", "").replace(" Aggregation", "")
                
                # Update layout
                fig.update_layout(
                    title=dict(
                        text=f'Trend: "{selected_entity}" ({mode_text})',
                        font=dict(size=18, color=AITREND_COLOURS['text'], family='Arial, sans-serif'),
                        x=0.5,
                        xanchor='center'
                    ),
                    height=450,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        x=0,
                        font=dict(size=13)
                    ),
                    margin=dict(l=70, r=70, t=90, b=70),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=12,
                        font_family="Arial, sans-serif"
                    )
                )
                
                # Update y-axes
                color_count_dark = '#A05A1F'
                color_sentiment_dark = '#3A6B7A'
                
                # Left y-axis (article count) - force integer ticks with proper spacing
                max_count = plot_data['article_count'].max()
                if max_count <= 5:
                    tick_spacing = 1
                elif max_count <= 10:
                    tick_spacing = 2
                elif max_count <= 20:
                    tick_spacing = 5
                else:
                    tick_spacing = int(max_count / 5)  # ~5 ticks
                
                fig.update_yaxes(
                    title_text=count_label,
                    title_font=dict(size=16, color=color_count_dark),
                    tickfont=dict(size=14, color=color_count_dark),
                    gridcolor='rgba(0,0,0,0.1)',
                    griddash='dot',
                    zeroline=False,
                    rangemode='tozero',
                    dtick=tick_spacing,  # Integer spacing based on data range
                    secondary_y=False
                )
                
                # Right y-axis (sentiment) - constrain to [-1, 1] range
                fig.update_yaxes(
                    title_text="Net Sentiment",
                    title_font=dict(size=16, color=color_sentiment_dark),
                    tickfont=dict(size=14, color=color_sentiment_dark),
                    zeroline=True,
                    zerolinecolor=AITREND_COLOURS['neutral'],
                    zerolinewidth=2,
                    range=[-1, 1],  # Hard limit to logical sentiment range
                    dtick=0.2,  # Show ticks at -1, -0.8, -0.6, ..., 0.8, 1
                    secondary_y=True
                )
                
                # Update x-axis
                fig.update_xaxes(
                    title_text="Publication Date",
                    title_font=dict(size=16, color=AITREND_COLOURS['text']),
                    tickfont=dict(size=14, color=AITREND_COLOURS['text']),
                    tickangle=-45,
                    showgrid=False
                )
                
                # Display the chart
                st.plotly_chart(fig)
                
                # Show summary statistics in single line
                positive_count = (topic_articles['sentiment'] == 'positive').sum()
                positive_pct = (positive_count / len(topic_articles)) * 100
                negative_count = (topic_articles['sentiment'] == 'negative').sum()
                negative_pct = (negative_count / len(topic_articles)) * 100
                date_range = (topic_articles['date'].max() - topic_articles['date'].min()).days
                
                st.markdown(
                    f"**Total Articles:** {len(topic_articles)} &nbsp;|&nbsp; "
                    f"**Positive:** {positive_pct:.1f}% ({positive_count}) &nbsp;|&nbsp; "
                    f"**Negative:** {negative_pct:.1f}% ({negative_count}) &nbsp;|&nbsp; "
                    f"**Date Span:** {date_range} days"
                )
        else:
            st.info(f"No articles found containing the entity '{selected_entity}'")
    
    st.markdown("---")
    
    # Second row: Net Sentiment Distribution
    st.subheader("Net Sentiment Distribution")
    
    # Calculate net sentiment for all articles
    df['net_sentiment'] = df['positive_score'] - df['negative_score']
    
    # Calculate all metrics
    sentiment_counts = df['sentiment'].value_counts()
    total_articles = len(df)
    positive_count = sentiment_counts.get('positive', 0)
    neutral_count = sentiment_counts.get('neutral', 0)
    negative_count = sentiment_counts.get('negative', 0)
    mixed_count = sentiment_counts.get('mixed', 0)
    positive_pct = (positive_count / total_articles) * 100
    neutral_pct = (neutral_count / total_articles) * 100
    negative_pct = (negative_count / total_articles) * 100
    mixed_pct = (mixed_count / total_articles) * 100
    
    leaning_negative = (df['net_sentiment'] < 0).sum()
    leaning_positive = (df['net_sentiment'] > 0).sum()
    leaning_neg_pct = (leaning_negative / total_articles) * 100
    leaning_pos_pct = (leaning_positive / total_articles) * 100
    mean_sentiment = df['net_sentiment'].mean()
    median_sentiment = df['net_sentiment'].median()
    
    st.markdown("""
    This chart shows the overall sentiment spectrum of all articles. The **net sentiment score** is calculated 
    as positive score minus negative score, ranging from **-1 (very negative)** through **0 (neutral)** to **+1 (very positive)**. 
    The distribution shows how articles lean across the sentiment spectrum.
    """)
    
    # Create Plotly histogram with gradient coloring and KDE overlay
    n_bins = 30
    
    # Calculate histogram bins manually to assign colors
    counts, bin_edges = np.histogram(df['net_sentiment'], bins=n_bins, range=(-1, 1))
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_width = bin_edges[1] - bin_edges[0]
    
    # Create color gradient based on bin position (negative=orange, neutral=tan, positive=teal)
    def get_sentiment_color(value):
        """Get color based on sentiment value (-1 to 1)"""
        # Normalize to 0-1 range
        norm_value = (value + 1) / 2
        if norm_value < 0.5:
            # Blend from negative to neutral
            ratio = norm_value * 2
            # Orange to tan
            return f'rgba({int(193 + (156-193)*ratio)}, {int(125 + (142-125)*ratio)}, {int(61 + (122-61)*ratio)}, 0.8)'
        else:
            # Blend from neutral to positive
            ratio = (norm_value - 0.5) * 2
            # Tan to teal
            return f'rgba({int(156 - (156-91)*ratio)}, {int(142 + (143-142)*ratio)}, {int(122 + (163-122)*ratio)}, 0.8)'
    
    bar_colors = [get_sentiment_color(bc) for bc in bin_centers]
    
    # Create figure
    fig = go.Figure()
    
    # Add histogram bars with gradient colors
    fig.add_trace(go.Bar(
        x=bin_centers,
        y=counts,
        width=bin_width * 0.95,
        marker=dict(
            color=bar_colors,
            line=dict(color='white', width=1)
        ),
        hovertemplate='<b>Sentiment: %{x:.3f}</b><br>Articles: %{y}<extra></extra>',
        showlegend=False
    ))
    
    # Add KDE curve
    density = stats.gaussian_kde(df['net_sentiment'])
    xs = np.linspace(-1, 1, 200)
    ys = density(xs)
    # Scale KDE to match histogram height
    ys_scaled = ys * len(df['net_sentiment']) * bin_width
    
    fig.add_trace(go.Scatter(
        x=xs,
        y=ys_scaled,
        mode='lines',
        line=dict(color=AITREND_COLOURS['text'], width=2.5),
        name='Density Curve',
        hovertemplate='<b>Sentiment: %{x:.3f}</b><br>Density: %{y:.1f}<extra></extra>'
    ))
    
    # Add vertical line at zero (neutral)
    fig.add_vline(
        x=0,
        line_dash="dash",
        line_color=AITREND_COLOURS['text'],
        line_width=2.5,
        opacity=0.7,
        annotation_text="Neutral",
        annotation_position="top",
        annotation_font_size=12,
        annotation_font_color=AITREND_COLOURS['text']
    )
    
    # Add shaded regions for negative/positive
    fig.add_vrect(
        x0=-1, x1=0,
        fillcolor=AITREND_COLOURS['negative'],
        opacity=0.08,
        line_width=0,
        layer='below'
    )
    fig.add_vrect(
        x0=0, x1=1,
        fillcolor=AITREND_COLOURS['positive'],
        opacity=0.08,
        line_width=0,
        layer='below'
    )
    
    # Add text annotations for regions
    color_negative_dark = '#A05A1F'
    color_positive_dark = '#3A6B7A'
    
    # Get max y value for positioning labels
    max_y = max(max(counts), max(ys_scaled))
    
    fig.add_annotation(
        x=-0.5, y=max_y * 0.95,
        text="<b>Negative</b>",
        showarrow=False,
        font=dict(size=14, color=color_negative_dark),
        yshift=0
    )
    
    fig.add_annotation(
        x=0.5, y=max_y * 0.95,
        text="<b>Positive</b>",
        showarrow=False,
        font=dict(size=14, color=color_positive_dark),
        yshift=0
    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text='Distribution of Article Sentiment',
            font=dict(size=18, color=AITREND_COLOURS['text'], family='Arial, sans-serif'),
            x=0.5,
            xanchor='center'
        ),
        xaxis_title="Net Sentiment Score (Negative ← → Positive)",
        yaxis_title="Number of Articles",
        height=450,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=70, r=70, t=80, b=70),
        hovermode='x unified',
        showlegend=False,
        bargap=0.02
    )
    
    # Update axes
    fig.update_xaxes(
        range=[-1, 1],
        dtick=0.2,
        tickfont=dict(size=14, color=AITREND_COLOURS['text']),
        title_font=dict(size=16, color=AITREND_COLOURS['text']),
        showgrid=False
    )
    
    fig.update_yaxes(
        rangemode='tozero',
        tickfont=dict(size=14, color=AITREND_COLOURS['text']),
        title_font=dict(size=16, color=AITREND_COLOURS['text']),
        gridcolor='rgba(0,0,0,0.1)',
        griddash='dot'
    )
    
    st.plotly_chart(fig)
    
    # Display metrics in two compact lines
    st.markdown(
        f"**Positive:** {positive_pct:.1f}% ({positive_count}) &nbsp;|&nbsp; "
        f"**Neutral:** {neutral_pct:.1f}% ({neutral_count}) &nbsp;|&nbsp; "
        f"**Negative:** {negative_pct:.1f}% ({negative_count}) &nbsp;|&nbsp; "
        f"**Mixed:** {mixed_pct:.1f}% ({mixed_count})"
    )
    st.markdown(
        f"**Leaning Negative:** {leaning_neg_pct:.1f}% ({leaning_negative}) &nbsp;|&nbsp; "
        f"**Leaning Positive:** {leaning_pos_pct:.1f}% ({leaning_positive}) &nbsp;|&nbsp; "
        f"**Mean Score:** {mean_sentiment:.3f} &nbsp;|&nbsp; "
        f"**Median Score:** {median_sentiment:.3f}"
    )
    
    st.markdown("---")
    
    # Source Statistics section
    st.subheader("Source Statistics & Growth")
    
    # Create sentiment by source analysis
    source_sentiment = pd.crosstab(df['source'], df['sentiment'])
    source_sentiment['Total'] = source_sentiment.sum(axis=1)
    source_sentiment = source_sentiment.sort_values('Total', ascending=False)
    
    # Clean up source names (remove www. prefix)
    source_sentiment.index = source_sentiment.index.str.replace(r'^www\.', '', regex=True)
    
    # Prepare data for Plotly stacked bar chart
    sources = source_sentiment.index.tolist()
    num_sources = len(sources)

    # Calculate dynamic height: minimum 48px per source, minimum 400px total
    chart_height = max(400, num_sources * 48)
    
    # Get sentiment counts and percentages for each source
    sentiment_data = {
        'Negative': {'counts': [], 'percentages': [], 'color': '#C17D3D'},
        'Neutral': {'counts': [], 'percentages': [], 'color': '#8B9D83'},
        'Positive': {'counts': [], 'percentages': [], 'color': '#5C9AA5'},
        'Mixed': {'counts': [], 'percentages': [], 'color': '#B8A893'}
    }
    
    for source in sources:
        total = source_sentiment.loc[source, 'Total']
        for sentiment_type in ['Negative', 'Neutral', 'Positive', 'Mixed']:
            count = source_sentiment.loc[source].get(sentiment_type.lower(), 0)
            pct = (count / total * 100) if total > 0 else 0
            sentiment_data[sentiment_type]['counts'].append(count)
            sentiment_data[sentiment_type]['percentages'].append(pct)
    
    # Create Plotly stacked horizontal bar chart (100% stacked)
    fig = go.Figure()
    
    # Add bars for each sentiment type (in order: Negative, Neutral, Positive, Mixed)
    for sentiment_type in ['Negative', 'Neutral', 'Positive', 'Mixed']:
        data = sentiment_data[sentiment_type]
        fig.add_trace(go.Bar(
            name=sentiment_type,
            y=sources,
            x=data['percentages'],  # Use percentages for x-axis
            orientation='h',
            marker=dict(color=data['color']),
            text=[f"{pct:.1f}% ({count})" if count > 0 else "" for count, pct in zip(data['counts'], data['percentages'])],
            textposition='inside',
            textfont=dict(color='white', size=14),
            hovertemplate='<b>%{y}</b><br>' +
                         f'{sentiment_type}: %{{customdata}} articles ' +
                         '(%{x:.1f}%)<extra></extra>',
            customdata=data['counts']  # Show counts in hover
        ))
    
    # Update layout
    fig.update_layout(
        barmode='stack',
        title=dict(
            text='Sentiment Distribution by Source',
            font=dict(size=16, color=AITREND_COLOURS['text'], family='Arial, sans-serif'),
            x=0.5,
            xanchor='center',
            pad=dict(b=20)  # Add padding below title
        ),
        xaxis_title="Sentiment Distribution (%)",
        yaxis_title=None,
        height=chart_height,  # Dynamic height based on number of sources
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=20, r=20, t=80, b=60),  # Increased top margin for title spacing
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=14),
            traceorder='normal'  # Keep legend in same order as traces (Negative, Neutral, Positive, Mixed)
        ),
        hovermode='y unified'
    )
    
    # Update axes
    fig.update_xaxes(
        tickfont=dict(size=14, color=AITREND_COLOURS['text']),
        title_font=dict(size=16, color=AITREND_COLOURS['text']),
        gridcolor='rgba(0,0,0,0.1)',
        griddash='dot',
        range=[0, 100],
        ticksuffix='%'
    )
    
    fig.update_yaxes(
        tickfont=dict(size=14, color=AITREND_COLOURS['text']),
        categoryorder='array',
        categoryarray=sources  # Maintain sorted order
    )
    
    st.plotly_chart(fig)
    
    # Add summary statistics table below the chart
    summary_data = []
    for source in sources:
        total = source_sentiment.loc[source, 'Total']
        share = (total / total_articles * 100)
        summary_data.append({
            'Source': source,
            'Total Articles': int(total),
            'Share of Total': f"{share:.1f}%"
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(
        summary_df,
        hide_index=True,
        height=len(summary_df) * 35 + 38,  # Dynamic height: 35px per row + 38px for header
        column_config={
            "Source": st.column_config.TextColumn("Source", width="medium"),
            "Total Articles": st.column_config.NumberColumn("Total Articles", width="small"),
            "Share of Total": st.column_config.TextColumn("Share of Total", width="small")
        }
    )
    
    st.markdown("---")
    st.markdown("**Growth Overview**")
    
    # Parse dates for growth analysis
    df['date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce', utc=True)
    df['indexed_at_parsed'] = pd.to_datetime(df['indexed_at'], errors='coerce', utc=True)
    df['date_parsed'] = df['date_parsed'].fillna(df['indexed_at_parsed'])
    
    # Get date range - ensure we're working with valid datetime objects only
    df_sorted = df.dropna(subset=['date_parsed']).copy()
    
    if len(df_sorted) > 0:
        # Remove timezone info for simpler handling
        df_sorted['date_parsed'] = df_sorted['date_parsed'].dt.tz_localize(None)
        df_sorted = df_sorted.sort_values('date_parsed')
        
        earliest_date = df_sorted['date_parsed'].min()
        latest_date = df_sorted['date_parsed'].max()
        
        # Calculate monthly growth
        df_sorted['month'] = df_sorted['date_parsed'].dt.to_period('M')
        monthly_counts = df_sorted.groupby('month').size()
        
        # Build growth overview text
        total_text = f"**Total Articles:** {len(df)}"
        
        if len(monthly_counts) > 1:
            recent_month = monthly_counts.iloc[-1]
            prev_month = monthly_counts.iloc[-2]
            growth = recent_month - prev_month
            growth_pct = (growth / prev_month * 100) if prev_month > 0 else 0
            month_text = f"**Latest Month:** {recent_month} ({growth:+d}, {growth_pct:+.0f}%)"
        else:
            month_text = f"**Latest Month:** {monthly_counts.iloc[-1] if len(monthly_counts) > 0 else 0}"
        
        # Date range
        if pd.notna(earliest_date) and pd.notna(latest_date):
            date_range = f"**Date Range:** {earliest_date.strftime('%b %Y')} - {latest_date.strftime('%b %Y')}"
        else:
            date_range = ""
        
        # Display all in one line
        st.markdown(f"{total_text} &nbsp;|&nbsp; {month_text} &nbsp;|&nbsp; {date_range}")
    else:
        st.warning("No valid dates found in articles for growth analysis.")
    
    st.markdown("---")
    
    # Key topics analysis (using named entities)
    # Check if we have entities
    all_entities = []
    for entities in df['entities']:
        if entities:
            all_entities.extend(entities)
    
    # If no entities, fall back to key phrases and show info message
    if not all_entities:
        st.info("⚠️ Named entities not found in current data. Showing key phrases instead. " +
                "To see entities, re-run the pipeline to update indexed articles.")
        st.markdown("*Key topics and phrases from articles*")
        all_entities = []
        for phrases in df['key_phrases']:
            if phrases:
                all_entities.extend(phrases)
    
    if all_entities:
        # Create word frequency dictionary for word cloud
        entity_counts = Counter(all_entities)
        
        # Top Topics Analysis section
        st.subheader("Top Topics Analysis")
        st.markdown("*Entities mentioned across multiple news sources (filtered to show cross-source trends)*")
        
        # Prepare detailed topic data with sentiment analysis
        # Apply fixed filter: minimum 2 sources (removes single-source boilerplate)
        MIN_SOURCES = 2
        
        topic_details = []
        for entity, count in entity_counts.most_common(100):  # Get top 100 for filtering
            # Find articles containing this entity
            articles_with_entity = df[df['entities'].apply(lambda x: entity in x if x else False)]
            
            if len(articles_with_entity) > 0:
                # Get number of unique articles and sources
                num_articles = len(articles_with_entity)
                num_sources = articles_with_entity['source'].nunique()
                
                # Apply filter: require minimum 2 sources
                if num_sources < MIN_SOURCES:
                    continue
                
                # Calculate sentiment distribution
                sentiment_dist = articles_with_entity['sentiment'].value_counts()
                positive = sentiment_dist.get('positive', 0)
                neutral = sentiment_dist.get('neutral', 0)
                negative = sentiment_dist.get('negative', 0)
                mixed = sentiment_dist.get('mixed', 0)
                
                # Calculate average net sentiment
                avg_net_sentiment = articles_with_entity['net_sentiment'].mean()
                
                topic_details.append({
                    'Topic': entity,
                    'Total Mentions': count,
                    'Articles': num_articles,
                    'Sources': num_sources,
                    'Positive': positive,
                    'Neutral': neutral,
                    'Negative': negative,
                    'Mixed': mixed,
                    'Avg Sentiment': avg_net_sentiment
                })
        
        # Create DataFrame
        topics_df = pd.DataFrame(topic_details)
        
        # Sort by total mentions
        topics_df = topics_df.sort_values('Total Mentions', ascending=False)
        
        # Show count of topics after filtering
        st.markdown(f"**Showing {len(topics_df)} cross-source topics** (minimum 2 news sources required)")
        
        # Interactive data table with all topics (sortable and filterable)
        st.markdown("**Topic Statistics** (sortable - click column headers to sort)")
        
        # Keep numeric values for proper sorting
        st.dataframe(
            topics_df,
            hide_index=True,
            column_config={
                "Topic": st.column_config.TextColumn("Topic", width="large"),
                "Total Mentions": st.column_config.NumberColumn("Mentions", width="small"),
                "Articles": st.column_config.NumberColumn("Articles", width="small", help="Number of unique articles mentioning this topic"),
                "Sources": st.column_config.NumberColumn("Sources", width="small", help="Number of different news sources covering this topic"),
                "Positive": st.column_config.NumberColumn("Positive", width="small"),
                "Neutral": st.column_config.NumberColumn("Neutral", width="small"),
                "Negative": st.column_config.NumberColumn("Negative", width="small"),
                "Mixed": st.column_config.NumberColumn("Mixed", width="small"),
                "Avg Sentiment": st.column_config.NumberColumn(
                    "Avg Sentiment", 
                    width="small",
                    format="%.3f"  # Format as 3 decimal places
                )
            },
            height=400
        )
        
        st.markdown("---")
        
        # Word Cloud section - moved to bottom for better page flow
        st.subheader("Topic Word Cloud")
        if all_entities and not any(df['entities'].apply(lambda x: len(x) > 0 if x else False)):
            st.markdown("*Visual representation of key topics and phrases*")
        else:
            st.markdown("*Visual representation of most mentioned organizations, people, products, and locations*")
        
        # Custom color function using AITREND_COLOURS palette
        def aitrend_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            import random
            # Use colors from the dashboard palette with variations
            colors = [
                AITREND_COLOURS['primary'],    # #C17D3D - Muted warm brown/tan
                AITREND_COLOURS['secondary'],  # #A0917A - Soft taupe
                AITREND_COLOURS['accent'],     # #5D5346 - Rich dark brown
                AITREND_COLOURS['positive'],   # #5B8FA3 - Muted teal/blue
                AITREND_COLOURS['neutral'],    # #9C8E7A - Medium warm tan
                AITREND_COLOURS['negative'],   # #C17D3D - Warm amber/orange (same as primary)
                '#7B9DA8',  # Lighter teal variation
                '#8B7A6B',  # Grey-brown variation
                '#A68A5F',  # Tan variation
                '#6B8B95',  # Steel teal
            ]
            return random.choice(colors)
        
        # Create high-resolution word cloud for crisp rendering
        wordcloud = WordCloud(
            width=1600,  # Doubled resolution for crispness
            height=700,  # Doubled resolution
            background_color=AITREND_COLOURS['background'],
            color_func=aitrend_color_func,
            relative_scaling=0.5,
            min_font_size=14,  # Increased for better readability
            max_words=100,
            contour_width=0,
            contour_color=AITREND_COLOURS['accent'],
            prefer_horizontal=0.7  # More horizontal text for readability
        ).generate_from_frequencies(entity_counts)
        
        # Display word cloud with high-quality settings
        figsize = get_responsive_figsize(10, 5, container_fraction=1.0)
        fig, ax = plt.subplots(figsize=figsize, dpi=150)  # Higher DPI for crispness
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        plt.tight_layout(pad=0)
        st.pyplot(fig)
    else:
        st.info("No entities available for analysis.")

def show_about_page():
    """About page with project information"""
    st.header("About AI Trend Monitor")
    
    st.markdown("""
    ### Project Overview
    
    AI Trend Monitor is an intelligent news aggregation and analysis system that:
    
    - **Collects** AI-related articles from multiple trusted sources
    - **Analyzes** content using Azure AI Language services
    - **Indexes** articles for fast semantic search
    - **Visualizes** trends and sentiment patterns
    
    ### Technology Stack
    
    **Backend:**
    - Python 3.12.11
    - Azure Blob Storage (data persistence)
    - Azure AI Language (NLP analysis)
    - Azure AI Search (semantic search)
    
    **Frontend:**
    - Streamlit (interactive dashboard)
    - Plotly (data visualizations)
    
    ### Data Sources
    
    **API Sources:**
    - The Guardian API (AI-related articles from June 2025+)
    
    **RSS Feeds:**
    - TechCrunch (AI category + events + Europe)
    - VentureBeat (AI category)
    - Ars Technica (artificial intelligence tag)
    - Gizmodo (AI tag)
    - IEEE Spectrum (technology & research)
    - The Register UK (tech news)
    - The Verge (product launches)
    - EU-Startups (European startup ecosystem)
    
    ### Features
    
    - Real-time article search with filters  
    - Sentiment analysis and scoring  
    - Key phrase extraction  
    - Entity recognition  
    - Interactive analytics dashboard  
    - Source and sentiment breakdowns  
    
    ### Project Status
    
    **Phase 3 Complete:** Knowledge Mining with Azure AI Search  
    **Phase 4 Complete:** Interactive Web Dashboard (this app!)  
    **Phase 5 Complete:** RAG-powered chatbot with GPT-4.1-mini  
    **Phase 6 Planned:** Automated weekly trend reports  
    
    ---
    
    **Author:** Amanda Sumner  
    **Repository:** [github.com/PieRatCat/ai-trend-monitor](https://github.com/PieRatCat/ai-trend-monitor)
    """)

def format_article_date(date_str):
    """Format article date to 'Thursday, October 16, 2025' format"""
    if not date_str or date_str == 'Unknown':
        return 'Date unknown'
    
    try:
        # Try parsing RFC 2822 format with GMT (e.g., "Sun, 12 Oct 2025 19:00:00 GMT")
        if ',' in date_str and 'GMT' in date_str:
            # Remove GMT and parse
            date_str_clean = date_str.replace('GMT', '').strip()
            date_obj = datetime.strptime(date_str_clean, '%a, %d %b %Y %H:%M:%S')
        # Try parsing RFC 2822 format with +0000 (e.g., "Tue, 14 Oct 2025 18:24:53 +0000")
        elif ',' in date_str and '+' in date_str:
            # Remove timezone info and parse
            date_str_clean = date_str.split('+')[0].strip()
            date_obj = datetime.strptime(date_str_clean, '%a, %d %b %Y %H:%M:%S')
        # Try parsing ISO format with timezone
        elif 'T' in date_str:
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Try standard date format
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Format as "Thursday, October 16, 2025"
        return date_obj.strftime('%A, %B %d, %Y')
    except Exception as e:
        # If parsing fails, return original
        return date_str

def show_chatbot_page():
    """Chatbot page with RAG-powered conversational AI"""
    
    # Get actual article count from Azure AI Search (cached for performance)
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_article_count():
        """Get the total number of indexed articles (filtered to June 1, 2025 onwards)"""
        from dateutil import parser as date_parser
        try:
            search_client = get_search_client()
            if search_client:
                # Get all articles with dates
                results = search_client.search(
                    search_text="*", 
                    select=["published_date"], 
                    top=1000
                )
                
                # Filter to June 1, 2025 onwards (same as Analytics page)
                cutoff_date = datetime(2025, 6, 1)
                filtered_count = 0
                
                for result in results:
                    date_str = result.get('published_date', '')
                    if date_str:
                        try:
                            article_date = date_parser.parse(date_str)
                            if article_date.tzinfo:
                                article_date = article_date.replace(tzinfo=None)
                            if article_date >= cutoff_date:
                                filtered_count += 1
                        except:
                            pass
                
                return filtered_count
        except Exception:
            pass
        return 150  # Fallback to approximate count
    
    article_count = get_article_count()
    
    st.markdown(f"""
    **Hello, I'm Dot, your AI trends assistant.** I'm here to help you explore the latest developments in artificial intelligence.  
    I can answer questions about AI trends, technologies, and breakthroughs by searching through **{article_count} curated news articles**. 
    
    *Powered by GPT-4.1-mini (GitHub Models) with retrieval-augmented generation*
    """)
    
    # Initialize chatbot (with caching to avoid recreating)
    @st.cache_resource
    def get_chatbot():
        """Initialize and cache the RAG chatbot instance"""
        try:
            return RAGChatbot()
        except Exception as e:
            st.error(f"Failed to initialize chatbot: {e}")
            st.info("Make sure your GITHUB_TOKEN is set in the .env file.")
            return None
    
    chatbot = get_chatbot()
    
    # Initialize session state for conversation history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    # Stats and controls at the top (simplified - no sliders)
    col_stats1, col_stats2, col_clear = st.columns([1, 1, 1.5])
    
    with col_stats1:
        st.metric("Total Messages", len(st.session_state.messages))
    
    with col_stats2:
        st.metric("Conversations", len([m for m in st.session_state.messages if m["role"] == "user"]))
    
    with col_clear:
        st.write("")  # Spacer for alignment
        # Clear conversation button
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.rerun()
    
    # Example questions in an expander
    with st.expander("Example Questions"):
        st.markdown("""
        - What are the latest trends in large language models?
        - What companies are investing in AI?
        - Tell me about recent AI safety concerns
        - What's happening with GPT-5?
        - Summarize recent AI regulations
        """)
    
    # Display chat history (only show divider if there are messages)
    if st.session_state.messages:
        st.divider()
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.container():
                st.markdown(f"""
                <div style="background-color: #F5F3EF; padding: 1rem; border-radius: 8px; 
                            margin: 0.5rem 0; border-left: 4px solid {AITREND_COLOURS['primary']}; 
                            color: {AITREND_COLOURS['text']};">
                    <strong>You:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.container():
                # Content is inside HTML div, so no LaTeX processing occurs - no need to escape
                st.markdown(f"""
                <div style="background-color: #FEFEFE; padding: 1rem; border-radius: 8px; 
                            margin: 0.5rem 0; border-left: 4px solid {AITREND_COLOURS['positive']}; 
                            color: {AITREND_COLOURS['text']};">
                    <strong>Dot:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Display sources in an expandable section
                if "sources" in message and message["sources"]:
                    with st.expander(f"View {len(message['sources'])} References", expanded=False):
                        for i, source in enumerate(message["sources"], 1):
                            formatted_date = format_article_date(source['date'])
                            st.markdown(f"""
                            <div style="background-color: #F5F3EF; padding: 0.5rem 0.75rem; border-radius: 6px; 
                                        margin: 0.3rem 0; border-left: 3px solid {AITREND_COLOURS['secondary']}; 
                                        font-size: 0.85rem;">
                                <strong>[{i}]</strong> <a href="{source['link']}" target="_blank" style="color: {AITREND_COLOURS['accent']}; text-decoration: none; font-weight: 600;">{source['title']}</a><br>
                                <span style="color: #666;">{source['source']} • {formatted_date}</span>
                            </div>
                            """, unsafe_allow_html=True)
    
    # Chat input
    if chatbot is not None:
        user_input = st.chat_input("Ask a question about AI trends...")
        
        if user_input:
            # Smart defaults: adjust retrieval based on query type
            # Temporal queries need more articles for comprehensive summaries
            temporal_keywords = ['last', 'past', 'this week', 'this month', 'recent', 'latest', 'today', 'yesterday', 'upcoming', 'future', 'next', 'later', 'soon', 'planned', 'expected', 'anticipated']
            is_temporal = any(keyword in user_input.lower() for keyword in temporal_keywords)
            
            top_k = 15 if is_temporal else 10  # More articles for temporal/future queries
            temperature = 0.7  # Balanced creativity/accuracy
            
            # Add user message to history
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Show loading state
            with st.spinner("Searching articles and generating answer..."):
                # Get response from chatbot
                if len(st.session_state.conversation_history) > 0:
                    # Use conversation history for follow-up questions
                    result = chatbot.chat_with_history(
                        user_query=user_input,
                        conversation_history=st.session_state.conversation_history,
                        top_k=top_k,
                        temperature=temperature
                    )
                else:
                    # First question - no history
                    result = chatbot.chat(
                        user_query=user_input,
                        top_k=top_k,
                        temperature=temperature
                    )
            
            # Add assistant response to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"]
            })
            
            # Update conversation history for multi-turn conversations
            st.session_state.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            st.session_state.conversation_history.append({
                "role": "assistant",
                "content": result["answer"]
            })
            
            # Rerun to display new messages
            st.rerun()
    
    else:
        st.warning("Chatbot is not available. Please check your configuration.")
        st.info("""
        **Required Setup:**
        1. Get a GitHub Personal Access Token from: https://github.com/settings/tokens
        2. Add it to your `.env` file as: `GITHUB_TOKEN=your_token_here`
        3. Restart the Streamlit app
        """)
    
    # Footer (add spacing without divider)
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        Powered by <strong>GPT-4.1-mini</strong> (GitHub Models) • 
        <strong>Azure AI Search</strong> • 
        <strong>{article_count} AI News Articles</strong>
    </div>
    """, unsafe_allow_html=True)
    
    # Back to top link
    st.markdown("""
    <div style="text-align: center; margin-top: 1.5rem;">
        <a href="#ai-trend-monitor" style="color: #5D5346; text-decoration: none; font-size: 0.95rem;">
            ↑ Back to Top
        </a>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
