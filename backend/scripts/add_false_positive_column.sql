-- Migration: Add is_false_positive column to posts table
-- This allows marking posts as false positives without deleting them

-- Add column if it doesn't exist
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS is_false_positive BOOLEAN DEFAULT FALSE;

-- Create index for filtering
CREATE INDEX IF NOT EXISTS idx_posts_is_false_positive ON posts(is_false_positive);

-- Update existing posts to ensure default value
UPDATE posts SET is_false_positive = FALSE WHERE is_false_positive IS NULL;
