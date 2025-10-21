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

def main():
    """Main application"""
    
    # Load custom CSS from external file
    css_file = Path(__file__).parent / "styles.css"
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    st.title("AI Trend Monitor")
    st.markdown("*Exploring AI news trends with advanced analytics and search*")
    
    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["News", "Analytics", "Chatbot", "About"]
    )
    
    if page == "News":
        show_news_page()
    elif page == "Analytics":
        show_analytics_page()
    elif page == "Chatbot":
        show_chatbot_page()
    else:
        show_about_page()

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
              "arstechnica.com", "gizmodo.com"]
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
        if len(content) > 400:
            st.markdown(f"{content[:400]}...")
        else:
            st.markdown(content)
        
        st.markdown(f"[Read More]({article['link']})")
        st.markdown("---")

@st.cache_data(ttl=3600)  # Cache for 1 hour
def generate_curated_content(section_type):
    """Generate curated content using RAG chatbot"""
    try:
        chatbot = RAGChatbot()
        
        if section_type == "releases":
            query = """What are the most recent AI product releases, model announcements, or major feature launches mentioned in the articles?

List 5 items in this format:
<li><strong>Product/Company Name:</strong> Brief description</li>

Focus on recently released products and announcements, not future events."""
            temperature = 0.5
        else:  # upcoming
            query = """What upcoming AI events, product releases, or anticipated launches are mentioned in the articles?

Provide exactly 5 items using this HTML format only (no numbered lists, no markdown):
<li><strong>Date/Timeframe:</strong> Event or release name and brief description</li>

Focus on future events and planned releases. Use only bullet points in the format shown above."""
            temperature = 0.7
        
        result = chatbot.chat(query, top_k=15, temperature=temperature)
        
        # Clean up the response
        answer = result["answer"]
        
        # Remove unwanted phrases
        unwanted_phrases = [
            "Based on the provided articles,",
            "here are 5",
            "here are five", 
            "Here are 5",
            "Here are five",
            "Recent AI Developments:",
            "Mark Your Calendar:",
            "Based on the articles,",
            "According to the articles,",
            "```html",
            "```"
        ]
        for phrase in unwanted_phrases:
            answer = answer.replace(phrase, "")
        
        # Remove article citations like [1], [2], [1][2], etc.
        import re
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
    
    # New Releases Section
    st.subheader("New Releases & Updates")
    
    with st.spinner("Generating recent developments..."):
        releases_content = generate_curated_content("releases")
    
    if releases_content:
        st.markdown(f"""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <p style='margin: 0; color: #2D2D2D;'><strong>Recent AI Developments:</strong></p>
        {releases_content}
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Generated from indexed articles</em></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to static content if generation fails
        st.markdown("""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <p style='margin: 0; color: #2D2D2D;'><strong>Recent AI Developments:</strong></p>
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
    
    # Upcoming Events Section
    st.subheader("Upcoming Events & Releases")
    
    with st.spinner("Generating upcoming events..."):
        upcoming_content = generate_curated_content("upcoming")
    
    if upcoming_content:
        st.markdown(f"""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <p style='margin: 0; color: #2D2D2D;'><strong>Mark Your Calendar:</strong></p>
        {upcoming_content}
        <p style='margin-top: 1rem; font-size: 0.95rem; color: #5D5346;'><em>Generated from indexed articles</em></p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Fallback to static content if generation fails
        st.markdown("""
        <div style='background-color: #E8E3D9; padding: 1rem; border-radius: 8px;'>
        <p style='margin: 0; color: #2D2D2D;'><strong>Mark Your Calendar:</strong></p>
        <ul style='margin-top: 0.5rem; color: #2D2D2D;'>
        <li><strong>Late 2025:</strong> OpenAI expected to release o1 reasoning model for all ChatGPT users</li>
        <li><strong>December 9-15, 2025:</strong> NeurIPS Conference in Vancouver - Premier AI research presentations</li>
        <li><strong>Early 2026:</strong> Google Gemini 2.0 anticipated with enhanced multimodal capabilities</li>
        <li><strong>January 7-10, 2026:</strong> CES 2026 in Las Vegas - AI hardware and consumer tech showcase</li>
        <li><strong>Q1 2026:</strong> Apple Intelligence features expanding to more languages and regions</li>
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
    
    # Sidebar with statistics
    with st.sidebar:
        st.header("Statistics")
        st.metric("Total Articles", len(df))
        st.metric("Data Sources", df['source'].nunique())
        st.metric("Earliest Article", min_date)
        st.metric("Latest Article", max_date)
        st.metric("Avg Net Sentiment", f"{avg_net_sentiment:.3f} ({delta_label})")
    
    st.markdown(f"**Analyzing {len(articles)} articles**")
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
        
        # Create columns: selection controls, viz mode, and reset button on one row
        # Responsive: will stack on mobile
        col_select1, col_select2, col_viz, col_clear = st.columns([1.8, 1.2, 1.5, 0.5], gap="small")
        
        with col_select1:
            # Dropdown with top 100 entities - also gets reset with counter
            selected_from_dropdown = st.selectbox(
                "Select entity",
                options=top_100_entities,
                index=0,
                key=f"entity_dropdown_{st.session_state.entity_reset_counter}"
            )
        
        with col_select2:
            # Text input for manual entry - key changes when reset is clicked
            manual_entity = st.text_input(
                "Or search",
                placeholder="e.g., Grok, ChatGPT",
                key=f"entity_manual_input_{st.session_state.entity_reset_counter}"
            )
        
        with col_viz:
            # Visualization mode toggle on same row
            viz_mode = st.selectbox(
                "View mode",
                options=["Daily", "Cumulative", "Weekly"],
                index=1,  # Default to Cumulative
                help="Daily Count, Cumulative Count, or Weekly Aggregation"
            )
            # Map short names to full names
            viz_mode_map = {
                "Daily": "Daily Count",
                "Cumulative": "Cumulative Count",
                "Weekly": "Weekly Aggregation"
            }
            viz_mode = viz_mode_map[viz_mode]
        
        with col_clear:
            # Add some spacing to align with inputs
            st.write("")
            st.write("")
            if st.button("Reset", use_container_width=True, help="Clear search and reset"):
                # Increment counter to force widget recreation with new key
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
            
            # Create compact figure with two y-axes (responsive sizing)
            figsize = get_responsive_figsize(10, 3.5, container_fraction=1.0)
            fig, ax1 = plt.subplots(figsize=figsize)
            
            # Plot 1: Article count (left y-axis)
            color_count = AITREND_COLOURS['primary']
            color_count_dark = '#A05A1F'  # Darker orange for better visibility
            
            # Line plot for all modes
            line1 = ax1.plot(plot_data['date'], plot_data['article_count'], 
            color=color_count, marker='o', linewidth=1.5, markersize=5,
            label=count_label, markeredgecolor='white', markeredgewidth=0.8)
            
            ax1.set_xlabel('Publication Date', fontsize=9, color=AITREND_COLOURS['text'], fontweight='bold')
            ax1.set_ylabel(count_label, fontsize=9, color=color_count_dark, fontweight='bold')
            ax1.tick_params(axis='y', labelcolor=color_count_dark, colors=color_count_dark, labelsize=8)
            ax1.tick_params(axis='x', rotation=45, colors=AITREND_COLOURS['text'], labelsize=7)
            
            # Set y-axis to start at 0 for article count and use whole numbers only
            ax1.set_ylim(bottom=0)
            ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
            ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
            ax1.set_axisbelow(True)
            
            # Plot 2: Net sentiment (right y-axis)
            ax2 = ax1.twinx()
            color_sentiment = AITREND_COLOURS['positive']  # Use teal color from pie chart
            color_sentiment_dark = '#3A6B7A'  # Darker teal for better visibility
            
            # Line plot for all modes
            line2 = ax2.plot(plot_data['date'], plot_data['net_sentiment'], 
            color=color_sentiment, marker='s', linewidth=1.5, markersize=5,
            label='Net Sentiment', markeredgecolor='white', markeredgewidth=0.8)
            
            ax2.set_ylabel('Net Sentiment', fontsize=9, color=color_sentiment_dark, fontweight='bold')
            ax2.tick_params(axis='y', labelcolor=color_sentiment_dark, colors=color_sentiment_dark, labelsize=8)
            
            # Set sentiment y-axis to be symmetric around 0 (-1 to +1)
            max_abs_sentiment = max(abs(plot_data['net_sentiment'].min()), 
                           abs(plot_data['net_sentiment'].max()), 0.3)
            ax2.set_ylim(-max_abs_sentiment * 1.1, max_abs_sentiment * 1.1)
            
            # Add horizontal line at y=0 for neutral sentiment
            ax2.axhline(y=0, color=AITREND_COLOURS['neutral'], linestyle='-', 
               linewidth=1.2, alpha=0.6, label='Neutral (0)')
            
            # Add shaded regions for positive/negative
            ax2.axhspan(0, max_abs_sentiment * 1.1, alpha=0.05, color=AITREND_COLOURS['positive'], zorder=0)
            ax2.axhspan(-max_abs_sentiment * 1.1, 0, alpha=0.05, color=AITREND_COLOURS['negative'], zorder=0)
            
            # Title
            mode_text = viz_mode.replace(" Count", "").replace(" Aggregation", "")
            plt.title(f'Trend: "{selected_entity}" ({mode_text})', 
             fontsize=11, color=AITREND_COLOURS['text'], fontweight='bold', pad=20)
            
            # Combined legend - positioned above the plot area
            lines = line1 + line2
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc='lower left', bbox_to_anchor=(0, 1.02), 
              ncol=2, fontsize=8, framealpha=0.95, borderaxespad=0)
            
            # Format x-axis
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig)
            
            # Show summary statistics (full width for better visibility)
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 1], gap="medium")
            with col_a:
                st.metric("Total Articles", len(topic_articles))
            with col_b:
                positive_count = (topic_articles['sentiment'] == 'positive').sum()
                positive_pct = (positive_count / len(topic_articles)) * 100
                st.metric("Positive", f"{positive_pct:.1f}% ({positive_count})")
            with col_c:
                negative_count = (topic_articles['sentiment'] == 'negative').sum()
                negative_pct = (negative_count / len(topic_articles)) * 100
                st.metric("Negative", f"{negative_pct:.1f}% ({negative_count})")
            with col_d:
                date_range = (topic_articles['date'].max() - topic_articles['date'].min()).days
                st.metric("Date Span", f"{date_range} days")
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
    
    # Create diverging histogram with zero in the middle (responsive sizing)
    figsize = get_responsive_figsize(6, 3.5, container_fraction=1.0)
    fig, ax = plt.subplots(figsize=figsize)
    
    # Create histogram with gradient coloring
    # Create custom colormap from orange (negative) to teal (positive)
    colors_gradient = [AITREND_COLOURS['negative'], AITREND_COLOURS['neutral'], AITREND_COLOURS['positive']]
    n_bins = 30
    cmap = mcolors.LinearSegmentedColormap.from_list('sentiment', colors_gradient, N=n_bins)
    
    # Create histogram data
    counts, bins, patches = ax.hist(df['net_sentiment'], bins=n_bins, alpha=0.7, edgecolor='white', linewidth=0.5)
    
    # Color each bar based on its position (negative to positive)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    # Normalize bin centers to [0, 1] for colormap
    col = (bin_centers + 1) / 2  # Map from [-1, 1] to [0, 1]
    for c, p in zip(col, patches):
        p.set_facecolor(cmap(c))
    
    # Add KDE curve
    density = stats.gaussian_kde(df['net_sentiment'])
    xs = np.linspace(-1, 1, 200)
    ys = density(xs)
    # Scale KDE to match histogram height
    ys_scaled = ys * len(df['net_sentiment']) * (bins[1] - bins[0])
    ax.plot(xs, ys_scaled, color=AITREND_COLOURS['text'], linewidth=2, alpha=0.8)
    
    # Add vertical line at zero (neutral)
    ax.axvline(x=0, color=AITREND_COLOURS['text'], linestyle='--', 
               linewidth=2, alpha=0.7, label='Neutral (0)')
    
    # Color the regions
    ax.axvspan(-1, 0, alpha=0.05, color=AITREND_COLOURS['negative'], zorder=0)
    ax.axvspan(0, 1, alpha=0.05, color=AITREND_COLOURS['positive'], zorder=0)
    
    # Add labels for regions with darker colors
    color_negative_dark = '#A05A1F'  # Darker orange
    color_positive_dark = '#3A6B7A'  # Darker teal
    ax.text(-0.5, ax.get_ylim()[1] * 0.95, 'Negative', 
           fontsize=9, color=color_negative_dark, 
           ha='center', va='top', fontweight='bold', alpha=1.0)
    ax.text(0.5, ax.get_ylim()[1] * 0.95, 'Positive', 
           fontsize=9, color=color_positive_dark, 
           ha='center', va='top', fontweight='bold', alpha=1.0)
    
    ax.set_xlabel('Net Sentiment Score (Negative ← → Positive)', 
                  fontsize=9, color=AITREND_COLOURS['text'], fontweight='bold')
    ax.set_ylabel('Number of Articles', fontsize=9, color=AITREND_COLOURS['text'], fontweight='bold')
    ax.set_title('Distribution of Article Sentiment', fontsize=10, 
                color=AITREND_COLOURS['text'], pad=10, fontweight='bold')
    ax.tick_params(labelsize=7, colors=AITREND_COLOURS['text'])
    ax.set_xlim(-1, 1)
    ax.legend(fontsize=7, framealpha=0.9)
    
    plt.tight_layout()
    st.pyplot(fig)
    
    # Combined metrics in two rows
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        st.metric("Positive", f"{positive_pct:.1f}% ({positive_count} articles)")
    with col2:
        st.metric("Neutral", f"{neutral_pct:.1f}% ({neutral_count} articles)")
    with col3:
        st.metric("Negative", f"{negative_pct:.1f}% ({negative_count} articles)")
    with col4:
        st.metric("Mixed", f"{mixed_pct:.1f}% ({mixed_count} articles)")
    
    col5, col6, col7, col8 = st.columns(4, gap="small")
    with col5:
        st.metric("Leaning Negative", f"{leaning_neg_pct:.1f}% ({leaning_negative} articles)")
    with col6:
        st.metric("Leaning Positive", f"{leaning_pos_pct:.1f}% ({leaning_positive} articles)")
    with col7:
        st.metric("Mean Score", f"{mean_sentiment:.3f}")
    with col8:
        st.metric("Median Score", f"{median_sentiment:.3f}")
    
    st.markdown("---")
    
    # Source Statistics section
    st.subheader("Source Statistics & Growth")
    
    # Create sentiment by source analysis
    source_sentiment = pd.crosstab(df['source'], df['sentiment'])
    source_sentiment['Total'] = source_sentiment.sum(axis=1)
    source_sentiment = source_sentiment.sort_values('Total', ascending=False)
    
    # Create compact HTML table
    table_html = """<table class="source-table">
    <thead>
        <tr>
            <th>Source</th>
            <th style="text-align: center;">Articles</th>
            <th style="text-align: center;">Share</th>
            <th>Sentiment Distribution</th>
        </tr>
    </thead>
    <tbody>"""
    
    for source in source_sentiment.index:
        count = source_sentiment.loc[source, 'Total']
        pct = (count / total_articles) * 100
        
        # Get sentiment counts for this source
        pos = source_sentiment.loc[source].get('positive', 0)
        neu = source_sentiment.loc[source].get('neutral', 0)
        neg = source_sentiment.loc[source].get('negative', 0)
        mix = source_sentiment.loc[source].get('mixed', 0)
        
        # Calculate percentages for sentiment bar
        pos_pct = (pos / count * 100) if count > 0 else 0
        neu_pct = (neu / count * 100) if count > 0 else 0
        neg_pct = (neg / count * 100) if count > 0 else 0
        mix_pct = (mix / count * 100) if count > 0 else 0
        
        # Build sentiment bar (ordered: Negative → Neutral → Positive → Mixed)
        sentiment_bar = '<div class="sentiment-bar">'
        if neg > 0:
            sentiment_bar += f'<div class="sentiment-segment" style="width: {neg_pct}%; background-color: #C17D3D;">{neg}</div>'
        if neu > 0:
            sentiment_bar += f'<div class="sentiment-segment" style="width: {neu_pct}%; background-color: #8B9D83;">{neu}</div>'
        if pos > 0:
            sentiment_bar += f'<div class="sentiment-segment" style="width: {pos_pct}%; background-color: #5C9AA5;">{pos}</div>'
        if mix > 0:
            sentiment_bar += f'<div class="sentiment-segment" style="width: {mix_pct}%; background-color: #B8A893;">{mix}</div>'
        sentiment_bar += '</div>'
        
        table_html += f"""
    <tr>
        <td><strong>{source}</strong></td>
        <td style="text-align: center;">{int(count)}</td>
        <td style="text-align: center;">{pct:.0f}%</td>
        <td>{sentiment_bar}</td>
    </tr>"""
    
    table_html += """
    </tbody>
</table>"""
    
    st.markdown(table_html, unsafe_allow_html=True)
    
    # Legend below table (ordered: Negative → Neutral → Positive → Mixed)
    st.markdown("""
    <div style="margin-top: 8px; font-size: 16px; color: #666;">
        <span style="color: #C17D3D;">●</span> Negative &nbsp;
        <span style="color: #8B9D83;">●</span> Neutral &nbsp;
        <span style="color: #5C9AA5;">●</span> Positive &nbsp;
        <span style="color: #B8A893;">●</span> Mixed
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**Growth Overview**")
    
    # Parse dates for growth analysis
    df['date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce')
    df['indexed_at_parsed'] = pd.to_datetime(df['indexed_at'], errors='coerce')
    df['date_parsed'] = df['date_parsed'].fillna(df['indexed_at_parsed'])
    
    # Get date range
    df_sorted = df.sort_values('date_parsed')
    earliest_date = df_sorted['date_parsed'].min()
    latest_date = df_sorted['date_parsed'].max()
    
    # Calculate monthly growth
    df_sorted['month'] = df_sorted['date_parsed'].dt.to_period('M')
    monthly_counts = df_sorted.groupby('month').size()
    
    # Display metrics
    st.metric("Total Articles", f"{len(df)}")
    
    if len(monthly_counts) > 1:
        recent_month = monthly_counts.iloc[-1]
        prev_month = monthly_counts.iloc[-2]
        growth = recent_month - prev_month
        growth_pct = (growth / prev_month * 100) if prev_month > 0 else 0
        st.metric("Latest Month", f"{recent_month} ({growth:+d}, {growth_pct:+.0f}%)")
    else:
        st.metric("Latest Month", f"{monthly_counts.iloc[-1] if len(monthly_counts) > 0 else 0}")
    
    # Date range
    if pd.notna(earliest_date) and pd.notna(latest_date):
        date_range = f"{earliest_date.strftime('%b %Y')} - {latest_date.strftime('%b %Y')}"
        st.caption(date_range)
    
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
        
        # Word Cloud section - full width for better visibility
        st.subheader("Top Named Entities")
        if all_entities and not any(df['entities'].apply(lambda x: len(x) > 0 if x else False)):
            st.markdown("*Key topics and phrases from articles*")
        else:
            st.markdown("*Organizations, people, products, and locations mentioned in articles*")
        
        # Custom color function using AITREND_COLOURS palette (teal, grey, orange)
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
        
        # Create word cloud with better size
        wordcloud = WordCloud(
            width=800, 
            height=400,
            background_color=AITREND_COLOURS['background'],
            color_func=aitrend_color_func,
            relative_scaling=0.5,
            min_font_size=10,
            max_words=100,
            contour_width=0,
            contour_color=AITREND_COLOURS['accent']
        ).generate_from_frequencies(entity_counts)
        
        # Display word cloud with responsive figure size
        figsize = get_responsive_figsize(10, 5, container_fraction=1.0)
        fig, ax = plt.subplots(figsize=figsize)
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        plt.tight_layout(pad=0)
        st.pyplot(fig)
        
        st.markdown("---")
        
        # Top 10 Topics section
        st.subheader("Top 10 Topics")
        st.markdown("*Most frequently mentioned entities*")
        
        # Get top 10 entities
        top_10 = entity_counts.most_common(10)
        
        # Create HTML table with larger font size
        table_html = """<table class="topics-table">
    <thead>
        <tr>
            <th class="rank-col">#</th>
            <th>Topic</th>
            <th class="mentions-col">Mentions</th>
        </tr>
    </thead>
    <tbody>"""
        
        for i, (topic, mentions) in enumerate(top_10, 1):
            table_html += f"""
        <tr>
            <td class="rank-col">{i}</td>
            <td>{topic}</td>
            <td class="mentions-col">{mentions}</td>
        </tr>"""
        
        table_html += """
    </tbody>
</table>"""
        
        st.markdown(table_html, unsafe_allow_html=True)
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
    
    - The Guardian API
    - TechCrunch RSS
    - VentureBeat RSS
    - Ars Technica RSS
    - Gizmodo RSS
    
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
    st.header("AI Trends Chatbot")
    st.markdown("""
    Ask questions about artificial intelligence trends and get answers grounded in our curated news database. 
    The chatbot uses **GPT-4.1-mini** powered by GitHub Models and retrieves information from **150+ indexed articles**.
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
    
    # Sidebar with settings
    st.sidebar.header("Chatbot Settings")
    
    # Number of articles to retrieve
    top_k = st.sidebar.slider(
        "Articles to retrieve",
        min_value=5,
        max_value=20,
        value=15,
        help="Number of relevant articles to use as context. For temporal queries (e.g., 'last 24 hours'), more articles = more comprehensive summary."
    )
    
    # Temperature setting
    temperature = st.sidebar.slider(
        "Response creativity",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Lower = more focused, Higher = more creative"
    )
    
    st.sidebar.divider()
    
    st.sidebar.subheader("Chat Statistics")
    st.sidebar.metric("Total Messages", len(st.session_state.messages))
    st.sidebar.metric("Conversations", len([m for m in st.session_state.messages if m["role"] == "user"]))
    
    st.sidebar.divider()
    
    # Clear conversation button
    if st.sidebar.button("Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.rerun()
    
    st.sidebar.divider()
    
    st.sidebar.subheader("Example Questions")
    st.sidebar.markdown("""
    - What are the latest trends in large language models?
    - What companies are investing in AI?
    - Tell me about recent AI safety concerns
    - What's happening with GPT-5?
    - Summarize recent AI regulations
    """)
    
    # Main chat interface
    st.divider()
    
    # Display chat history
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
                # Escape the content to prevent markdown issues
                escaped_content = message["content"].replace("$", r"\$")
                st.markdown(f"""
                <div style="background-color: #FEFEFE; padding: 1rem; border-radius: 8px; 
                            margin: 0.5rem 0; border-left: 4px solid {AITREND_COLOURS['positive']}; 
                            color: {AITREND_COLOURS['text']};">
                    <strong>Assistant:</strong><br>
                    {escaped_content}
                </div>
                """, unsafe_allow_html=True)
                
                # Display sources as numbered references
                if "sources" in message and message["sources"]:
                    st.markdown("<br><strong>References:</strong>", unsafe_allow_html=True)
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
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        Powered by <strong>GPT-4.1-mini</strong> (GitHub Models) • 
        <strong>Azure AI Search</strong> • 
        <strong>150+ AI News Articles</strong>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
