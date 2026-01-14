-- Watermarked files: health check / consistency report
-- Run in pgAdmin or psql.

-- 1) Row count
SELECT COUNT(*) AS total_rows FROM watermarked_files;

-- 2) Null checks for core fields
SELECT
  COUNT(*) FILTER (WHERE user_id IS NULL)            AS null_user_id,
  COUNT(*) FILTER (WHERE watermark_id IS NULL)       AS null_watermark_id,
  COUNT(*) FILTER (WHERE watermark_code IS NULL)     AS null_watermark_code,
  COUNT(*) FILTER (WHERE metadata IS NULL)           AS null_metadata,
  COUNT(*) FILTER (WHERE metadata_hash IS NULL)      AS null_metadata_hash,
  COUNT(*) FILTER (WHERE issued_at IS NULL)          AS null_issued_at,
  COUNT(*) FILTER (WHERE original_file_hash IS NULL) AS null_original_file_hash
FROM watermarked_files;

-- 3) Metadata key checks (expects JSONB object)
SELECT
  COUNT(*) FILTER (WHERE metadata ? 'title')        AS has_title,
  COUNT(*) FILTER (WHERE metadata ? 'author')       AS has_author,
  COUNT(*) FILTER (WHERE metadata ? 'createdDate')  AS has_createdDate,
  COUNT(*) FILTER (WHERE metadata ? 'organization') AS has_organization
FROM watermarked_files;

-- 4) Show newest 20 (for quick sanity)
SELECT
  watermark_code,
  issued_at,
  source_created_at,
  (metadata->>'title')        AS title,
  (metadata->>'author')       AS author,
  (metadata->>'createdDate')  AS createdDate,
  (metadata->>'organization') AS organization
FROM watermarked_files
ORDER BY issued_at DESC NULLS LAST
LIMIT 20;
