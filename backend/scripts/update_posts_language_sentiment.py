"""
Script to update existing posts with improved language detection and sentiment analysis.
Run this script to update all posts in the database with:
- Correct language detection (using Google Translate, DeepL, LLM, or fallback methods)
- Improved sentiment scores (especially for French)

IMPORTANT: Stop the FastAPI server before running this script to avoid database lock issues.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app import database as db
from app.analysis import sentiment, language_detection
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def update_posts():
    """Update all posts with improved language detection and sentiment analysis."""
    logger.info("🚀 Starting update of posts with improved language detection and sentiment analysis...")
    logger.info("⚠️  Make sure the FastAPI server is stopped to avoid database lock issues!")
    
    # Get all posts
    all_posts = db.get_posts(limit=100000, offset=0)
    total = len(all_posts)
    logger.info(f"📊 Found {total} posts to process")
    
    if total == 0:
        logger.info("ℹ️  No posts found in database. Nothing to update.")
        return
    
    updated_language = 0
    updated_sentiment = 0
    skipped_language = 0
    skipped_sentiment = 0
    errors = 0
    
    # Process posts in batches for better performance
    batch_size = 50
    updates_batch = []
    
    for idx, post in enumerate(all_posts):
        if (idx + 1) % 100 == 0:
            logger.info(f"⏳ Processing {idx + 1}/{total} posts... (updated: {updated_language} lang, {updated_sentiment} sentiment)")
        
        post_id = post.get('id')
        if not post_id:
            continue
        
        try:
            # Detect language
            detected_language = language_detection.detect_language_from_post(post)
            current_language = post.get('language', 'unknown')
            
            # Analyze sentiment with language awareness
            content = post.get('content', '') or ''
            an = sentiment.analyze(content, language=detected_language)
            new_score = an.get('score', 0.0)
            new_label = an.get('label', 'neutral')
            
            current_score = post.get('sentiment_score', 0.0)
            current_label = post.get('sentiment_label', 'neutral')
            
            # Prepare updates
            needs_language_update = detected_language != current_language and detected_language != 'unknown'
            score_diff = abs(new_score - current_score)
            needs_sentiment_update = score_diff > 0.1 or new_label != current_label
            
            # Batch updates for better performance
            if needs_language_update or needs_sentiment_update:
                update_data = {
                    'id': post_id,
                    'language': detected_language if needs_language_update else current_language,
                    'sentiment_score': new_score if needs_sentiment_update else current_score,
                    'sentiment_label': new_label if needs_sentiment_update else current_label,
                    'needs_language_update': needs_language_update,
                    'needs_sentiment_update': needs_sentiment_update,
                }
                updates_batch.append(update_data)
            
            # Execute batch updates
            if len(updates_batch) >= batch_size:
                try:
                    with db.get_db() as conn:
                        cursor = conn.cursor()
                        for update in updates_batch:
                            if update['needs_language_update']:
                                cursor.execute(
                                    'UPDATE posts SET language = ? WHERE id = ?',
                                    (update['language'], update['id'])
                                )
                                updated_language += 1
                            else:
                                skipped_language += 1
                            
                            if update['needs_sentiment_update']:
                                cursor.execute(
                                    'UPDATE posts SET sentiment_score = ?, sentiment_label = ? WHERE id = ?',
                                    (update['sentiment_score'], update['sentiment_label'], update['id'])
                                )
                                updated_sentiment += 1
                            else:
                                skipped_sentiment += 1
                        conn.commit()
                except Exception as e:
                    logger.error(f"Error updating batch: {e}")
                    errors += len(updates_batch)
                finally:
                    updates_batch = []
        
        except Exception as e:
            errors += 1
            logger.error(f"Error processing post {post_id}: {e}")
            continue
    
    # Process remaining batch
    if updates_batch:
        try:
            with db.get_db() as conn:
                cursor = conn.cursor()
                for update in updates_batch:
                    if update['needs_language_update']:
                        cursor.execute(
                            'UPDATE posts SET language = ? WHERE id = ?',
                            (update['language'], update['id'])
                        )
                        updated_language += 1
                    else:
                        skipped_language += 1
                    
                    if update['needs_sentiment_update']:
                        cursor.execute(
                            'UPDATE posts SET sentiment_score = ?, sentiment_label = ? WHERE id = ?',
                            (update['sentiment_score'], update['sentiment_label'], update['id'])
                        )
                        updated_sentiment += 1
                    else:
                        skipped_sentiment += 1
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating final batch: {e}")
            errors += len(updates_batch)
    
    logger.info(f"\n✅ Update completed!")
    logger.info(f"   📝 Language: {updated_language} updated, {skipped_language} unchanged")
    logger.info(f"   💭 Sentiment: {updated_sentiment} updated, {skipped_sentiment} unchanged")
    logger.info(f"   ❌ Errors: {errors}")
    logger.info(f"   📊 Total processed: {total} posts")


if __name__ == "__main__":
    try:
        update_posts()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Update interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

