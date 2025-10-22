"""
RAG Chatbot for AI Trend Monitor
Uses GitHub Models (GPT-4.1-mini) + Azure AI Search

This module provides a Retrieval-Augmented Generation (RAG) chatbot that:
1. Retrieves relevant articles from Azure AI Search
2. Formats them as context for the LLM
3. Generates answers grounded in the article content
"""
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_env_var(key: str) -> str:
    """
    Get environment variable from .env or system environment
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        KeyError: If variable is not found
    """
    value = os.getenv(key)
    if value is None:
        raise KeyError(f"{key} not found in environment variables")
    return value


class RAGChatbot:
    """RAG-powered chatbot for querying AI news articles"""
    
    def __init__(self, model: str = "openai/gpt-4.1-mini"):
        """
        Initialize the RAG chatbot with GitHub Models and Azure AI Search
        
        Args:
            model: Model identifier (default: openai/gpt-4.1-mini)
        """
        self.model = model
        
        # Initialize GitHub Models client
        try:
            self.llm_client = OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=get_env_var("GITHUB_TOKEN"),
            )
            logger.info("GitHub Models client initialized successfully")
        except KeyError:
            logger.error("GITHUB_TOKEN not found in environment variables")
            raise
        
        # Initialize Azure AI Search client
        try:
            self.search_client = SearchClient(
                endpoint=get_env_var("SEARCH_ENDPOINT"),
                index_name="ai-articles-index",
                credential=AzureKeyCredential(get_env_var("SEARCH_KEY"))
            )
            logger.info("Azure AI Search client initialized successfully")
        except KeyError as e:
            logger.error(f"Azure Search credentials missing: {e}")
            raise
    
    def _detect_time_range(self, query: str):
        """
        Detect temporal phrases in the query and return a date range
        
        Args:
            query: User's search query
            
        Returns:
            Tuple of (start_date, end_date) where:
            - start_date: Earliest date to include (inclusive)
            - end_date: Latest date to include (exclusive), or None for open-ended
            Or None if no temporal phrase detected
        """
        from datetime import datetime, timedelta
        import re
        
        query_lower = query.lower()
        now = datetime.now()
        
        # Skip temporal detection if query contains date context phrases
        if 'today is' in query_lower or 'today\'s date is' in query_lower:
            # This is just providing date context, not asking for today's articles
            logger.info("Skipping temporal detection - query contains date context phrase")
            return None
        
        # Current year and month for relative dates
        current_year = now.year
        current_month = now.month
        
        # Patterns for temporal queries (ordered from specific to general)
        temporal_patterns = {
            # Specific time periods
            r'last 24 hours?|past 24 hours?|today|in the last day': timedelta(days=1),
            r'last 48 hours?|past 48 hours?': timedelta(days=2),
            r'last (\d+) days?|past (\d+) days?|in the (?:last|past) (\d+) days?': None,  # Extract number
            
            # Week-based
            r'(?:in the )?past weeks?': timedelta(days=7),
            r'(?:in the )?last weeks?': None,  # Special: previous calendar week
            r'(?:in the )?next weeks?': None,  # Special: next calendar week
            r'this weeks?': None,  # Special: current week
            r'last (\d+) weeks?|past (\d+) weeks?': None,  # Extract number * 7
            
            # Month-based  
            r'(?:in the )?past months?': timedelta(days=30),
            r'(?:in the )?last months?': None,  # Special: previous calendar month
            r'(?:in the )?next months?': None,  # Special: next calendar month
            r'this months?': None,  # Special: current month
            r'last (\d+) months?|past (\d+) months?': None,  # Extract number * 30
            
            # Year-based
            r'(?:before|by|until) (?:the )?end of (?:this )?year': None,  # Until end of year
            r'(?:in |during )?this year|in (\d{4})': None,  # Specific year
            r'(?:before|until|by) (\d{4})': None,  # Before specific year
            
            # Recent/latest
            r'recent(?:ly)?|latest|newest': timedelta(days=30),
        }
        
        for pattern, delta in temporal_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if delta is None:
                    # Special handling based on pattern
                    if 'end of' in pattern and 'year' in pattern:
                        # "before end of this year" - this is asking about FUTURE articles
                        # Since we don't have future articles, return None to indicate no temporal filtering
                        # The LLM will understand from the context that we only have articles up to today
                        logger.info(f"Detected future temporal query: 'before end of year' -> no filtering (relies on available articles)")
                        return None
                    
                    elif 'this month' in match.group():
                        # "this month" - articles from current calendar month only
                        start_date = datetime(current_year, current_month, 1)
                        # End date is first day of next month
                        if current_month == 12:
                            end_date = datetime(current_year + 1, 1, 1)
                        else:
                            end_date = datetime(current_year, current_month + 1, 1)
                        logger.info(f"Detected temporal query: 'this month' -> date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({now.strftime('%B')} only)")
                        return (start_date, end_date)
                    
                    elif 'last month' in match.group():
                        # "last month" - articles from previous calendar month ONLY
                        if current_month == 1:
                            # January -> previous month is December of last year
                            prev_month = 12
                            prev_year = current_year - 1
                        else:
                            prev_month = current_month - 1
                            prev_year = current_year
                        start_date = datetime(prev_year, prev_month, 1)
                        # End date is first day of current month
                        end_date = datetime(current_year, current_month, 1)
                        month_name = start_date.strftime('%B')
                        logger.info(f"Detected temporal query: 'last month' -> date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({month_name} only)")
                        return (start_date, end_date)
                    
                    elif 'next month' in match.group():
                        # "next month" - future query, no articles available
                        logger.info(f"Detected future temporal query: 'next month' -> no articles available")
                        return None
                    
                    elif 'this week' in match.group():
                        # "this week" - articles from Monday of current week to now
                        days_since_monday = now.weekday()  # 0=Monday, 6=Sunday
                        start_date = now - timedelta(days=days_since_monday)
                        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        logger.info(f"Detected temporal query: 'this week' -> from {start_date.strftime('%Y-%m-%d')} (Monday) onwards")
                        return (start_date, None)  # Open-ended (up to now)
                    
                    elif 'last week' in match.group():
                        # "last week" - articles from previous calendar week ONLY (Mon-Sun)
                        days_since_monday = now.weekday()  # 0=Monday, 6=Sunday
                        monday_this_week = now - timedelta(days=days_since_monday)
                        start_date = monday_this_week - timedelta(days=7)
                        end_date = monday_this_week  # Exclude this week
                        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        logger.info(f"Detected temporal query: 'last week' -> date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} (previous week only)")
                        return (start_date, end_date)
                    
                    elif 'next week' in match.group():
                        # "next week" - future query, no articles available
                        logger.info(f"Detected future temporal query: 'next week' -> no articles available")
                        return None
                    
                    elif 'this year' in match.group() or (match.lastindex and match.group(match.lastindex).isdigit() and len(match.group(match.lastindex)) == 4):
                        # Specific year like "in 2025" or "this year"
                        year = int(match.group(match.lastindex)) if match.lastindex and match.group(match.lastindex).isdigit() else current_year
                        start_date = datetime(year, 1, 1)
                        logger.info(f"Detected temporal query: year {year} -> from {start_date.strftime('%Y-%m-%d')} onwards")
                        return (start_date, None)  # Open-ended
                    
                    elif 'weeks?' in pattern:
                        # Extract weeks and convert to days
                        weeks = int(match.group(1) or match.group(2) or match.group(3) or 1)
                        delta = timedelta(days=weeks * 7)
                    
                    elif 'months?' in pattern:
                        # Extract months and convert to days (approximate)
                        months = int(match.group(1) or match.group(2) or match.group(3) or 1)
                        delta = timedelta(days=months * 30)
                    
                    elif 'days?' in pattern:
                        # Extract number of days
                        days = int(match.group(1) or match.group(2) or match.group(3))
                        delta = timedelta(days=days)
                    
                    else:
                        logger.warning(f"Unhandled temporal pattern: {pattern}")
                        continue
                
                # For other temporal queries, return open-ended range (cutoff to now)
                cutoff = now - delta
                logger.info(f"Detected temporal query: '{match.group()}' -> cutoff date: {cutoff.strftime('%Y-%m-%d')} (open-ended)")
                return (cutoff, None)  # None means no end date (up to present)
        
        return None
    
    def _is_future_oriented_query(self, query: str) -> bool:
        """
        Detect if query is asking about future events/plans/releases
        These queries should use broad retrieval (*) to find mentions in articles
        
        Args:
            query: User's search query
            
        Returns:
            True if query is future-oriented, False otherwise
        """
        import re
        
        query_lower = query.lower()
        
        # Future-oriented keywords
        future_keywords = [
            r'\bupcoming\b',
            r'\bfuture\b',
            r'\bnext\s+(week|month|year|quarter)',
            r'\blater\b',
            r'\bsoon\b',
            r'\bplanned\b',
            r'\bexpected\b',
            r'\banticipated\b',
            r'\bcoming\b',
            r'\bwill\s+be\b',
            r'\bto\s+be\s+(released|launched|announced)\b',
            r'\bin\s+2026\b',
            r'\bin\s+2027\b',
            r'\bearly\s+2026\b',
            r'\blate\s+2025\b',
            r'\bevents?\s+in\b',
            r'\breleases?\s+in\b',
            r'\blaunch(es|ing)?\s+in\b',
            r'\broadmap\b',
            r'\bschedule(d)?\b',
        ]
        
        for pattern in future_keywords:
            if re.search(pattern, query_lower):
                logger.info(f"Detected future-oriented query pattern: '{pattern}'")
                return True
        
        return False
    
    def retrieve_articles(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve relevant articles from Azure AI Search (filtered to June 1, 2025 onwards)
        Also detects temporal queries like "last 24 hours" for more specific filtering
        
        Args:
            query: User's search query
            top_k: Number of articles to retrieve (default: 5)
            
        Returns:
            List of article dictionaries with title, content, source, date, link
        """
        from datetime import datetime
        from dateutil import parser as date_parser
        
        try:
            # Detect if query contains temporal phrases or is future-oriented
            temporal_range = self._detect_time_range(query)
            is_future_query = self._is_future_oriented_query(query)
            
            # Base cutoff: June 1, 2025 (always applied as minimum)
            base_cutoff = datetime(2025, 6, 1)
            
            # Determine date filtering parameters
            if temporal_range:
                start_date, end_date = temporal_range
                # Use the most restrictive start date (later of base or temporal)
                cutoff_date = max(start_date, base_cutoff)
            else:
                cutoff_date = base_cutoff
                end_date = None
            
            # Retrieve more results than needed for filtering
            # If temporal query OR future-oriented query, retrieve ALL articles (*) sorted by date
            use_broad_search = temporal_range is not None or is_future_query
            search_text = "*" if use_broad_search else query
            search_params = {
                "search_text": search_text,
                "select": ["title", "content", "source", "published_date", "link"]
            }
            
            if use_broad_search:
                # For temporal/future queries, get many results and sort by date
                search_params["top"] = 200  # Get enough to cover all articles
                search_params["order_by"] = ["published_date desc"]  # Most recent first
            else:
                search_params["top"] = top_k * 3
            
            results = self.search_client.search(**search_params)
            
            articles = []
            for result in results:
                # Parse and filter by date
                date_str = result.get("published_date", "")
                if date_str:
                    try:
                        article_date = date_parser.parse(date_str)
                        # Handle timezone-aware dates
                        if article_date.tzinfo:
                            article_date = article_date.replace(tzinfo=None)
                        
                        # Filter by date range
                        if article_date >= cutoff_date:
                            # If end_date is specified, also check upper bound
                            if end_date is None or article_date < end_date:
                                articles.append({
                                    "title": result.get("title", ""),
                                    "content": result.get("content", "")[:3000],  # Get more content, will be truncated in format_context() based on token budget
                                    "source": result.get("source", ""),
                                    "date": date_str,
                                    "link": result.get("link", "")
                                })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse date '{date_str}': {e}")
                        continue
            
            # Sort by date descending (most recent first)
            articles.sort(key=lambda x: x['date'], reverse=True)
            
            # Return top K articles
            articles = articles[:top_k]
            
            if temporal_range:
                date_range_str = f"{cutoff_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}" if end_date else f"{cutoff_date.strftime('%Y-%m-%d')}+"
                logger.info(f"Retrieved {len(articles)} articles (filtered to {date_range_str}) for temporal query")
            elif is_future_query:
                logger.info(f"Retrieved {len(articles)} articles (broad search for future-oriented query)")
            else:
                logger.info(f"Retrieved {len(articles)} articles (filtered to June 2025+) for query: {query}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles: {e}")
            return []
    
    def format_context(self, articles: List[Dict], max_tokens: int = 5000) -> str:
        """
        Format retrieved articles as context for the LLM with token budget management
        
        Args:
            articles: List of article dictionaries
            max_tokens: Maximum tokens for context (default: 5000 to leave room for system prompt + response)
            
        Returns:
            Formatted string with all article content, truncated to fit token budget
        """
        if not articles:
            return "No relevant articles found."
        
        # Rough token estimate: 1 token ≈ 4 characters
        chars_per_token = 4
        max_chars = max_tokens * chars_per_token
        
        # Calculate adaptive content length per article
        num_articles = len(articles)
        # Reserve chars for metadata (title, source, date, URL, formatting)
        metadata_overhead_per_article = 200  # ~50 tokens per article for metadata
        available_chars = max_chars - (num_articles * metadata_overhead_per_article)
        chars_per_article = max(300, available_chars // num_articles)  # Minimum 300 chars per article
        
        logger.info(f"Token budget: {max_tokens} tokens (~{max_chars} chars) for {num_articles} articles = ~{chars_per_article} chars/article")
        
        context = "Here are relevant articles from the AI news database. Use numbered references [1], [2], etc. to cite them:\n\n"
        
        for i, article in enumerate(articles, 1):
            content = article['content'][:chars_per_article]
            if len(article['content']) > chars_per_article:
                content += "... [truncated]"
            
            context += f"[{i}] {article['title']}\n"
            context += f"    Source: {article['source']}\n"
            context += f"    Date: {article['date']}\n"
            context += f"    URL: {article['link']}\n"
            context += f"    Content: {content}\n\n"
        
        return context
    
    def chat(self, user_query: str, top_k: int = 5, temperature: float = 0.7, search_override: str = None) -> Dict:
        """
        Main RAG chatbot function: retrieve articles and generate answer
        
        Args:
            user_query: User's question
            top_k: Number of articles to retrieve (default: 5)
            temperature: Model temperature for response generation (default: 0.7)
            search_override: Optional search query to override default retrieval (default: None, uses user_query)
            
        Returns:
            Dictionary with 'answer' and 'sources' (list of article dicts)
        """
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Retrieve relevant articles (use search_override if provided, otherwise use user_query)
        search_query = search_override if search_override else user_query
        if search_override:
            logger.info(f"Using search override: {search_override}")
        articles = self.retrieve_articles(search_query, top_k=top_k)
        
        if not articles:
            return {
                "answer": "I couldn't find any relevant articles for your query. Try rephrasing or asking about a different AI topic!",
                "sources": []
            }
        
        # Step 2: Format context
        context = self.format_context(articles)
        
        # Step 3: Create messages with system prompt and context
        # Add current date context for temporal awareness
        current_date = datetime.now().strftime("%B %d, %Y")
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are Dot, a friendly and knowledgeable AI assistant that helps users understand trends in artificial intelligence news. "
                    f"Today's date is {current_date}. Answer questions based ONLY on the article content provided.\n\n"
                    "IMPORTANT: Focus exclusively on AI-related content. If articles contain non-AI topics, ignore them. "
                    "Only discuss artificial intelligence, machine learning, large language models, AI companies, AI products, and related technologies.\n\n"
                    "CITATION RULES:\n"
                    "- Articles are numbered [1], [2], [3], etc.\n"
                    "- Cite sources in brackets at the end of sentences: 'OpenAI released a new model [1]'\n"
                    "- Combine multiple sources when relevant: [1][2]\n\n"
                    "HANDLING LIMITED INFORMATION:\n"
                    "- If articles only mention the topic briefly (e.g., in a list or passing reference), acknowledge this and provide what context IS available\n"
                    "- Example: 'The articles mention [Company X] briefly: it appears in a list of conference speakers [1][2] and is described as a U.K. self-driving startup that received investment [3]. However, the articles don't provide detailed information about what the company does or why it's newsworthy.'\n"
                    "- Be helpful by extracting ANY available context, even if limited\n\n"
                    "If articles don't fully answer the question, say so honestly. For future events, explain you only have data up to today. "
                    "Be concise and factual."
                )
            },
            {
                "role": "user",
                "content": f"{context}\n\nUser Question: {user_query}"
            }
        ]
        
        # Step 4: Get response from model
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=1,
                max_tokens=1000,
            )
            
            answer = response.choices[0].message.content
            logger.info("Generated answer successfully")
            
            return {
                "answer": answer,
                "sources": articles  # Include sources for citation
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "answer": f"Sorry, I encountered an error generating a response: {str(e)}",
                "sources": articles
            }
    
    def chat_with_history(
        self, 
        user_query: str, 
        conversation_history: List[Dict],
        top_k: int = 5,
        temperature: float = 0.7
    ) -> Dict:
        """
        Chat with conversation history for multi-turn conversations
        
        Args:
            user_query: User's current question
            conversation_history: List of previous message dicts with 'role' and 'content'
            top_k: Number of articles to retrieve
            temperature: Model temperature
            
        Returns:
            Dictionary with 'answer' and 'sources'
        """
        logger.info(f"Processing query with history: {user_query}")
        
        # Retrieve articles for current query
        articles = self.retrieve_articles(user_query, top_k=top_k)
        
        if not articles:
            return {
                "answer": "I couldn't find any relevant articles for your query. Try rephrasing or asking about a different AI topic!",
                "sources": []
            }
        
        # Format context with reduced token budget due to conversation history
        # History can be 500-1500 tokens, so reduce context budget accordingly
        context = self.format_context(articles, max_tokens=3500)  # Reduced from 5000 to account for history
        
        # Build messages with system prompt, history, and new context
        # Add current date context for temporal awareness
        current_date = datetime.now().strftime("%B %d, %Y")
        
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are Dot, a friendly and knowledgeable AI assistant that helps users understand trends in artificial intelligence news. "
                    f"Today's date is {current_date}. Answer questions using the article content and previous conversation context.\n\n"
                    "IMPORTANT: Focus exclusively on AI-related content. Ignore non-AI topics even if present in articles.\n\n"
                    "CITATION RULES:\n"
                    "- Articles are numbered [1], [2], [3], etc.\n"
                    "- Cite sources in brackets: 'The model was released [1]'\n"
                    "- Combine multiple sources: [1][2]\n\n"
                    "HANDLING LIMITED INFORMATION:\n"
                    "- If articles only mention the topic briefly, acknowledge this and provide what context IS available\n"
                    "- Be helpful by extracting ANY available context, even if limited\n\n"
                    "Be concise and factual."
                )
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add new query with context
        messages.append({
            "role": "user",
            "content": f"{context}\n\nUser Question: {user_query}"
        })
        
        # Generate response
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=1,
                max_tokens=1000,
            )
            
            answer = response.choices[0].message.content
            logger.info("Generated answer with history successfully")
            
            return {
                "answer": answer,
                "sources": articles
            }
            
        except Exception as e:
            logger.error(f"Error generating response with history: {e}")
            return {
                "answer": f"Sorry, I encountered an error: {str(e)}",
                "sources": articles
            }


# Convenience function for simple usage
def chat(user_query: str, top_k: int = 5) -> str:
    """
    Simple function for one-off queries without conversation history
    
    Args:
        user_query: User's question
        top_k: Number of articles to retrieve
        
    Returns:
        Answer string
    """
    chatbot = RAGChatbot()
    result = chatbot.chat(user_query, top_k=top_k)
    return result["answer"]


# Example usage for testing
if __name__ == "__main__":
    # Initialize chatbot
    chatbot = RAGChatbot()
    
    # Test query
    user_question = "What are the latest trends in large language models?"
    result = chatbot.chat(user_question)
    
    print(f"Question: {user_question}")
    print(f"\nAnswer: {result['answer']}")
    print(f"\nSources ({len(result['sources'])} articles):")
    for i, source in enumerate(result['sources'], 1):
        print(f"  {i}. {source['title']} ({source['source']})")
