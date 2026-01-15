"""PowerPoint report generator for OVH feedback analytics."""
import io
import logging
from typing import List, Dict, Optional
from datetime import datetime
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
except ImportError:
    PPTX_AVAILABLE = False

logger = logging.getLogger(__name__)


def generate_powerpoint_report(
    posts: List[Dict],
    filters: Dict,
    recommended_actions: List[Dict],
    stats: Dict,
    llm_analysis: Optional[str] = None
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
        raise RuntimeError("python-pptx, matplotlib, or Pillow not installed. Install with: pip install python-pptx matplotlib Pillow")
    
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
    
    # Slide 3-6: Charts (will be added by caller with chart images)
    # For now, we'll create placeholder slides
    
    # Slide 7: Key Takeaways
    if recommended_actions:
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        
        title_shape.text = "Key Takeaways & Recommended Actions"
        tf = body_shape.text_frame
        tf.text = ""
        
        for i, action in enumerate(recommended_actions[:5], 1):  # Top 5 actions
            p = tf.add_paragraph()
            p.text = f"{action.get('icon', '•')} {action.get('text', 'N/A')}"
            p.level = 0
            p.font.size = Pt(14)
            
            # Color code by priority
            priority = action.get('priority', 'medium').lower()
            if priority == 'high':
                p.font.color.rgb = RGBColor(239, 68, 68)  # Red
            elif priority == 'medium':
                p.font.color.rgb = RGBColor(245, 158, 11)  # Orange
            else:
                p.font.color.rgb = RGBColor(34, 197, 94)  # Green
    
    # Slide 8: AI Analysis (if available)
    if llm_analysis:
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        
        title_shape.text = "AI-Generated Analysis"
        tf = body_shape.text_frame
        tf.text = llm_analysis
        tf.word_wrap = True
        
        # Format text
        for paragraph in tf.paragraphs:
            paragraph.font.size = Pt(12)
            paragraph.space_after = Pt(6)
    
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

