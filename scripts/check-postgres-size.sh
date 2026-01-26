#!/bin/bash
# Script pour vérifier la taille de la base de données PostgreSQL

echo "=== Taille de la base de données PostgreSQL ==="

# Se connecter au conteneur PostgreSQL et vérifier la taille
docker compose exec -T postgres psql -U postgres -d customer_feedbacks -c "
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'customer_feedbacks';
" 2>/dev/null || echo "Impossible de se connecter à PostgreSQL (conteneur arrêté)"

echo ""
echo "=== Taille des tables ==="
docker compose exec -T postgres psql -U postgres -d customer_feedbacks -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;
" 2>/dev/null || echo "Impossible de se connecter à PostgreSQL (conteneur arrêté)"

echo ""
echo "=== Nombre de lignes par table ==="
docker compose exec -T postgres psql -U postgres -d customer_feedbacks -c "
SELECT 
    'posts' as table_name, COUNT(*) as row_count FROM posts
UNION ALL
SELECT 
    'scraping_logs', COUNT(*) FROM scraping_logs
UNION ALL
SELECT 
    'jobs', COUNT(*) FROM jobs
UNION ALL
SELECT 
    'saved_queries', COUNT(*) FROM saved_queries;
" 2>/dev/null || echo "Impossible de se connecter à PostgreSQL (conteneur arrêté)"
