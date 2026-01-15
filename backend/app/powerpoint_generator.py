"""PowerPoint report generator for OVH feedback analytics."""
import io
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter, defaultdict
import os

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from PIL import Image
    PPTX_AVAILABLE = True
    MISSING_DEPENDENCIES = []
except ImportError as e:
    PPTX_AVAILABLE = False
    # Determine which dependency is missing
    missing = []
    try:
        import pptx
    except ImportError:
        missing.append("python-pptx")
    try:
        import matplotlib
    except ImportError:
        missing.append("matplotlib")
    try:
        from PIL import Image
    except ImportError:
        missing.append("Pillow")
    MISSING_DEPENDENCIES = missing if missing else ["python-pptx", "matplotlib", "Pillow"]

logger = logging.getLogger(__name__)


def generate_powerpoint_report(
    posts: List[Dict],
    filters: Dict,
    recommended_actions: List[Dict],
    stats: Dict,
    llm_analysis: Optional[str] = None,
    chart_images: Optional[Dict[str, bytes]] = None
) -> bytes:
    """
    Generate a PowerPoint report with charts and insights.
    
    Args:
        posts: List of post dictionaries
        filters: Current filter settings
        recommended_actions: List of recommended actions
        stats: Statistics dictionary
        llm_analysis: Optional LLM-generated analysis text
    
    Returns:
        bytes: PowerPoint file as bytes
    """
    if not PPTX_AVAILABLE:
        deps = ", ".join(MISSING_DEPENDENCIES)
        raise RuntimeError(
            f"PowerPoint generation requires {deps}. "
            f"Install with: pip install {' '.join(MISSING_DEPENDENCIES)} "
            f"or install all dependencies: pip install -r requirements.txt"
        )
    
    # Create presentation
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # Slide 1: Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    
    title.text = "OVH Customer Feedback Report"
    subtitle.text = f"Generated on {datetime.now().strftime('%B %d, %Y')}\nBased on {len(posts)} feedback posts"
    
    # Slide 2: Executive Summary
    bullet_slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(bullet_slide_layout)
    shapes = slide.shapes
    title_shape = shapes.title
    body_shape = shapes.placeholders[1]
    
    title_shape.text = "Executive Summary"
    tf = body_shape.text_frame
    tf.text = f"Total Posts Analyzed: {stats.get('total', len(posts))}"
    
    p = tf.add_paragraph()
    p.text = f"Positive: {stats.get('positive', 0)} | Negative: {stats.get('negative', 0)} | Neutral: {stats.get('neutral', 0)}"
    p.level = 0
    
    if filters.get('search'):
        p = tf.add_paragraph()
        p.text = f"Search Filter: \"{filters['search']}\""
        p.level = 0
    
    if filters.get('dateFrom') or filters.get('dateTo'):
        date_range = f"{filters.get('dateFrom', 'Start')} to {filters.get('dateTo', 'End')}"
        p = tf.add_paragraph()
        p.text = f"Date Range: {date_range}"
        p.level = 0
    
    # Slide 3: Combined slide with charts, key takeaways, and LLM analysis
    # Use blank layout for custom layout
    blank_slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Add title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(9), Inches(0.6))
    title_frame = title_box.text_frame
    title_frame.text = "Dashboard Overview & Insights"
    title_paragraph = title_frame.paragraphs[0]
    title_paragraph.font.size = Pt(24)
    title_paragraph.font.bold = True
    title_paragraph.font.color.rgb = RGBColor(0, 0, 0)
    
    # Add charts in a 2x2 grid (or 3 charts if available)
    chart_images_dict = chart_images or {}
    chart_positions = [
        ('timeline', Inches(0.5), Inches(1), Inches(4.5), Inches(2.5)),
        ('source', Inches(5.5), Inches(1), Inches(4.5), Inches(2.5)),
        ('sentiment', Inches(0.5), Inches(3.8), Inches(4.5), Inches(2.5))
    ]
    
    charts_added = 0
    for chart_type, left, top, width, height in chart_positions:
        if chart_type in chart_images_dict and chart_images_dict[chart_type]:
            try:
                slide.shapes.add_picture(io.BytesIO(chart_images_dict[chart_type]), left, top, width, height)
                charts_added += 1
            except Exception as e:
                logger.warning(f"Failed to add {chart_type} chart: {e}")
    
    # Key Takeaways box (right side, below source chart)
    takeaways_left = Inches(5.5)
    takeaways_top = Inches(3.8)
    takeaways_width = Inches(4.5)
    takeaways_height = Inches(2.5)
    
    # Add background shape for key takeaways
    from pptx.enum.shapes import MSO_SHAPE
    takeaways_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, takeaways_left, takeaways_top, takeaways_width, takeaways_height)
    takeaways_shape.fill.solid()
    takeaways_shape.fill.fore_color.rgb = RGBColor(240, 248, 255)  # Light blue background
    takeaways_shape.line.color.rgb = RGBColor(0, 212, 255)  # Cyan border
    takeaways_shape.line.width = Pt(2)
    
    # Add text to key takeaways box
    takeaways_textbox = slide.shapes.add_textbox(takeaways_left + Inches(0.2), takeaways_top + Inches(0.2), takeaways_width - Inches(0.4), takeaways_height - Inches(0.4))
    takeaways_frame = takeaways_textbox.text_frame
    takeaways_frame.word_wrap = True
    takeaways_frame.text = "Key Takeaways"
    
    # Format title
    takeaways_title = takeaways_frame.paragraphs[0]
    takeaways_title.font.size = Pt(16)
    takeaways_title.font.bold = True
    takeaways_title.font.color.rgb = RGBColor(0, 0, 0)
    takeaways_title.space_after = Pt(8)
    
    # Add recommended actions as bullets
    if recommended_actions:
        for action in recommended_actions[:3]:  # Top 3 actions
            p = takeaways_frame.add_paragraph()
            p.text = f"• {action.get('text', 'N/A')}"
            p.level = 0
            p.font.size = Pt(11)
            p.space_after = Pt(4)
            
            # Color by priority
            priority = action.get('priority', 'medium').lower()
            if priority == 'high':
                p.font.color.rgb = RGBColor(239, 68, 68)  # Red
            elif priority == 'medium':
                p.font.color.rgb = RGBColor(245, 158, 11)  # Orange
            else:
                p.font.color.rgb = RGBColor(34, 197, 94)  # Green
    
    # LLM Analysis box (below sentiment chart, full width)
    if llm_analysis:
        analysis_left = Inches(0.5)
        analysis_top = Inches(6.5)
        analysis_width = Inches(9)
        analysis_height = Inches(1)
        
        # Add background shape for LLM analysis
        analysis_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, analysis_left, analysis_top, analysis_width, analysis_height)
        analysis_shape.fill.solid()
        analysis_shape.fill.fore_color.rgb = RGBColor(255, 250, 240)  # Light beige background
        analysis_shape.line.color.rgb = RGBColor(245, 158, 11)  # Orange border
        analysis_shape.line.width = Pt(2)
        
        # Add LLM analysis text
        analysis_textbox = slide.shapes.add_textbox(analysis_left + Inches(0.2), analysis_top + Inches(0.15), analysis_width - Inches(0.4), analysis_height - Inches(0.3))
        analysis_frame = analysis_textbox.text_frame
        analysis_frame.word_wrap = True
        
        # Parse LLM analysis into bullet points
        analysis_lines = llm_analysis.split('\n')
        bullet_points = []
        for line in analysis_lines:
            line = line.strip()
            if line:
                # Remove existing bullets if any
                line = line.lstrip('•-*').strip()
                bullet_points.append(line)
        
        # Take first 2-3 bullet points
        for i, point in enumerate(bullet_points[:3]):
            if i == 0:
                analysis_frame.text = f"• {point}"
            else:
                p = analysis_frame.add_paragraph()
                p.text = f"• {point}"
                p.level = 0
            
            if i < len(bullet_points[:3]) - 1:
                analysis_frame.paragraphs[i].space_after = Pt(4)
        
        # Format analysis text
        for paragraph in analysis_frame.paragraphs:
            paragraph.font.size = Pt(11)
            paragraph.font.color.rgb = RGBColor(0, 0, 0)
    
    # Save to bytes
    pptx_bytes = io.BytesIO()
    prs.save(pptx_bytes)
    pptx_bytes.seek(0)
    
    return pptx_bytes.getvalue()


def create_chart_image(chart_type: str, data: Dict, width: int = 800, height: int = 600) -> bytes:
    """
    Create a chart image from data.
    
    Args:
        chart_type: Type of chart ('timeline', 'product', 'source', 'sentiment')
        data: Chart data dictionary
        width: Image width in pixels
        height: Image height in pixels
    
    Returns:
        bytes: PNG image as bytes
    """
    if not PPTX_AVAILABLE:
        raise RuntimeError("matplotlib not available")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
    
    if chart_type == 'timeline':
        # Timeline chart
        dates = data.get('dates', [])
        counts = data.get('counts', [])
        ax.bar(dates, counts, color='#0099ff', alpha=0.7)
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Number of Posts', fontsize=10)
        ax.set_title('Posts Timeline', fontsize=12, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        
    elif chart_type == 'product':
        # Product distribution
        products = data.get('products', [])
        counts = data.get('counts', [])
        colors = plt.cm.Set3(range(len(products)))
        ax.pie(counts, labels=products, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.set_title('Distribution by Product', fontsize=12, fontweight='bold')
        
    elif chart_type == 'source':
        # Source distribution
        sources = data.get('sources', [])
        counts = data.get('counts', [])
        ax.barh(sources, counts, color='#34d399')
        ax.set_xlabel('Number of Posts', fontsize=10)
        ax.set_title('Posts by Source', fontsize=12, fontweight='bold')
        
    elif chart_type == 'sentiment':
        # Sentiment distribution
        sentiments = data.get('sentiments', [])
        counts = data.get('counts', [])
        colors = ['#ef4444', '#f59e0b', '#10b981']  # Red, Orange, Green
        ax.pie(counts, labels=sentiments, autopct='%1.1f%%', colors=colors[:len(sentiments)], startangle=90)
        ax.set_title('Sentiment Distribution', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    
    # Save to bytes
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_bytes.seek(0)
    
    return img_bytes.getvalue()


def prepare_chart_data(posts: List[Dict]) -> Dict:
    """
    Prepare chart data from posts for PowerPoint generation.
    
    Args:
        posts: List of post dictionaries
    
    Returns:
        Dict with chart data for timeline, product, source, and sentiment
    """
    chart_data = {}
    
    if not posts:
        return chart_data
    
    # Sentiment Distribution
    sentiment_counts = Counter()
    for post in posts:
        sentiment = post.get('sentiment_label', 'neutral') or 'neutral'
        sentiment_counts[sentiment] += 1
    
    if sentiment_counts:
        chart_data['sentiment'] = {
            'sentiments': list(sentiment_counts.keys()),
            'counts': [sentiment_counts[s] for s in sentiment_counts.keys()]
        }
    
    # Timeline Chart - Group by date
    timeline_groups = defaultdict(int)
    for post in posts:
        created_at = post.get('created_at', '')
        if created_at:
            try:
                # Parse date
                if 'T' in created_at:
                    date_str = created_at.split('T')[0]
                else:
                    date_str = created_at.split()[0]
                timeline_groups[date_str] += 1
            except:
                continue
    
    if timeline_groups:
        sorted_dates = sorted(timeline_groups.keys())
        chart_data['timeline'] = {
            'dates': sorted_dates,
            'counts': [timeline_groups[d] for d in sorted_dates]
        }
    
    # Source Distribution
    source_counts = Counter()
    for post in posts:
        source = post.get('source', 'Unknown') or 'Unknown'
        source_counts[source] += 1
    
    if source_counts:
        # Sort by count descending, take top 10
        top_sources = source_counts.most_common(10)
        chart_data['source'] = {
            'sources': [s[0] for s in top_sources],
            'counts': [s[1] for s in top_sources]
        }
    
    # Product Distribution - Simple keyword-based detection
    product_patterns = [
        ('VPS', r'\b(vps|virtual\s*private\s*server)\b'),
        ('Dedicated', r'\b(dedicated|dédié|bare\s*metal)\b'),
        ('Public Cloud', r'\b(public\s*cloud|openstack|instance)\b'),
        ('Private Cloud', r'\b(private\s*cloud|vmware)\b'),
        ('Hosting', r'\b(web\s*host|hosting|hébergement)\b'),
        ('Domain', r'\b(domain|domaine|dns)\b'),
        ('Email', r'\b(email|exchange|mail|mx)\b'),
        ('Storage', r'\b(object\s*storage|swift|s3)\b'),
        ('CDN', r'\b(cdn|content\s*delivery)\b'),
        ('Backup', r'\b(backup|veeam|archive)\b'),
    ]
    
    product_counts = Counter()
    for post in posts:
        content = (post.get('content', '') or '').lower()
        detected = False
        for product_name, pattern in product_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                product_counts[product_name] += 1
                detected = True
                break  # Only count first match
        if not detected:
            product_counts['Other'] += 1
    
    if product_counts:
        # Take top 8 products
        top_products = product_counts.most_common(8)
        chart_data['product'] = {
            'products': [p[0] for p in top_products],
            'counts': [p[1] for p in top_products]
        }
    
    return chart_data

