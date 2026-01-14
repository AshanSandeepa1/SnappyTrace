-- Optional: prune legacy columns from watermarked_files
-- IMPORTANT: This is irreversible. Only run once you've confirmed nothing depends on these columns.
-- Recommended workflow:
-- 1) Run watermarked_files_healthcheck.sql
-- 2) Take a DB backup/snapshot
-- 3) Run these DROP COLUMN statements

-- These are legacy columns from earlier iterations and are not required by the current app logic.
-- Uncomment one-by-one if you want a clean schema.

-- ALTER TABLE watermarked_files DROP COLUMN IF EXISTS file_hash;
-- ALTER TABLE watermarked_files DROP COLUMN IF EXISTS created_at;
-- ALTER TABLE watermarked_files DROP COLUMN IF EXISTS watermarked_path;
-- ALTER TABLE watermarked_files DROP COLUMN IF EXISTS uploaded_at;

-- If you drop uploaded_at, make sure you are using issued_at everywhere in the app.
