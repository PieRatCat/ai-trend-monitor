"""
Weekly AI Trend Report Generator
Analyzes the past 7 days of articles and generates a comprehensive report
"""

import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI
from collections import Counter

# Optional: Email sending (requires azure-communication-email package)
try:
    from azure.communication.email import EmailClient
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logging.warning("azure-communication-email not installed. Email sending disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WeeklyReportGenerator:
    def __init__(self):
        """Initialize with Azure Search and OpenAI clients"""
        load_dotenv()
        
        # Azure AI Search setup
        search_endpoint = os.getenv('SEARCH_ENDPOINT')
        search_key = os.getenv('SEARCH_KEY')
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name='ai-articles-index',
            credential=AzureKeyCredential(search_key)
        )
        
        # OpenAI/GitHub Models setup
        github_token = os.getenv('GITHUB_TOKEN')
        self.openai_client = OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=github_token
        )
        
        self.model = "gpt-4.1-mini"
    
    def get_weekly_articles(self, days=7):
        """Retrieve articles from the past N days"""
        logging.info(f"Fetching articles from past {days} days...")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Search - get all recent articles (can't rely on Azure Search date filter with mixed formats)
        results = self.search_client.search(
            search_text="*",
            select=["title", "content", "link", "source", "published_date",
                   "sentiment_overall", "sentiment_positive_score", 
                   "sentiment_negative_score", "key_phrases", "entities"],
            top=1000,
            order_by=["published_date desc"]
        )
        
        # Client-side filtering for last N days (handle mixed date formats)
        articles = []
        for article in results:
            pub_date_str = article.get('published_date', '')
            if not pub_date_str:
                continue
            
            try:
                # Try ISO format first (2025-10-20T10:15:07.00Z)
                if 'T' in pub_date_str:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                else:
                    # Try RFC 822/2822 format (Mon, 20 Oct 2025 08:15:50 +0000 or GMT)
                    from email.utils import parsedate_to_datetime
                    # Replace GMT with +0000 for better parsing
                    normalized = pub_date_str.replace(' GMT', ' +0000')
                    pub_date = parsedate_to_datetime(normalized)
                
                # Only include articles from the last N days
                if pub_date.replace(tzinfo=None) >= cutoff_date:
                    articles.append(article)
            except Exception as e:
                # Skip articles with unparseable dates (don't log to reduce noise)
                continue
        
        # Sort by date descending
        articles.sort(key=lambda x: self._parse_date_safe(x.get('published_date', '')), reverse=True)
        
        logging.info(f"Retrieved {len(articles)} articles from past {days} days (filtered from search results)")
        return articles
    
    def _parse_date_safe(self, date_str):
        """Safely parse date string, return datetime object or epoch"""
        if not date_str:
            return datetime(1970, 1, 1)
        
        try:
            # Try ISO format first (2025-10-20T10:15:07.00Z)
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Try RFC 822/2822 format (Mon, 20 Oct 2025 08:15:50 +0000 or GMT)
                from email.utils import parsedate_to_datetime
                # Replace GMT with +0000 for better parsing
                normalized = date_str.replace(' GMT', ' +0000')
                return parsedate_to_datetime(normalized)
        except Exception as e:
            # If all parsing fails, return epoch
            return datetime(1970, 1, 1)
    
    def analyze_statistics(self, articles):
        """Generate statistical insights from articles"""
        logging.info("Analyzing weekly statistics...")
        
        # Entity frequency
        all_entities = []
        for article in articles:
            entities = article.get('entities', [])
            
            # Parse JSON string if needed
            if isinstance(entities, str):
                import json
                try:
                    entities = json.loads(entities)
                except:
                    entities = []
            
            if isinstance(entities, list):
                # Entities are stored as dicts with 'text', 'category', 'confidence'
                for entity in entities:
                    if isinstance(entity, dict):
                        all_entities.append(entity.get('text', ''))
                    else:
                        # Fallback for string entities
                        all_entities.append(str(entity))
        
        entity_counts = Counter(all_entities)
        
        # Sentiment distribution
        sentiments = [a.get('sentiment_overall', 'neutral') for a in articles]
        sentiment_counts = Counter(sentiments)
        
        # Source distribution
        sources = [a.get('source', 'Unknown') for a in articles]
        source_counts = Counter(sources)
        
        # Calculate average net sentiment
        net_sentiments = [
            a.get('sentiment_positive_score', 0) - a.get('sentiment_negative_score', 0)
            for a in articles
        ]
        avg_net_sentiment = sum(net_sentiments) / len(net_sentiments) if net_sentiments else 0
        
        stats = {
            'total_articles': len(articles),
            'top_entities': entity_counts.most_common(20),
            'sentiment_distribution': dict(sentiment_counts),
            'avg_net_sentiment': avg_net_sentiment,
            'source_distribution': dict(source_counts.most_common(10)),
            'date_range': {
                'start': min(a.get('published_date', '') for a in articles) if articles else '',
                'end': max(a.get('published_date', '') for a in articles) if articles else ''
            }
        }
        
        return stats
    
    def categorize_articles(self, articles):
        """Categorize articles by topic for better analysis"""
        categories = {
            'models_software': [],
            'research_technical': [],
            'tools_platforms': [],
            'industry_business': [],
            'other': []
        }
        
        # Keywords for AI development focus
        dev_keywords = ['model', 'gpt', 'llm', 'release', 'version', 'update', 'api', 
                       'training', 'dataset', 'parameter', 'inference', 'fine-tuning',
                       'transformer', 'neural', 'algorithm', 'framework', 'library',
                       'anthropic', 'openai', 'claude', 'gemini', 'copilot', 'chatgpt']
        
        research_keywords = ['research', 'study', 'paper', 'breakthrough', 'advance',
                            'technique', 'method', 'architecture', 'performance']
        
        tools_keywords = ['platform', 'tool', 'api', 'sdk', 'service', 'feature',
                         'integration', 'workflow', 'automation', 'code']
        
        for article in articles:
            title_lower = article.get('title', '').lower()
            content_lower = article.get('content', '')[:500].lower()
            text = title_lower + ' ' + content_lower
            
            # Prioritize AI development content
            if any(kw in text for kw in dev_keywords):
                categories['models_software'].append(article)
            elif any(kw in text for kw in research_keywords):
                categories['research_technical'].append(article)
            elif any(kw in text for kw in tools_keywords):
                categories['tools_platforms'].append(article)
            elif any(kw in text for kw in ['funding', 'startup', 'company', 'job', 'investment']):
                categories['industry_business'].append(article)
            else:
                categories['other'].append(article)
        
        return categories
    
    def build_context_for_llm(self, articles, stats):
        """Build condensed context covering ALL articles with focus on AI development"""
        logging.info("Building context for report generation...")
        
        # Categorize articles by topic
        categories = self.categorize_articles(articles)
        
        context = f"""You are analyzing ALL {stats['total_articles']} AI articles from the past week.

COVERAGE STATISTICS:
- Total Articles: {stats['total_articles']}
- Date Range: {stats['date_range']['start']} to {stats['date_range']['end']}
- Sentiment Distribution: {stats['sentiment_distribution']}
- Average Net Sentiment: {stats['avg_net_sentiment']:.3f}

ARTICLE BREAKDOWN BY CATEGORY:
- AI Models & Software: {len(categories['models_software'])} articles
- Research & Technical: {len(categories['research_technical'])} articles
- Tools & Platforms: {len(categories['tools_platforms'])} articles
- Industry & Business: {len(categories['industry_business'])} articles
- Other: {len(categories['other'])} articles

TOP ENTITIES (Organizations, People, Products):
{', '.join([f"{entity} ({count})" for entity, count in stats['top_entities'][:20]])}

TOP SOURCES:
{', '.join([f"{source} ({count})" for source, count in stats['source_distribution'].items()])}

=== AI MODELS & SOFTWARE RELEASES ({len(categories['models_software'])} articles) ===
"""
        
        # Prioritize AI development content - show more detail
        for i, article in enumerate(categories['models_software'][:30], 1):
            title = article.get('title', 'Untitled')
            source = article.get('source', 'Unknown')
            sentiment = article.get('sentiment_overall', 'neutral')
            content = article.get('content', '')[:200]
            
            context += f"\n{i}. [{source}] {title} ({sentiment})\n   {content}...\n"
        
        context += f"\n\n=== RESEARCH & TECHNICAL ({len(categories['research_technical'])} articles) ===\n"
        for i, article in enumerate(categories['research_technical'][:20], 1):
            title = article.get('title', 'Untitled')
            source = article.get('source', 'Unknown')
            context += f"{i}. [{source}] {title}\n"
        
        context += f"\n\n=== TOOLS & PLATFORMS ({len(categories['tools_platforms'])} articles) ===\n"
        for i, article in enumerate(categories['tools_platforms'][:20], 1):
            title = article.get('title', 'Untitled')
            source = article.get('source', 'Unknown')
            context += f"{i}. [{source}] {title}\n"
        
        context += f"\n\n=== INDUSTRY NEWS ({len(categories['industry_business'])} articles - mention briefly) ===\n"
        for i, article in enumerate(categories['industry_business'][:10], 1):
            title = article.get('title', 'Untitled')
            context += f"{i}. {title}\n"
        
        return context
    
    def generate_report_section(self, section_name, prompt, context, max_tokens=800):
        """Generate a single report section using GPT-4o-mini"""
        logging.info(f"Generating section: {section_name}...")
        
        full_prompt = f"""{context}

---

{prompt}

Write in a professional, technical style for AI/ML developers and practitioners. Focus on actionable technical information. Be specific about model names, versions, capabilities, and technical specifications. 

CRITICAL: Do NOT use emojis, exclamation marks, or casual language. Do NOT use numbered lists in the Executive Summary. Each section covers DIFFERENT content - do not repeat. Complete all thoughts fully.
"""
        
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a senior AI engineer writing content for an HTML email newsletter. Write ONLY the body paragraphs - no headers, no section titles, no markdown formatting. Use plain paragraphs separated by blank lines. Be technical and specific. NEVER use emojis or exclamation marks. Complete all sentences fully - the content will be truncated at max_tokens so ensure every sentence is complete before moving to the next."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def extract_entities_from_content(self, report_sections):
        """Use GPT to extract key companies, products, and technologies mentioned in the generated content"""
        # Combine all sections
        all_content = "\n\n".join([
            report_sections.get('executive_summary', ''),
            report_sections.get('models_and_research', ''),
            report_sections.get('tools_and_platforms', '')
        ])
        
        prompt = f"""Read the following AI newsletter content and extract ONLY the specific companies, products, models, and technologies that are explicitly mentioned.

Content:
{all_content}

List each unique entity mentioned (companies like OpenAI, products like ChatGPT, models like GPT-4, technologies like PyTorch, etc.).
Return ONLY the entity names, one per line, no explanations, no categories, no numbering.
Only include entities that are CLEARLY mentioned in the text above.
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You extract specific entity names from text. Return only the names, one per line."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0
            )
            
            # Parse the response into a list
            entities_text = response.choices[0].message.content.strip()
            entities = [line.strip() for line in entities_text.split('\n') if line.strip()]
            
            logging.info(f"Extracted {len(entities)} entities from generated content: {', '.join(entities[:10])}")
            return entities
            
        except Exception as e:
            logging.error(f"Failed to extract entities: {e}")
            return []
    
    def generate_full_report(self):
        """Generate complete weekly report"""
        logging.info("=== Starting Weekly Report Generation ===")
        
        # Step 1: Fetch articles
        articles = self.get_weekly_articles(days=7)
        
        if len(articles) == 0:
            logging.warning("No articles found for the past week. Aborting report generation.")
            return None
        
        # Step 2: Analyze statistics
        stats = self.analyze_statistics(articles)
        
        # Step 3: Build context
        context = self.build_context_for_llm(articles, stats)
        
        # Step 4: Generate report sections (3 sections only - streamlined)
        report_sections = {}
        
        report_sections['executive_summary'] = self.generate_report_section(
            "Executive Summary",
            f"Write a single flowing paragraph (150-200 words) summarizing the week's most significant AI developments. Focus on the overall narrative. NO section headers, NO markdown, NO bullet points - just one cohesive paragraph. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=400
        )
        
        report_sections['models_and_research'] = self.generate_report_section(
            "Models and Research",
            f"Write 3-4 flowing paragraphs about model releases, LLM updates, and research breakthroughs. Each paragraph should be 80-120 words. Include specific model names/versions, technical capabilities, and innovations. NO section headers, NO markdown, NO bullet points. Write naturally in paragraphs. Start directly with the first model - don't introduce the section. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=900
        )
        
        report_sections['tools_and_platforms'] = self.generate_report_section(
            "Tools and Platforms",
            f"Write 2-3 flowing paragraphs about developer tools, APIs, SDKs, and platforms. Each paragraph 80-120 words. Cover new features, integrations, and updates. NO section headers, NO markdown, NO bullet points. Write naturally in paragraphs. Start directly with the first tool - don't introduce the section. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=600
        )
        
        # Step 4.5: Extract key entities mentioned in the generated content
        logging.info("Extracting key entities from generated content...")
        key_entities = self.extract_entities_from_content(report_sections)
        stats['content_entities'] = key_entities  # Add to stats for entity linking
        
        # Step 5: Compile full report
        report = self.compile_report(report_sections, stats, articles)
        
        # Store for email HTML generation
        self.last_report_sections = report_sections
        self.last_stats = stats
        
        logging.info("=== Report Generation Complete ===")
        return report
    
    def compile_report(self, sections, stats, articles):
        """Compile all sections into email-friendly report format"""
        report_date = datetime.now().strftime('%B %d, %Y')
        week_start = (datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')
        
        # Format sentiment as percentage for readability
        total = stats['total_articles']
        sentiment_summary = f"{stats['sentiment_distribution'].get('positive', 0)} positive ({stats['sentiment_distribution'].get('positive', 0)/total*100:.0f}%), {stats['sentiment_distribution'].get('neutral', 0)} neutral ({stats['sentiment_distribution'].get('neutral', 0)/total*100:.0f}%), {stats['sentiment_distribution'].get('negative', 0)} negative ({stats['sentiment_distribution'].get('negative', 0)/total*100:.0f}%)"
        
        # Get top entities for display
        top_entities_list = ""
        if stats['top_entities']:
            top_5 = stats['top_entities'][:5]
            top_entities_list = ", ".join([f"{entity} ({count})" for entity, count in top_5])
        else:
            top_entities_list = "No entities extracted this week"
        
        # Get article counts by category
        categories = self.categorize_articles(articles)
        
        report = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    AI TREND MONITOR - TECHNICAL WEEKLY DIGEST
    Week of {week_start} - {report_date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Analysis of {stats['total_articles']} articles: {len(categories['models_software'])} model/software releases, {len(categories['research_technical'])} research papers, {len(categories['tools_platforms'])} tool updates.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{sections['executive_summary']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MODELS AND RESEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{sections['models_and_research']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOLS AND PLATFORMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{sections['tools_and_platforms']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY RESOURCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Most mentioned: {top_entities_list}

Top sources: {', '.join([source for source, _ in stats['source_distribution'].items()][:5])}

Sentiment: {sentiment_summary}

Selected technical articles:

{self._format_notable_articles_email(categories['models_software'][:5] if categories['models_software'] else articles[:5])}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Report generated {report_date}

— AI Trend Monitor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return report
    
    def _format_notable_articles_email(self, articles):
        """Format notable articles list for email"""
        output = ""
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Untitled')
            source = article.get('source', 'Unknown')
            link = article.get('link', '#')
            
            output += f"{i}. {title}\n"
            output += f"   Source: {source}\n"
            output += f"   Link: {link}\n\n"
        
        return output
    
    def save_report(self, report, format='markdown'):
        """Save report to Azure Blob Storage"""
        from src.storage import save_report_to_blob
        
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"weekly_report_{timestamp}.md"
        
        # Save to Azure Blob Storage
        blob_path = save_report_to_blob(report, filename)
        logging.info(f"Report saved to Azure: {blob_path}")
        
        return blob_path
    
    def send_report_email(self, report):
        """Send report via email using Azure Communication Services"""
        if not EMAIL_AVAILABLE:
            logging.warning("Email sending skipped: azure-communication-email not installed")
            logging.info("Install with: pip install azure-communication-email")
            return False
        
        connection_string = os.getenv('AZURE_COMMUNICATION_CONNECTION_STRING')
        sender_email = os.getenv('EMAIL_SENDER')
        
        if not connection_string:
            logging.error("AZURE_COMMUNICATION_CONNECTION_STRING not found in .env")
            return False
        
        if not sender_email:
            logging.error("EMAIL_SENDER not found in .env")
            return False
        
        # Get active subscribers from Table Storage
        try:
            from src.subscriber_manager import SubscriberManager
            manager = SubscriberManager()
            subscribers = manager.get_active_subscribers()
            
            logging.info(f"Retrieved {len(subscribers)} active subscribers from database")
            
            if not subscribers:
                logging.info("No subscribers in database. Using EMAIL_RECIPIENT from .env as fallback...")
                # Fallback to .env for testing/manual recipients
                recipient_email = os.getenv('EMAIL_RECIPIENT')
                if recipient_email:
                    subscribers = [{'email': email.strip(), 'unsubscribe_token': ''} 
                                 for email in recipient_email.split(',')]
                    logging.info(f"Using {len(subscribers)} recipient(s) from EMAIL_RECIPIENT environment variable")
                else:
                    logging.error("No subscribers in database and no EMAIL_RECIPIENT in .env")
                    return False
            
            logging.info(f"Sending newsletter to {len(subscribers)} recipient(s)")
            
        except Exception as e:
            logging.error(f"Error retrieving subscribers: {str(e)}")
            return False
        
        try:
            logging.info("Sending email report...")
            
            # Create email client
            email_client = EmailClient.from_connection_string(connection_string)
            
            # Email subject
            report_date = datetime.now().strftime('%B %d, %Y')
            subject = f"AI Trend Monitor - Weekly Digest ({report_date})"
            
            # Send individual emails with personalized unsubscribe links
            success_count = 0
            for subscriber in subscribers:
                try:
                    email_address = subscriber['email']
                    unsubscribe_token = subscriber.get('unsubscribe_token', '')
                    
                    # Convert report to HTML with personalized unsubscribe link
                    html_content = self._convert_report_to_html(
                        self.last_report_sections, 
                        self.last_stats,
                        email_address, 
                        unsubscribe_token
                    )
                    
                    # Build email message (HTML only, no plain text fallback)
                    message = {
                        "senderAddress": sender_email,
                        "content": {
                            "subject": subject,
                            "html": html_content
                        },
                        "recipients": {
                            "to": [{"address": email_address, "displayName": "Subscriber"}]
                        }
                    }
                    
                    # Send email
                    poller = email_client.begin_send(message)
                    result = poller.result()
                    
                    logging.info(f"Email sent to {email_address}. Status: {result['status']}")
                    success_count += 1
                    
                except Exception as e:
                    logging.error(f"Failed to send email to {subscriber['email']}: {str(e)}")
                    continue
            
            logging.info(f"Newsletter sent to {success_count}/{len(subscribers)} subscribers")
            print(f"\n✓ Newsletter sent to {success_count} subscriber(s)")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send email: {str(e)}")
            print(f"\n✗ Email sending failed: {str(e)}")
            return False
    
    def _markdown_to_html(self, text):
        """Convert markdown formatting to HTML"""
        if not text:
            return ""
        
        # Remove incomplete sentences at the end (text that ends without punctuation)
        lines = text.split('\n')
        if lines:
            last_line = lines[-1].strip()
            # Check if last line is incomplete (no ending punctuation and seems cut off)
            if last_line and not last_line[-1] in '.!?':
                lines = lines[:-1]
                text = '\n'.join(lines)
        
        # Convert **bold** to <strong>
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        
        # Convert ### headers to <h3>
        text = re.sub(r'^### (.+?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Convert ## headers to <h3> (subheadings)
        text = re.sub(r'^## (.+?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Split into paragraphs (double newline = new paragraph)
        paragraphs = text.split('\n\n')
        html_parts = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If it's already an HTML tag, keep it
            if para.startswith('<h3>'):
                html_parts.append(para)
            else:
                # Replace single newlines with spaces within paragraphs
                para = para.replace('\n', ' ')
                html_parts.append(f'<p>{para}</p>')
        
        return '\n'.join(html_parts)
    
    def _add_entity_links(self, html_content, top_entities, dashboard_url="https://trends.goblinsen.se"):
        """Add clickable links to entity mentions that search the dashboard"""
        import re
        from urllib.parse import quote
        
        # Handle both list formats: [(entity, count), ...] or [entity, ...]
        # If it's a list of strings (from GPT), use them directly
        if top_entities and isinstance(top_entities[0], str):
            entities_to_process = top_entities[:50]
        else:
            # If it's a list of tuples (from database), extract entity names
            entities_to_process = [entity for entity, count in top_entities[:50]]
        
        # Get top entities with better filtering
        # Filter out generic/numeric entities and common words
        filtered_entities = []
        generic_terms = {
            # Generic words (but allow specific product names like "Atlas", "Copilot")
            'one', 'two', 'three', 'new', 'first', 'second', 'third', 
            'technology', 'company', 'companies', 'product', 'products',
            'feature', 'features', 'update', 'updates', 'release', 'releases',
            'users', 'user', 'now', 'today', 'week', 'month', 'year',
            'tech resources', 'data', 'system', 'systems', 'service', 'services',
            # Countries/regions
            'us', 'uk', 'eu', 'china', 'japan',
        }
        
        for entity in entities_to_process:  # Check more entities
            entity_lower = entity.lower()
            
            # Skip if:
            # - Too short (unless it's an acronym like "AI")
            # - All digits or contains $ or % 
            # - Generic term
            # - Starts with a number
            if (len(entity) <= 2 and entity_lower != 'ai' or
                entity.replace(',', '').replace('.', '').isdigit() or
                '$' in entity or '%' in entity or
                entity_lower in generic_terms or
                entity[0].isdigit()):
                continue
            
            # Add to filtered list
            filtered_entities.append(entity)
            if len(filtered_entities) >= 30:  # Get up to 30 entities
                break
        
        # Sort by length (longest first) to avoid partial matches
        filtered_entities.sort(key=len, reverse=True)
        
        for entity in filtered_entities:
            # Create case-insensitive pattern that matches whole words
            # Avoid matching if already inside an HTML tag or existing link
            pattern = r'(?<![<"/])(\b' + re.escape(entity) + r'\b)(?![^<]*>|[^<]*</a>)'
            
            # Create search URL
            search_url = f"{dashboard_url}?search={quote(entity)}"
            replacement = rf'<a href="{search_url}" style="color: #0066cc; text-decoration: none; border-bottom: 1px dotted #0066cc;">\1</a>'
            
            # Replace only the first 3 occurrences of each entity to avoid over-linking
            html_content = re.sub(pattern, replacement, html_content, count=3, flags=re.IGNORECASE)
        
        return html_content
    
    def _convert_report_to_html(self, report_sections, stats, recipient_email='', unsubscribe_token=''):
        """Convert report sections dict to HTML for email with personalized unsubscribe link"""
        
        # Extract header info from stats
        report_date = datetime.now().strftime('%B %d, %Y')
        week_start = (datetime.now() - timedelta(days=7)).strftime('%B %d, %Y')
        week_info = f"Week of {week_start} - {report_date}"
        
        # Get article counts by category
        from src.generate_weekly_report import WeeklyReportGenerator
        temp_gen = WeeklyReportGenerator()
        articles = temp_gen.get_weekly_articles(days=7)
        categories = temp_gen.categorize_articles(articles)
        article_count = f"Analysis of {stats['total_articles']} articles: {len(categories['models_software'])} model/software releases, {len(categories['research_technical'])} research papers, {len(categories['tools_platforms'])} tool updates."
        
        # Build HTML
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
            max-width: 700px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        .header {{
            padding: 20px 0;
            text-align: center;
            border-bottom: 1px solid #cccccc;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 24px;
            font-weight: 600;
            color: #000000;
        }}
        .header p {{
            margin: 5px 0;
            font-size: 14px;
            color: #000000;
        }}
        .content {{
            padding: 30px 0;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #000000;
            margin: 0 0 15px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #cccccc;
        }}
        .section-content {{
            font-size: 15px;
            line-height: 1.8;
            color: #000000;
        }}
        .section-content p {{
            margin: 0 0 20px 0;
        }}
        .section-content h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #000000;
            margin: 25px 0 12px 0;
        }}
        .section-content strong {{
            font-weight: 600;
            color: #000000;
        }}
        .resources {{
            background-color: #f5f5f5;
            padding: 20px;
            margin-top: 30px;
        }}
        .resources h3 {{
            margin: 0 0 12px 0;
            font-size: 16px;
            color: #000000;
            font-weight: 600;
        }}
        .resources p {{
            margin: 8px 0;
            font-size: 14px;
            color: #000000;
        }}
        .article-list {{
            list-style: none;
            padding: 0;
            margin: 15px 0 0 0;
        }}
        .article-list li {{
            margin-bottom: 15px;
            padding: 15px;
            background-color: #f5f5f5;
            border-left: 2px solid #cccccc;
        }}
        .article-title {{
            font-weight: 600;
            color: #000000;
            margin-bottom: 5px;
        }}
        .article-source {{
            font-size: 13px;
            color: #666666;
            margin-bottom: 5px;
        }}
        .article-link {{
            font-size: 13px;
        }}
        .article-link a {{
            color: #0066cc;
            text-decoration: none;
        }}
        .article-link a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 20px 0;
            text-align: center;
            border-top: 1px solid #cccccc;
        }}
        .footer p {{
            margin: 5px 0;
            font-size: 14px;
            color: #000000;
        }}
        .metrics {{
            display: inline-block;
            margin: 0 15px;
            color: #000000;
        }}
        @media only screen and (max-width: 600px) {{
            .header {{
                padding: 20px 0;
            }}
            .header h1 {{
                font-size: 20px;
            }}
            .content {{
                padding: 20px 0;
            }}
            .section-title {{
                font-size: 18px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Trend Monitor</h1>
            <p style="font-size: 18px; margin-top: 10px;">Weekly Digest</p>
            <p>{week_info}</p>
            <p style="font-size: 14px;">{article_count}</p>
        </div>
        
        <div class="content">
"""
        
        # Get articles and categorize them for source links
        articles = self.get_weekly_articles(days=7)
        categories = self.categorize_articles(articles)
        
        # Add each section with proper formatting and entity links
        if 'executive_summary' in report_sections:
            content = report_sections['executive_summary'].strip()
            formatted_content = self._markdown_to_html(content)
            # Add clickable entity links to dashboard
            formatted_content = self._add_entity_links(formatted_content, stats.get('content_entities', stats['top_entities']))
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Executive Summary</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        if 'models_and_research' in report_sections:
            content = report_sections['models_and_research'].strip()
            formatted_content = self._markdown_to_html(content)
            # Add clickable entity links to dashboard
            formatted_content = self._add_entity_links(formatted_content, stats.get('content_entities', stats['top_entities']))
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Models and Research</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        if 'tools_and_platforms' in report_sections:
            content = report_sections['tools_and_platforms'].strip()
            formatted_content = self._markdown_to_html(content)
            # Add clickable entity links to dashboard
            formatted_content = self._add_entity_links(formatted_content, stats.get('content_entities', stats['top_entities']))
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Tools and Platforms</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        # Add metrics section
        top_sources_list = ', '.join([source for source, _ in stats.get('source_distribution', {}).items()][:5])
        
        # Format sentiment
        total = stats['total_articles']
        sentiment_text = f"{stats['sentiment_distribution'].get('positive', 0)} positive ({stats['sentiment_distribution'].get('positive', 0)/total*100:.0f}%), {stats['sentiment_distribution'].get('neutral', 0)} neutral ({stats['sentiment_distribution'].get('neutral', 0)/total*100:.0f}%), {stats['sentiment_distribution'].get('negative', 0)} negative ({stats['sentiment_distribution'].get('negative', 0)/total*100:.0f}%)"
        
        html_template += f"""
            <div class="resources">
                <h3>This Week's Metrics</h3>
                <p><strong>Top Sources:</strong> {top_sources_list}</p>
                <p><strong>Sentiment:</strong> {sentiment_text}</p>
            </div>
"""
        
        # Add call-to-action to explore dashboard
        dashboard_url = "https://trends.goblinsen.se"
        html_template += f"""
            <div class="section" style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-top: 30px;">
                <h3 style="margin-top: 0; color: #000000;">Explore More on the Dashboard</h3>
                <p style="margin-bottom: 15px;">Click on any highlighted topic above to search our full archive, or visit the interactive dashboard to:</p>
                <ul style="margin-bottom: 15px; line-height: 1.8;">
                    <li>Search and filter {stats['total_articles']} articles</li>
                    <li>Analyze sentiment trends over time</li>
                    <li>Chat with AI about recent developments</li>
                    <li>Explore topic evolution and entity relationships</li>
                </ul>
                <p style="text-align: center; margin-top: 20px;">
                    <a href="{dashboard_url}" style="display: inline-block; background-color: #0066cc; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: 600;">Visit Dashboard →</a>
                </p>
            </div>
"""
        
        # Footer
        report_date = datetime.now().strftime('%B %d, %Y')
        html_template += f"""
        </div>
        
        <div class="footer">
            <p style="font-weight: 600; color: #000000; margin-bottom: 10px;">AI Trend Monitor</p>
            <p>Report generated {report_date}</p>
            <p style="margin-top: 15px; font-size: 13px;">
                This is an automated weekly digest of AI development news.
            </p>
"""
        
        # Add unsubscribe link if subscriber info provided (GDPR requirement)
        if recipient_email and unsubscribe_token:
            base_url = os.getenv('STREAMLIT_APP_URL', 'http://localhost:8501')
            # Strip trailing slash to avoid double slashes in URL
            base_url_clean = base_url.rstrip('/')
            unsubscribe_url = f"{base_url_clean}/?unsubscribe={unsubscribe_token}&email={recipient_email}"
            html_template += f"""
            <p style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #cccccc; font-size: 12px;">
                <a href="{unsubscribe_url}" style="color: #666666;">Unsubscribe</a> | 
                <span style="color: #666666;">Your data is stored securely in Azure (Sweden) in compliance with GDPR</span>
            </p>"""
        
        html_template += """
        </div>
    </div>
</body>
</html>
"""
        
        return html_template


def main():
    """Main execution"""
    generator = WeeklyReportGenerator()
    report = generator.generate_full_report()
    
    if report:
        filename = generator.save_report(report)
        print(f"\nWeekly report generated successfully")
        print(f"Saved to: {filename}")
        
        # Optional: Send via email (requires setup - see docs/EMAIL_SETUP_GUIDE.md)
        # Uncomment the line below after configuring Azure Communication Services
        # generator.send_report_email(report)
    else:
        print("\nNo report generated (no articles found)")


if __name__ == '__main__':
    main()
