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
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # Search with date filter
        results = self.search_client.search(
            search_text="*",
            filter=f"published_date ge '{cutoff_str}'",
            select=["title", "content", "link", "source", "published_date",
                   "sentiment_overall", "sentiment_positive_score", 
                   "sentiment_negative_score", "key_phrases", "entities"],
            top=1000,
            order_by=["published_date desc"]
        )
        
        articles = list(results)
        logging.info(f"Retrieved {len(articles)} articles")
        return articles
    
    def analyze_statistics(self, articles):
        """Generate statistical insights from articles"""
        logging.info("Analyzing weekly statistics...")
        
        # Entity frequency
        all_entities = []
        for article in articles:
            entities = article.get('entities', [])
            if isinstance(entities, list):
                all_entities.extend(entities)
        
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
                {"role": "system", "content": "You are a senior AI engineer writing a technical weekly digest for generative AI developers. Your audience works with LLMs, model training, inference optimization, and AI tools. Focus on technical developments, model releases, research breakthroughs, and tools. Be specific and professional. NEVER use emojis. Avoid repetition across sections. Complete all sentences."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
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
            f"Write a single editorial paragraph (150-200 words) summarizing the week's most significant AI developments from ALL {stats['total_articles']} articles. Focus on the overall narrative: what's happening in AI model development, what trends are emerging, what matters for practitioners. Do NOT use numbered lists or bullet points. Write in flowing prose. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=400
        )
        
        report_sections['models_and_research'] = self.generate_report_section(
            "Models and Research",
            f"Cover ALL model releases, LLM updates, and research breakthroughs from the 'Models & Software' and 'Research & Technical' categories. Include: specific model names/versions, technical capabilities, performance improvements, architectural innovations, training techniques. This is the ONLY section covering models - be comprehensive. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=900
        )
        
        report_sections['tools_and_platforms'] = self.generate_report_section(
            "Tools and Platforms",
            f"Focus exclusively on developer tools, APIs, SDKs, frameworks, and platform updates from the 'Tools & Platforms' category. Do NOT repeat any models already discussed. Cover: new APIs, integrations, workflow tools, deployment platforms. Today's date is {datetime.now().strftime('%B %d, %Y')}.",
            context,
            max_tokens=600
        )
        
        # Step 5: Compile full report
        report = self.compile_report(report_sections, stats, articles)
        
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
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"reports/weekly_report_{timestamp}.md"
        
        os.makedirs('reports', exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logging.info(f"Report saved to: {filename}")
        return filename
    
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
                    html_content = self._convert_report_to_html(report, email_address, unsubscribe_token)
                    
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
    
    def _convert_report_to_html(self, report, recipient_email='', unsubscribe_token=''):
        """Convert markdown report to HTML for email with personalized unsubscribe link"""
        # Parse the report sections
        lines = report.split('\n')
        
        # Extract header info
        week_info = ""
        article_count = ""
        for line in lines[:10]:
            if "Week of" in line:
                week_info = line.strip()
            elif "Analysis of" in line:
                article_count = line.strip()
        
        # Extract sections
        sections = {}
        current_section = None
        current_content = []
        
        for line in lines:
            if line.strip() and line.strip().startswith('━'):
                continue
            elif line.strip() in ['EXECUTIVE SUMMARY', 'MODELS AND RESEARCH', 'TOOLS AND PLATFORMS', 'KEY RESOURCES']:
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Add last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)
        
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
            line-height: 1.6;
            color: #000000;
        }}
        .section-content p {{
            margin: 0 0 15px 0;
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
        
        # Add each section with proper formatting
        if 'EXECUTIVE SUMMARY' in sections:
            content = sections['EXECUTIVE SUMMARY'].strip()
            # Convert paragraphs
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            formatted_content = ''.join([f'<p>{p}</p>' for p in paragraphs])
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Executive Summary</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        if 'MODELS AND RESEARCH' in sections:
            content = sections['MODELS AND RESEARCH'].strip()
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            formatted_content = ''.join([f'<p>{p}</p>' for p in paragraphs])
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Models and Research</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        if 'TOOLS AND PLATFORMS' in sections:
            content = sections['TOOLS AND PLATFORMS'].strip()
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            formatted_content = ''.join([f'<p>{p}</p>' for p in paragraphs])
            
            html_template += f"""
            <div class="section">
                <h2 class="section-title">Tools and Platforms</h2>
                <div class="section-content">
                    {formatted_content}
                </div>
            </div>
"""
        
        # Parse KEY RESOURCES section for structured display
        if 'KEY RESOURCES' in sections:
            resources_content = sections['KEY RESOURCES'].strip()
            lines = resources_content.split('\n')
            
            most_mentioned = ""
            top_sources = ""
            sentiment = ""
            articles = []
            
            current_article = {}
            for line in lines:
                line = line.strip()
                if line.startswith('Most mentioned:'):
                    most_mentioned = line.replace('Most mentioned:', '').strip()
                elif line.startswith('Top sources:'):
                    top_sources = line.replace('Top sources:', '').strip()
                elif line.startswith('Sentiment:'):
                    sentiment = line.replace('Sentiment:', '').strip()
                elif line.startswith('Selected technical articles:'):
                    continue
                elif line and line[0].isdigit() and '. ' in line:
                    if current_article:
                        articles.append(current_article)
                    current_article = {'title': line.split('. ', 1)[1] if '. ' in line else line}
                elif line.startswith('Source:'):
                    current_article['source'] = line.replace('Source:', '').strip()
                elif line.startswith('Link:'):
                    current_article['link'] = line.replace('Link:', '').strip()
            
            if current_article:
                articles.append(current_article)
            
            html_template += f"""
            <div class="resources">
                <h3>This Week's Metrics</h3>
                <p><strong>Most Mentioned:</strong> {most_mentioned}</p>
                <p><strong>Top Sources:</strong> {top_sources}</p>
                <p><strong>Sentiment:</strong> {sentiment}</p>
            </div>
"""
            
            if articles:
                html_template += """
            <div class="section">
                <h2 class="section-title">Selected Technical Articles</h2>
                <ul class="article-list">
"""
                for article in articles[:5]:
                    title = article.get('title', 'Untitled')
                    source = article.get('source', 'Unknown')
                    link = article.get('link', '#')
                    
                    html_template += f"""
                    <li>
                        <div class="article-title">{title}</div>
                        <div class="article-source">Source: {source}</div>
                        <div class="article-link"><a href="{link}">Read article →</a></div>
                    </li>
"""
                
                html_template += """
                </ul>
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
            </p>"""
        
        # Add unsubscribe link if subscriber info provided (GDPR requirement)
        if recipient_email and unsubscribe_token:
            base_url = os.getenv('STREAMLIT_APP_URL', 'http://localhost:8501')
            unsubscribe_url = f"{base_url}/?unsubscribe={unsubscribe_token}&email={recipient_email}"
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
