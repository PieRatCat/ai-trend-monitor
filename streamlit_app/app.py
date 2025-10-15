"""
AI Trend Monitor - Interactive Dashboard
A Streamlit web application for exploring AI news trends
"""

import streamlit as st
import os
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

# Load environment variables
load_dotenv()

# Claude.ai inspired color palette - warm beiges and dark greys
# Color-blind accessible sentiment colors
CLAUDE_COLORS = {
    'primary': '#C17D3D',      # Muted warm brown/tan
    'secondary': '#A0917A',    # Soft taupe
    'accent': '#5D5346',       # Rich dark brown
    'positive': '#5B8FA3',     # Muted teal/blue (distinguishable from orange)
    'neutral': '#9C8E7A',      # Medium warm tan (higher contrast)
    'negative': '#C17D3D',     # Warm amber/orange (replaces rose)
    'mixed': '#7B6B8F',        # Deeper purple (more saturated)
    'background': '#F5F3EF',   # Warm light beige
    'text': '#2D2D2D'          # Dark charcoal grey
}

# Set seaborn style with Claude-inspired theme
sns.set_theme(style="whitegrid", palette=[
    CLAUDE_COLORS['primary'], 
    CLAUDE_COLORS['secondary'], 
    CLAUDE_COLORS['accent'],
    CLAUDE_COLORS['positive'],
    CLAUDE_COLORS['neutral']
])
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#FEFEFE'
plt.rcParams['text.color'] = CLAUDE_COLORS['text']
plt.rcParams['axes.labelcolor'] = CLAUDE_COLORS['text']
plt.rcParams['xtick.color'] = CLAUDE_COLORS['text']
plt.rcParams['ytick.color'] = CLAUDE_COLORS['text']

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
    search_endpoint = os.getenv('SEARCH_ENDPOINT')
    search_key = os.getenv('SEARCH_KEY')
    index_name = 'ai-articles-index'
    
    if not search_endpoint or not search_key:
        st.error("⚠️ Azure Search credentials not found. Please check your .env file.")
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
    
    # Build filter string
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
    """Retrieve all articles for analytics"""
    return search_articles("*", top=1000)

def display_article_card(article):
    """Display a single article in a card format"""
    sentiment = article.get('sentiment_overall', 'neutral')
    sentiment_emoji = {
        'positive': '✨',  # Sparkle for positive
        'neutral': '�',   # Document for neutral
        'negative': '⚠️',  # Warning for negative
        'mixed': '�'     # Cycle for mixed
    }
    
    # Sentiment color badges
    sentiment_colors = {
        'positive': CLAUDE_COLORS['positive'],
        'neutral': CLAUDE_COLORS['neutral'],
        'negative': CLAUDE_COLORS['negative'],
        'mixed': CLAUDE_COLORS['mixed']
    }
    
    with st.container():
        st.markdown(f"### {article['title']}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
        with col2:
            sentiment_color = sentiment_colors.get(sentiment, CLAUDE_COLORS['neutral'])
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
        
        # Content preview
        content = article.get('content', '')
        if len(content) > 300:
            st.markdown(f"{content[:300]}...")
        else:
            st.markdown(content)
        
        # Key phrases
        key_phrases = article.get('key_phrases', [])
        if key_phrases:
            st.markdown(f"**Key Topics:** {', '.join(key_phrases[:5])}")
        
        st.markdown(f"[Read Full Article]({article['link']})")
        st.markdown("---")

def main():
    """Main application"""
    
    # Custom CSS for Claude-inspired styling - beige and dark grey theme
    st.markdown("""
        <style>
        /* Import Libre Baskerville font */
        @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap');
        
        /* Main title styling - dark grey with Libre Baskerville */
        h1 {
            color: #2D2D2D !important;
            font-weight: 700 !important;
            font-family: 'Libre Baskerville', 'Georgia', serif !important;
            letter-spacing: -0.5px;
        }
        
        /* Subheaders with dark brown accent and Libre Baskerville */
        h2, h3 {
            color: #5D5346 !important;
            font-weight: 700 !important;
            font-family: 'Libre Baskerville', 'Georgia', serif !important;
            letter-spacing: -0.3px;
        }
        
        /* Card-like containers with beige */
        .stContainer {
            background-color: #E8E3D9;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #D4CFC3;
        }
        
        /* Buttons with muted warm theme */
        .stButton>button {
            background-color: #C17D3D;
            color: #F5F3EF;
            border-radius: 6px;
            border: none;
            font-weight: 500;
        }
        
        .stButton>button:hover {
            background-color: #A0917A;
        }
        
        /* Metrics with dark brown */
        [data-testid="stMetricValue"] {
            color: #5D5346;
        }
        
        /* Sidebar styling with darker beige */
        [data-testid="stSidebar"] {
            background-color: #E8E3D9;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("AI Trend Monitor")
    st.markdown("*Exploring AI news trends with advanced analytics and search*")
    
    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["News", "Analytics", "About"]
    )
    
    if page == "News":
        show_news_page()
    elif page == "Analytics":
        show_analytics_page()
    else:
        show_about_page()

def show_news_page():
    """News page with search and curated sections"""
    st.header("AI News & Updates")
    
    # Two-column layout: Search on left (wider), Curated sections on right (more compact)
    col_search, col_curated = st.columns([1.6, 1])
    
    with col_search:
        st.subheader("Search Articles")
        show_search_interface()
    
    with col_curated:
        show_curated_sections()

def show_search_interface():
    """Search interface component"""
    
    # Initialize session state for pagination
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    if 'last_source' not in st.session_state:
        st.session_state.last_source = "All Sources"
    if 'last_sentiment' not in st.session_state:
        st.session_state.last_sentiment = "All Sentiments"
    
    # Search input
    query = st.text_input(
        "Search keywords",
        placeholder="e.g., machine learning, ChatGPT, AI ethics...",
        help="Enter keywords to search articles"
    )
    
    # Filters in three columns
    col1, col2, col3 = st.columns(3)
    with col1:
        sources = ["All Sources", "The Guardian", "techcrunch.com", "venturebeat.com", 
                  "arstechnica.com", "gizmodo.com"]
        source_filter = st.selectbox("Source", sources)
    
    with col2:
        sentiments = ["All Sentiments", "positive", "neutral", "negative", "mixed"]
        sentiment_filter = st.selectbox("Sentiment", sentiments)
    
    with col3:
        date_ranges = ["All Time", "Last 7 days", "Last 30 days", "Last 90 days", "Last 6 months", "Last year"]
        date_filter = st.selectbox("Date Range", date_ranges)
    
    # Check if filters changed - reset pagination
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
    
    # Search button
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
        'positive': CLAUDE_COLORS['positive'],
        'neutral': CLAUDE_COLORS['neutral'],
        'negative': CLAUDE_COLORS['negative'],
        'mixed': CLAUDE_COLORS['mixed']
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
            sentiment_color = sentiment_colors.get(sentiment, CLAUDE_COLORS['neutral'])
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

def show_curated_sections():
    """Display curated 'New' and 'Upcoming' sections"""
    
    # New Releases Section
    st.subheader("New Releases & Updates")
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
    <p style='margin-top: 1rem; font-size: 0.85rem; color: #5D5346;'><em>Updated October 2025</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Upcoming Events Section
    st.subheader("Upcoming Events & Releases")
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
    <p style='margin-top: 1rem; font-size: 0.85rem; color: #5D5346;'><em>Based on industry announcements and trends</em></p>
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
    
    st.markdown(f"**Analyzing {len(articles)} articles**")
    st.markdown("---")
    
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
    
    # Metrics row - 5 columns
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Articles", len(df))
    with col2:
        st.metric("Data Sources", df['source'].nunique())
    with col3:
        # Calculate earliest article date
        df['date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce')
        df['indexed_at_parsed'] = pd.to_datetime(df['indexed_at'], errors='coerce')
        df['date_final'] = df['date_parsed'].fillna(df['indexed_at_parsed'])
        min_date = df['date_final'].min().strftime('%b %d, %Y')
        st.metric("Earliest Article", min_date)
    with col4:
        # Calculate latest article date
        max_date = df['date_final'].max().strftime('%b %d, %Y')
        st.metric("Latest Article", max_date)
    with col5:
        # Calculate average net sentiment
        df['net_sentiment'] = df['positive_score'] - df['negative_score']
        avg_net_sentiment = df['net_sentiment'].mean()
        # Determine if positive or negative trend
        delta_label = "Positive lean" if avg_net_sentiment > 0 else "Negative lean" if avg_net_sentiment < 0 else "Neutral"
        st.metric("Avg Net Sentiment", f"{avg_net_sentiment:.3f}", delta_label)
    
    st.markdown("---")
    
    # Visualizations - Three columns for more compact layout
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.subheader("Sentiment Distribution")
        sentiment_counts = df['sentiment'].value_counts()
        
        # Create smaller pie chart with Claude colors
        fig, ax = plt.subplots(figsize=(3.5, 3))
        sentiment_colors = {
            'positive': CLAUDE_COLORS['positive'],
            'neutral': CLAUDE_COLORS['neutral'],
            'negative': CLAUDE_COLORS['negative'],
            'mixed': CLAUDE_COLORS['mixed']
        }
        color_list = [sentiment_colors.get(s, CLAUDE_COLORS['neutral']) for s in sentiment_counts.index]
        
        ax.pie(sentiment_counts.values, labels=sentiment_counts.index, 
               autopct='%1.1f%%', colors=color_list, startangle=90,
               textprops={'fontsize': 8, 'color': CLAUDE_COLORS['text']})
        ax.axis('equal')
        plt.tight_layout()
        st.pyplot(fig)
    
    with col2:
        st.subheader("Articles by Source")
        
        # Create sentiment by source crosstab
        sentiment_source = pd.crosstab(df['source'], df['sentiment'])
        
        # Calculate totals
        sentiment_source['Total'] = sentiment_source.sum(axis=1)
        sentiment_source = sentiment_source.sort_values('Total', ascending=True)
        
        # Create smaller stacked horizontal bar chart
        fig, ax = plt.subplots(figsize=(3.5, 3))
        
        # Define colors for each sentiment
        sentiment_colors_map = {
            'positive': CLAUDE_COLORS['positive'],
            'neutral': CLAUDE_COLORS['neutral'],
            'negative': CLAUDE_COLORS['negative'],
            'mixed': CLAUDE_COLORS['mixed']
        }
        
        # Plot stacked bars (excluding Total column)
        sentiment_cols = [col for col in sentiment_source.columns if col != 'Total']
        left = None
        for sentiment in sentiment_cols:
            if sentiment in sentiment_source.columns:
                color = sentiment_colors_map.get(sentiment, CLAUDE_COLORS['neutral'])
                if left is None:
                    ax.barh(sentiment_source.index, sentiment_source[sentiment], 
                           color=color, label=sentiment.title(), alpha=0.8)
                    left = sentiment_source[sentiment]
                else:
                    ax.barh(sentiment_source.index, sentiment_source[sentiment], 
                           left=left, color=color, label=sentiment.title(), alpha=0.8)
                    left = left + sentiment_source[sentiment]
        
        # Add total labels at the end of bars
        for idx, (source, total) in enumerate(sentiment_source['Total'].items()):
            ax.text(total + 0.5, idx, f'{int(total)}', 
                   va='center', fontsize=8, color=CLAUDE_COLORS['text'], fontweight='bold')
        
        ax.set_xlabel('Articles', fontsize=8, color=CLAUDE_COLORS['text'])
        ax.set_ylabel('Source', fontsize=8, color=CLAUDE_COLORS['text'])
        ax.legend(loc='lower right', fontsize=6, framealpha=0.9)
        ax.tick_params(colors=CLAUDE_COLORS['text'], labelsize=7)
        plt.tight_layout()
        st.pyplot(fig)
    
    with col3:
        st.subheader("Articles Over Time")
        
        # Parse publication dates
        df['date_parsed'] = pd.to_datetime(df['published_date'], errors='coerce')
        
        # For articles with missing publication dates, use indexed_at as fallback
        df['indexed_at_parsed'] = pd.to_datetime(df['indexed_at'], errors='coerce')
        df['date_parsed'] = df['date_parsed'].fillna(df['indexed_at_parsed'])
        
        # Sort by publication date
        df_sorted = df.sort_values('date_parsed')
        
        # Group by month and count cumulative articles
        df_sorted['month'] = df_sorted['date_parsed'].dt.to_period('M')
        monthly_counts = df_sorted.groupby('month').size()
        cumulative_counts = monthly_counts.cumsum()
        
        # Create compact area chart showing cumulative article growth
        fig, ax = plt.subplots(figsize=(3.5, 3))
        x_pos = range(len(cumulative_counts))
        ax.fill_between(x_pos, cumulative_counts.values, 
                        alpha=0.6, color=CLAUDE_COLORS['accent'])
        ax.plot(x_pos, cumulative_counts.values,
               color=CLAUDE_COLORS['accent'], linewidth=2, marker='o', markersize=4)
        
        # Set x-axis labels with months
        ax.set_xticks(x_pos)
        month_labels = [p.strftime('%b %Y') for p in cumulative_counts.index]
        ax.set_xticklabels(month_labels, rotation=45, ha='right')
        
        ax.set_xlabel('Month', fontsize=8, color=CLAUDE_COLORS['text'])
        ax.set_ylabel('Total Articles', fontsize=8, color=CLAUDE_COLORS['text'])
        ax.tick_params(colors=CLAUDE_COLORS['text'], labelsize=7)
        
        # Set y-axis to integers only
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        ax.grid(True, alpha=0.2, linestyle='--', axis='y')
        plt.tight_layout()
        st.pyplot(fig)
    
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
        
        # Two-column layout with headers at same level
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.subheader("Top Named Entities")
            if all_entities and not any(df['entities'].apply(lambda x: len(x) > 0 if x else False)):
                st.markdown("*Key topics and phrases from articles*")
            else:
                st.markdown("*Organizations, people, products, and locations mentioned in articles*")
            
            # Custom color function for darker warm tones (avoiding light yellows)
            def dark_warm_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
                import random
                # Generate colors in darker warm brown/orange/tan range
                # Using darker, more saturated colors
                colors = [
                    '#8B5A3C',  # Sienna brown
                    '#A0522D',  # Sienna
                    '#6B4423',  # Dark brown
                    '#8B4513',  # Saddle brown
                    '#704214',  # Sepia
                    '#7B3F00',  # Chocolate brown
                    '#654321',  # Dark brown
                    '#8B6914',  # Dark goldenrod
                    '#996515',  # Brown
                    '#6B5344',  # Dark taupe
                ]
                return random.choice(colors)
            
            # Create word cloud with adjusted height
            wordcloud = WordCloud(
                width=600, 
                height=300,
                background_color=CLAUDE_COLORS['background'],
                color_func=dark_warm_color_func,
                relative_scaling=0.5,
                min_font_size=8,
                max_words=100,
                contour_width=0,
                contour_color=CLAUDE_COLORS['accent']
            ).generate_from_frequencies(entity_counts)
            
            # Display word cloud with adjusted figure size
            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            plt.tight_layout(pad=0)
            st.pyplot(fig)
        
        with col2:
            st.subheader("Top 10 Topics")
            st.markdown("*Most frequently mentioned entities*")
            
            # Get top 10 entities
            top_10 = entity_counts.most_common(10)
            
            # Create HTML table with larger font size
            table_html = """<style>
.topics-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 16px;
}
.topics-table th {
    background-color: #E8E3D9;
    color: #2D2D2D;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid #C17D3D;
}
.topics-table td {
    padding: 6px 12px;
    border-bottom: 1px solid #E8E3D9;
}
.topics-table tr:hover {
    background-color: #F5F3EF;
}
.rank-col {
    width: 40px;
    text-align: center;
    color: #888;
    font-weight: 600;
}
.mentions-col {
    width: 80px;
    text-align: right;
    font-weight: 600;
    color: #C17D3D;
}
</style>
<table class="topics-table">
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
        
        # Create container column for all content
        col_content, col_spacer = st.columns([2, 1])
        
        with col_content:
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
            
            # Create two columns for selection methods (within the content column)
            col_select1, col_select2 = st.columns([2, 1])
            
            with col_select1:
                # Dropdown with top 100 entities
                selected_from_dropdown = st.selectbox(
                    "Select from top 100 entities",
                    options=top_100_entities,
                    index=0
                )
            
            with col_select2:
                # Text input for manual entry
                manual_entity = st.text_input(
                    "Or enter an entity manually",
                    placeholder="e.g., OpenAI, Google, ChatGPT"
                )
            
            # Use manual input if provided, otherwise use dropdown selection
            selected_entity = manual_entity.strip() if manual_entity.strip() else selected_from_dropdown
            
            # Filter articles that contain the selected entity
            df['has_entity'] = df['entities'].apply(
                lambda x: selected_entity in x if x else False
            )
            topic_articles = df[df['has_entity']].copy()
            
            if len(topic_articles) > 0:
                # Convert published_date to datetime
                topic_articles['date'] = pd.to_datetime(topic_articles['published_date'], errors='coerce')
                topic_articles = topic_articles.dropna(subset=['date'])
                topic_articles['date_only'] = topic_articles['date'].dt.date
                
                # Group by date for article count and average sentiment
                daily_stats = topic_articles.groupby('date_only').agg({
                    'title': 'count',  # Article count
                    'positive_score': 'mean',
                    'negative_score': 'mean'
                }).reset_index()
                daily_stats.columns = ['date', 'article_count', 'avg_positive', 'avg_negative']
                
                # Calculate net sentiment (positive - negative) ranging from -1 to +1
                daily_stats['net_sentiment'] = daily_stats['avg_positive'] - daily_stats['avg_negative']
                
                # Create compact figure with two y-axes
                fig, ax1 = plt.subplots(figsize=(8, 4))
                
                # Plot 1: Article count (left y-axis)
                color_count = CLAUDE_COLORS['primary']
                color_count_dark = '#A05A1F'  # Darker orange for better visibility
                line1 = ax1.plot(daily_stats['date'], daily_stats['article_count'], 
                        color=color_count, marker='o', linewidth=1.5, markersize=5,
                        label='Article Count', markeredgecolor='white', markeredgewidth=0.8)
                ax1.set_xlabel('Publication Date', fontsize=9, color=CLAUDE_COLORS['text'], fontweight='bold')
                ax1.set_ylabel('Article Count', fontsize=9, color=color_count_dark, fontweight='bold')
                ax1.tick_params(axis='y', labelcolor=color_count_dark, colors=color_count_dark, labelsize=8)
                ax1.tick_params(axis='x', rotation=45, colors=CLAUDE_COLORS['text'], labelsize=7)
                
                # Set y-axis to start at 0 for article count and use whole numbers only
                ax1.set_ylim(bottom=0)
                ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
                ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
                ax1.set_axisbelow(True)
                
                # Plot 2: Net sentiment (right y-axis)
                ax2 = ax1.twinx()
                color_sentiment = CLAUDE_COLORS['positive']  # Use teal color from pie chart
                color_sentiment_dark = '#3A6B7A'  # Darker teal for better visibility
                line2 = ax2.plot(daily_stats['date'], daily_stats['net_sentiment'], 
                        color=color_sentiment, marker='s', linewidth=1.5, markersize=5,
                        label='Net Sentiment', markeredgecolor='white', markeredgewidth=0.8)
                ax2.set_ylabel('Net Sentiment', fontsize=9, color=color_sentiment_dark, fontweight='bold')
                ax2.tick_params(axis='y', labelcolor=color_sentiment_dark, colors=color_sentiment_dark, labelsize=8)
                
                # Set sentiment y-axis to be symmetric around 0 (-1 to +1)
                max_abs_sentiment = max(abs(daily_stats['net_sentiment'].min()), 
                                       abs(daily_stats['net_sentiment'].max()), 0.3)
                ax2.set_ylim(-max_abs_sentiment * 1.1, max_abs_sentiment * 1.1)
                
                # Add horizontal line at y=0 for neutral sentiment
                ax2.axhline(y=0, color=CLAUDE_COLORS['neutral'], linestyle='-', 
                           linewidth=1.2, alpha=0.6, label='Neutral (0)')
                
                # Add shaded regions for positive/negative
                ax2.axhspan(0, max_abs_sentiment * 1.1, alpha=0.05, color=CLAUDE_COLORS['positive'], zorder=0)
                ax2.axhspan(-max_abs_sentiment * 1.1, 0, alpha=0.05, color=CLAUDE_COLORS['negative'], zorder=0)
                
                # Title
                plt.title(f'Trend: "{selected_entity}"', 
                         fontsize=11, color=CLAUDE_COLORS['text'], fontweight='bold', pad=20)
                
                # Combined legend - positioned above the plot area
                lines = line1 + line2
                labels = [l.get_label() for l in lines]
                ax1.legend(lines, labels, loc='lower left', bbox_to_anchor=(0, 1.02), 
                          ncol=2, fontsize=8, framealpha=0.95, borderaxespad=0)
                
                # Format x-axis
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                st.pyplot(fig)
                
                # Show summary statistics
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Total Articles", len(topic_articles))
                with col_b:
                    positive_count = (topic_articles['sentiment'] == 'positive').sum()
                    positive_pct = (positive_count / len(topic_articles)) * 100
                    st.metric("Positive", f"{positive_pct:.1f}%", f"{positive_count} articles")
                with col_c:
                    negative_count = (topic_articles['sentiment'] == 'negative').sum()
                    negative_pct = (negative_count / len(topic_articles)) * 100
                    st.metric("Negative", f"{negative_pct:.1f}%", f"{negative_count} articles")
                with col_d:
                    date_range = (topic_articles['date'].max() - topic_articles['date'].min()).days
                    st.metric("Date Range", f"{date_range} days")
            else:
                st.info(f"No articles found containing the entity '{selected_entity}'")
    
    st.markdown("---")
    
    # Net Sentiment Distribution
    st.subheader("Net Sentiment Distribution")
    
    # Create container column for all content
    col_content, col_spacer = st.columns([2, 1])
    
    with col_content:
        st.markdown("""
        This chart shows the overall sentiment spectrum of all articles. The **net sentiment score** is calculated 
        as positive score minus negative score, ranging from **-1 (very negative)** through **0 (neutral)** to **+1 (very positive)**. 
        The distribution shows how articles lean across the sentiment spectrum.
        """)
        
        # Calculate net sentiment for all articles
        df['net_sentiment'] = df['positive_score'] - df['negative_score']
        
        # Create diverging histogram with zero in the middle
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Create histogram with gradient coloring
        # Create custom colormap from orange (negative) to teal (positive)
        colors_gradient = [CLAUDE_COLORS['negative'], CLAUDE_COLORS['neutral'], CLAUDE_COLORS['positive']]
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
        ax.plot(xs, ys_scaled, color=CLAUDE_COLORS['text'], linewidth=2, alpha=0.8)
        
        # Add vertical line at zero (neutral)
        ax.axvline(x=0, color=CLAUDE_COLORS['text'], linestyle='--', 
                   linewidth=2, alpha=0.7, label='Neutral (0)')
        
        # Color the regions
        ax.axvspan(-1, 0, alpha=0.05, color=CLAUDE_COLORS['negative'], zorder=0)
        ax.axvspan(0, 1, alpha=0.05, color=CLAUDE_COLORS['positive'], zorder=0)
        
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
                      fontsize=9, color=CLAUDE_COLORS['text'], fontweight='bold')
        ax.set_ylabel('Number of Articles', fontsize=9, color=CLAUDE_COLORS['text'], fontweight='bold')
        ax.set_title('Distribution of Article Sentiment', fontsize=10, 
                    color=CLAUDE_COLORS['text'], pad=10, fontweight='bold')
        ax.tick_params(labelsize=7, colors=CLAUDE_COLORS['text'])
        ax.set_xlim(-1, 1)
        ax.legend(fontsize=7, framealpha=0.9)
        
        plt.tight_layout()
        st.pyplot(fig)
        
        # Add summary statistics
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            negative_articles = (df['net_sentiment'] < 0).sum()
            negative_pct = (negative_articles / len(df)) * 100
            st.metric("Leaning Negative", f"{negative_pct:.1f}%", f"{negative_articles} articles")
        with col_b:
            positive_articles = (df['net_sentiment'] > 0).sum()
            positive_pct = (positive_articles / len(df)) * 100
            st.metric("Leaning Positive", f"{positive_pct:.1f}%", f"{positive_articles} articles")
        with col_c:
            mean_sentiment = df['net_sentiment'].mean()
            st.metric("Mean Sentiment", f"{mean_sentiment:.3f}")
        with col_d:
            median_sentiment = df['net_sentiment'].median()
            st.metric("Median Sentiment", f"{median_sentiment:.3f}")

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
    **Phase 4 In Progress:** Interactive Web Dashboard (this app!)  
    **Phase 5 Planned:** RAG-powered chatbot with Azure OpenAI  
    **Phase 6 Planned:** Automated weekly trend reports  
    
    ---
    
    **Author:** Amanda Sumner  
    **Repository:** [github.com/PieRatCat/ai-trend-monitor](https://github.com/PieRatCat/ai-trend-monitor)
    """)

if __name__ == "__main__":
    main()
