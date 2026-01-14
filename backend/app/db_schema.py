import json
from typing import Optional


async def ensure_schema() -> None:
    """Create required tables/extensions if they don't exist.

    This keeps local + Azure deployments simple (no separate migration tooling).
    """
    from app.database import db

    # UUID generator
    await db.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # Users table (used by auth routes)
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    # Watermarked records (store metadata/hashes only; not the file)
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS watermarked_files (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            original_filename TEXT NOT NULL,
            stored_filename TEXT,
            mime_type TEXT,
            original_file_hash TEXT NOT NULL,
            watermark_id TEXT UNIQUE NOT NULL,
            watermark_code TEXT UNIQUE NOT NULL,
            perceptual_hash TEXT,
            pdf_text_simhash TEXT,
            metadata JSONB NOT NULL,
            metadata_hash TEXT NOT NULL,
            source_created_at DATE,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            signed_at TIMESTAMPTZ,
            signer_cert_thumbprint TEXT,
            signer_name TEXT,
            per_page_hashes JSONB,
            algo_version INT NOT NULL DEFAULT 1
        );
        """
    )

    # If the table already existed (older schema), add missing columns safely.
    # These statements are no-ops if the column already exists.
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS stored_filename TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS mime_type TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS original_file_hash TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS watermark_id TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS watermark_code TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS metadata_hash TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS perceptual_hash TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS pdf_text_simhash TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS source_created_at DATE;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS issued_at TIMESTAMPTZ;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS signed_at TIMESTAMPTZ;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS signer_cert_thumbprint TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS signer_name TEXT;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS per_page_hashes JSONB;')
    await db.execute('ALTER TABLE watermarked_files ADD COLUMN IF NOT EXISTS algo_version INT;')

    # Backfill from legacy columns if present.
    # Older schema used file_hash; copy to original_file_hash if needed.
    await db.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='watermarked_files' AND column_name='file_hash'
            ) THEN
                EXECUTE 'UPDATE watermarked_files SET original_file_hash = file_hash WHERE original_file_hash IS NULL';
            END IF;
        END $$;
        """
    )

    # Backfill issued_at for older rows (NULLs sort first on DESC in Postgres).
    # Prefer source_created_at (date) when present; otherwise use now().
    await db.execute(
        """
        UPDATE watermarked_files
        SET issued_at = COALESCE(source_created_at::timestamptz, now())
        WHERE issued_at IS NULL;
        """
    )

    # Ensure future inserts get an issued_at even in legacy schemas where the column
    # was added without a default.
    await db.execute(
        """
        DO $$
        BEGIN
            BEGIN
                EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN issued_at SET DEFAULT now()';
            EXCEPTION WHEN others THEN
                -- ignore
            END;

            BEGIN
                EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN issued_at SET NOT NULL';
            EXCEPTION WHEN others THEN
                -- ignore
            END;
        END $$;
        """
    )

    # If legacy schema has NOT NULL constraints, relax them so new inserts work.
    # (We store original_file_hash now; legacy file_hash is kept for compatibility.)
    await db.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='watermarked_files' AND column_name='file_hash'
            ) THEN
                EXECUTE 'UPDATE watermarked_files SET file_hash = COALESCE(file_hash, original_file_hash)';
                BEGIN
                    EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN file_hash DROP NOT NULL';
                EXCEPTION WHEN others THEN
                    -- ignore if already nullable
                END;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='watermarked_files' AND column_name='created_at'
            ) THEN
                EXECUTE 'UPDATE watermarked_files SET created_at = COALESCE(created_at, now())';
                BEGIN
                    EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN created_at DROP NOT NULL';
                EXCEPTION WHEN others THEN
                END;
            END IF;

            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='watermarked_files' AND column_name='watermarked_path'
            ) THEN
                BEGIN
                    EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN watermarked_path DROP NOT NULL';
                EXCEPTION WHEN others THEN
                END;
            END IF;
        END $$;
        """
    )

    # Ensure defaults for new columns (safe even if already set)
    await db.execute('UPDATE watermarked_files SET issued_at = COALESCE(issued_at, now());')
    await db.execute('UPDATE watermarked_files SET algo_version = COALESCE(algo_version, 1);')

    # Backfill and enforce watermark_code if the legacy table allowed NULL.
    # Legacy data may have stored the WMK-* code in watermark_id.
    await db.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='watermarked_files' AND column_name='watermark_code'
            ) THEN
                -- Case 1: watermark_id already contains a WMK-* code.
                EXECUTE $wmk_sql_1$
                    UPDATE watermarked_files
                    SET watermark_code = UPPER(watermark_id)
                    WHERE watermark_code IS NULL AND watermark_id LIKE 'WMK-%'
                $wmk_sql_1$;

                -- Case 2: watermark_id is a hex id; derive WMK-* code.
                EXECUTE $wmk_sql_2$
                    UPDATE watermarked_files
                    SET watermark_code = 'WMK-' || UPPER(SUBSTRING(watermark_id FROM 1 FOR 12))
                    WHERE watermark_code IS NULL AND watermark_id IS NOT NULL
                $wmk_sql_2$;

                BEGIN
                    EXECUTE 'ALTER TABLE watermarked_files ALTER COLUMN watermark_code SET NOT NULL';
                EXCEPTION WHEN others THEN
                    -- ignore if already not null or not applicable
                END;
            END IF;
        END $$;
        """
    )

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_watermarked_files_user_id ON watermarked_files(user_id);"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_watermarked_files_watermark_code ON watermarked_files(watermark_code);"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_watermarked_files_perceptual_hash ON watermarked_files(perceptual_hash);"
    )

    # Unique indexes are safer than constraints for incremental upgrades.
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_watermarked_files_watermark_id ON watermarked_files(watermark_id);"
    )
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_watermarked_files_watermark_code ON watermarked_files(watermark_code);"
    )


def canonical_metadata_hash(metadata: dict) -> str:
    import hashlib

    # Stable JSON: sorted keys, no whitespace
    payload = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
