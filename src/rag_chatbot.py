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
                api_key=os.environ["GITHUB_TOKEN"],
            )
            logger.info("GitHub Models client initialized successfully")
        except KeyError:
            logger.error("GITHUB_TOKEN not found in environment variables")
            raise
        
        # Initialize Azure AI Search client
        try:
            self.search_client = SearchClient(
                endpoint=os.environ["SEARCH_ENDPOINT"],
                index_name="ai-articles-index",
                credential=AzureKeyCredential(os.environ["SEARCH_KEY"])
            )
            logger.info("Azure AI Search client initialized successfully")
        except KeyError as e:
            logger.error(f"Azure Search credentials missing: {e}")
            raise
    
    def _detect_time_range(self, query: str) -> Optional[datetime]:
        """
        Detect temporal phrases in the query and return a cutoff date
        
        Args:
            query: User's search query
            
        Returns:
            Datetime object for the cutoff, or None if no temporal phrase detected
        """
        from datetime import datetime, timedelta
        import re
        
        query_lower = query.lower()
        now = datetime.now()
        
        # Patterns for temporal queries
        temporal_patterns = {
            r'last 24 hours?|past 24 hours?|today': timedelta(days=1),
            r'last 48 hours?|past 48 hours?': timedelta(days=2),
            r'last (\d+) days?|past (\d+) days?': None,  # Extract number
            r'this week|last week': timedelta(days=7),
            r'this month|last month': timedelta(days=30),
        }
        
        for pattern, delta in temporal_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if delta is None:
                    # Extract number of days from match groups
                    days = int(match.group(1) or match.group(2))
                    delta = timedelta(days=days)
                
                cutoff = now - delta
                logger.info(f"Detected temporal query: '{match.group()}' -> cutoff date: {cutoff.strftime('%Y-%m-%d')}")
                return cutoff
        
        return None
    
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
            # Detect if query contains temporal phrases
            temporal_cutoff = self._detect_time_range(query)
            
            # Base cutoff: June 1, 2025 (always applied)
            base_cutoff = datetime(2025, 6, 1)
            
            # Use the most restrictive cutoff
            cutoff_date = max(temporal_cutoff, base_cutoff) if temporal_cutoff else base_cutoff
            
            # Retrieve more results than needed for filtering
            # If temporal query, retrieve ALL articles (*) sorted by date descending
            search_text = "*" if temporal_cutoff else query
            search_params = {
                "search_text": search_text,
                "select": ["title", "content", "source", "published_date", "link"]
            }
            
            if temporal_cutoff:
                # For temporal queries, get many results and sort by date
                search_params["top"] = 200  # Get enough to cover recent articles
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
                        
                        # Only include articles after cutoff date
                        if article_date >= cutoff_date:
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
            
            if temporal_cutoff:
                logger.info(f"Retrieved {len(articles)} articles (filtered to {cutoff_date.strftime('%Y-%m-%d')}+) for temporal query")
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
    
    def chat(self, user_query: str, top_k: int = 5, temperature: float = 0.7) -> Dict:
        """
        Main RAG chatbot function: retrieve articles and generate answer
        
        Args:
            user_query: User's question
            top_k: Number of articles to retrieve (default: 5)
            temperature: Model temperature for response generation (default: 0.7)
            
        Returns:
            Dictionary with 'answer' and 'sources' (list of article dicts)
        """
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Retrieve relevant articles
        articles = self.retrieve_articles(user_query, top_k=top_k)
        
        if not articles:
            return {
                "answer": "I couldn't find any relevant articles for your query. Try rephrasing or asking about a different topic.",
                "sources": []
            }
        
        # Step 2: Format context
        context = self.format_context(articles)
        
        # Step 3: Create messages with system prompt and context
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that helps users understand trends in artificial intelligence news. "
                    "Answer questions based ONLY on the article content provided below. "
                    "\n\nCITATION RULES:\n"
                    "- Each article is numbered [1], [2], [3], etc. in the context\n"
                    "- When referencing information from an article, use the number in brackets like [1] or [2]\n"
                    "- Place the citation at the end of the sentence or claim\n"
                    "- Example: 'OpenAI announced a new model [1]' or 'AI investments are declining [2][3]'\n"
                    "- You can cite multiple sources if relevant: [1][2]\n\n"
                    "If the articles don't contain enough information to fully answer the question, say so honestly. "
                    "Be concise and factual. Focus on what the articles actually say."
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
                "answer": "I couldn't find any relevant articles for your query.",
                "sources": []
            }
        
        # Format context with reduced token budget due to conversation history
        # History can be 500-1500 tokens, so reduce context budget accordingly
        context = self.format_context(articles, max_tokens=3500)  # Reduced from 5000 to account for history
        
        # Build messages with system prompt, history, and new context
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that helps users understand trends in artificial intelligence news. "
                    "Answer questions based on the article content provided and previous conversation context. "
                    "\n\nCITATION RULES:\n"
                    "- Each article is numbered [1], [2], [3], etc.\n"
                    "- Use these numbers in brackets to cite sources\n"
                    "- Place citations at the end of sentences: 'The model was released [1]'\n"
                    "- You can cite multiple sources: [1][2]\n\n"
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
