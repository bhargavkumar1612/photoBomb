-- PhotoBomb Database Schema
-- PostgreSQL 16+ with pgvector extension

-- Install required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For composite GIN indexes

-- ============================================================================
-- USERS & AUTH
-- ============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255), -- NULL for OAuth-only users
    full_name VARCHAR(255) NOT NULL,
    
    -- OAuth providers
    google_id VARCHAR(255) UNIQUE,
    apple_id VARCHAR(255) UNIQUE,
    
    -- Privacy settings
    face_recognition_enabled BOOLEAN DEFAULT FALSE,
    
    -- Storage quota (bytes)
    storage_quota_bytes BIGINT DEFAULT 107374182400, -- 100 GB default
    storage_used_bytes BIGINT DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete
    
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

CREATE TABLE refresh_tokens (
    token_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL, -- SHA256 of actual token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    
    -- Client info for security tracking
    user_agent TEXT,
    ip_address INET,
    
    CONSTRAINT check_not_expired CHECK (expires_at > created_at)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id, expires_at) 
    WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash) 
    WHERE revoked_at IS NULL AND expires_at > NOW();

-- ============================================================================
-- PHOTOS
-- ============================================================================

CREATE TABLE photos (
    photo_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- File metadata
    filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    
    -- Deduplication
    sha256 CHAR(64) NOT NULL, -- Exact duplicate detection
    phash BIGINT, -- Perceptual hash for near-duplicate detection (imagehash)
    
    -- EXIF data
    taken_at TIMESTAMPTZ, -- DateTimeOriginal from EXIF
    camera_make VARCHAR(100),
    camera_model VARCHAR(100),
    lens VARCHAR(100),
    iso INTEGER,
    aperture VARCHAR(20), -- e.g., "f/2.8"
    shutter_speed VARCHAR(20), -- e.g., "1/250"
    focal_length VARCHAR(20), -- e.g., "50mm"
    
    -- GPS
    gps_lat NUMERIC(10, 7),
    gps_lng NUMERIC(10, 7),
    gps_altitude NUMERIC(8, 2), -- meters
    location_name TEXT, -- Reverse-geocoded (e.g., "San Francisco, CA")
    
    -- User-editable fields
    caption TEXT,
    favorite BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ, -- When thumbnails completed
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ, -- Soft delete (30-day retention)
    
    CONSTRAINT valid_mime_type CHECK (
        mime_type IN ('image/jpeg', 'image/png', 'image/heic', 'image/webp', 'image/avif')
    )
);

CREATE INDEX idx_photos_user_taken ON photos(user_id, taken_at DESC NULLS LAST) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_photos_user_uploaded ON photos(user_id, uploaded_at DESC) 
    WHERE deleted_at IS NULL;
CREATE INDEX idx_photos_sha256 ON photos(sha256); -- Fast duplicate lookup
CREATE INDEX idx_photos_phash ON photos(phash) WHERE phash IS NOT NULL; -- Near-duplicate
CREATE INDEX idx_photos_gps ON photos USING GIST(ll_to_earth(gps_lat, gps_lng)) 
    WHERE gps_lat IS NOT NULL AND gps_lng IS NOT NULL;
CREATE INDEX idx_photos_favorite ON photos(user_id, uploaded_at DESC) 
    WHERE favorite = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_photos_caption_trgm ON photos USING GIN(caption gin_trgm_ops) 
    WHERE caption IS NOT NULL;

-- Full-text search on caption + location
CREATE INDEX idx_photos_search ON photos USING GIN(
    to_tsvector('english', COALESCE(caption, '') || ' ' || COALESCE(location_name, ''))
);

-- ============================================================================
-- PHOTO FILE VARIANTS (originals + thumbnails)
-- ============================================================================

CREATE TABLE photo_files (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    photo_id UUID NOT NULL REFERENCES photos(photo_id) ON DELETE CASCADE,
    
    variant VARCHAR(50) NOT NULL, -- 'original', 'thumb_256', 'thumb_512', 'thumb_1024'
    format VARCHAR(10) NOT NULL, -- 'jpeg', 'webp', 'avif'
    
    -- Storage
    storage_backend VARCHAR(20) DEFAULT 'b2', -- 'b2' or 'r2'
    b2_bucket VARCHAR(100),
    b2_key TEXT NOT NULL, -- Object key in bucket
    size_bytes BIGINT NOT NULL,
    
    -- Dimensions
    width INTEGER,
    height INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_photo_variant UNIQUE(photo_id, variant, format)
);

CREATE INDEX idx_photo_files_photo ON photo_files(photo_id);

-- ============================================================================
-- UPLOAD SESSIONS (presigned upload tracking)
-- ============================================================================

CREATE TABLE upload_sessions (
    upload_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Pre-upload info
    filename VARCHAR(500) NOT NULL,
    size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    sha256 CHAR(64),
    
    -- B2 presigned URL
    presigned_url TEXT NOT NULL,
    presigned_expires_at TIMESTAMPTZ NOT NULL,
    
    -- State
    status VARCHAR(20) DEFAULT 'pending', -- pending, uploaded, processing, completed, failed
    photo_id UUID REFERENCES photos(photo_id), -- Set after processing
    
    -- Error tracking
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    uploaded_at TIMESTAMPTZ, -- When browser confirms upload
    completed_at TIMESTAMPTZ, -- When processing done
    
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'uploaded', 'processing', 'completed', 'failed')
    )
);

CREATE INDEX idx_upload_sessions_user ON upload_sessions(user_id, created_at DESC);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status, created_at) 
    WHERE status IN ('uploaded', 'processing');

-- ============================================================================
-- FACE RECOGNITION (opt-in only)
-- ============================================================================

CREATE TABLE face_clusters (
    face_cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- User-assigned name (e.g., "Mom", "John")
    name VARCHAR(255),
    
    -- Representative face (highest quality detection)
    representative_face_id UUID,
    
    photo_count INTEGER DEFAULT 0, -- Denormalized for performance
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_face_clusters_user ON face_clusters(user_id);

CREATE TABLE face_detections (
    face_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    photo_id UUID NOT NULL REFERENCES photos(photo_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    face_cluster_id UUID REFERENCES face_clusters(face_cluster_id) ON DELETE SET NULL,
    
    -- Bounding box (normalized 0-1)
    bbox_x NUMERIC(5, 4) NOT NULL,
    bbox_y NUMERIC(5, 4) NOT NULL,
    bbox_width NUMERIC(5, 4) NOT NULL,
    bbox_height NUMERIC(5, 4) NOT NULL,
    
    -- Face embedding (512-dim FaceNet or InsightFace)
    embedding vector(512),
    
    -- Detection confidence
    confidence NUMERIC(4, 3), -- 0.0 - 1.0
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_bbox CHECK (
        bbox_x >= 0 AND bbox_x <= 1 AND
        bbox_y >= 0 AND bbox_y <= 1 AND
        bbox_width > 0 AND bbox_width <= 1 AND
        bbox_height > 0 AND bbox_height <= 1
    )
);

CREATE INDEX idx_face_detections_photo ON face_detections(photo_id);
CREATE INDEX idx_face_detections_cluster ON face_detections(face_cluster_id);

-- Vector similarity index (HNSW for fast approximate nearest neighbor)
CREATE INDEX idx_face_embeddings_hnsw ON face_detections 
    USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

-- ============================================================================
-- ALBUMS
-- ============================================================================

CREATE TABLE albums (
    album_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Auto-selected cover photo (most recent or user-selected)
    cover_photo_id UUID REFERENCES photos(photo_id) ON DELETE SET NULL,
    
    photo_count INTEGER DEFAULT 0, -- Denormalized
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_albums_user ON albums(user_id, updated_at DESC) 
    WHERE deleted_at IS NULL;

CREATE TABLE album_photos (
    album_id UUID NOT NULL REFERENCES albums(album_id) ON DELETE CASCADE,
    photo_id UUID NOT NULL REFERENCES photos(photo_id) ON DELETE CASCADE,
    
    -- Custom ordering within album
    position INTEGER DEFAULT 0,
    
    added_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (album_id, photo_id)
);

CREATE INDEX idx_album_photos_album ON album_photos(album_id, position);
CREATE INDEX idx_album_photos_photo ON album_photos(photo_id); -- Find albums for a photo

-- ============================================================================
-- SHARING
-- ============================================================================

CREATE TABLE shares (
    share_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    -- Short URL slug (base62, 8 chars)
    slug VARCHAR(20) NOT NULL UNIQUE,
    
    -- What's being shared
    album_id UUID REFERENCES albums(album_id) ON DELETE CASCADE,
    photo_ids UUID[], -- Array of photo IDs (if not sharing album)
    
    -- Access control
    password_hash VARCHAR(255), -- bcrypt, NULL if no password
    expires_at TIMESTAMPTZ NOT NULL,
    
    -- Options
    allow_download BOOLEAN DEFAULT FALSE,
    
    -- State
    status VARCHAR(20) DEFAULT 'active', -- active, expired, revoked
    view_count INTEGER DEFAULT 0,
    download_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_share_target CHECK (
        (album_id IS NOT NULL AND photo_ids IS NULL) OR
        (album_id IS NULL AND photo_ids IS NOT NULL)
    ),
    CONSTRAINT valid_status CHECK (status IN ('active', 'expired', 'revoked'))
);

CREATE INDEX idx_shares_user ON shares(user_id, created_at DESC);
CREATE INDEX idx_shares_slug ON shares(slug) WHERE status = 'active';
CREATE INDEX idx_shares_expires ON shares(expires_at) WHERE status = 'active';

-- Share access logs (for analytics and abuse detection)
CREATE TABLE share_access_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    share_id UUID NOT NULL REFERENCES shares(share_id) ON DELETE CASCADE,
    
    event VARCHAR(20) NOT NULL, -- 'viewed', 'downloaded', 'password_attempt'
    photo_id UUID, -- Specific photo if downloaded
    
    -- Visitor info
    ip_address INET,
    user_agent TEXT,
    referer TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_share_logs_share ON share_access_logs(share_id, created_at DESC);
CREATE INDEX idx_share_logs_ip ON share_access_logs(ip_address, created_at) 
    WHERE event = 'password_attempt'; -- Rate limiting

-- ============================================================================
-- PROCESSING JOBS (for async workers)
-- ============================================================================

CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_id UUID NOT NULL REFERENCES upload_sessions(upload_id) ON DELETE CASCADE,
    
    job_type VARCHAR(50) NOT NULL, -- 'thumbnail', 'face_detection', 'exif_extraction'
    priority INTEGER DEFAULT 5, -- 1=highest, 10=lowest
    
    status VARCHAR(20) DEFAULT 'queued', -- queued, processing, completed, failed
    
    -- Worker info
    worker_id VARCHAR(100), -- Which worker picked this up
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Idempotency
    idempotency_key VARCHAR(255) UNIQUE, -- Prevent duplicate jobs
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (
        status IN ('queued', 'processing', 'completed', 'failed')
    )
);

CREATE INDEX idx_jobs_queue ON processing_jobs(priority, created_at) 
    WHERE status = 'queued';
CREATE INDEX idx_jobs_upload ON processing_jobs(upload_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status, created_at);

-- ============================================================================
-- AUDIT LOG (compliance)
-- ============================================================================

CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    action VARCHAR(50) NOT NULL, -- 'photo_uploaded', 'photo_deleted', 'data_exported', 'account_deleted'
    resource_type VARCHAR(50), -- 'photo', 'album', 'user'
    resource_id UUID,
    
    -- For compliance (GDPR data deletion tracking)
    details JSONB,
    
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Q1: Timeline query (most common read)
-- SELECT * FROM photos 
-- WHERE user_id = $1 AND deleted_at IS NULL 
-- ORDER BY taken_at DESC NULLS LAST 
-- LIMIT 50;
-- Uses: idx_photos_user_taken

-- Q2: Duplicate detection on upload
-- SELECT photo_id FROM photos 
-- WHERE sha256 = $1 AND user_id = $2 AND deleted_at IS NULL;
-- Uses: idx_photos_sha256

-- Q3: Near-duplicate search (perceptual hash within Hamming distance 10)
-- This requires application-level filtering as Postgres doesn't have native perceptual hash index
-- SELECT photo_id, phash, BIT_COUNT(phash # $1::bigint) as distance 
-- FROM photos 
-- WHERE user_id = $2 AND phash IS NOT NULL 
-- HAVING BIT_COUNT(phash # $1::bigint) < 10;

-- Q4: Face similarity search (find photos with similar faces)
-- SELECT p.photo_id, p.thumb_urls, 
--        1 - (fd.embedding <=> $1::vector) as similarity
-- FROM face_detections fd
-- JOIN photos p ON fd.photo_id = p.photo_id
-- WHERE fd.user_id = $2 AND p.deleted_at IS NULL
-- ORDER BY fd.embedding <=> $1::vector
-- LIMIT 20;
-- Uses: idx_face_embeddings_hnsw (HNSW for fast ANN)

-- Q5: Location-based search (photos within 10km radius)
-- SELECT photo_id, gps_lat, gps_lng,
--        earth_distance(ll_to_earth(gps_lat, gps_lng), ll_to_earth($1, $2)) as distance_m
-- FROM photos
-- WHERE user_id = $3 
--   AND deleted_at IS NULL
--   AND earth_box(ll_to_earth($1, $2), 10000) @> ll_to_earth(gps_lat, gps_lng)
-- ORDER BY distance_m
-- LIMIT 50;
-- Uses: idx_photos_gps

-- Q6: Album photos (ordered)
-- SELECT p.* FROM photos p
-- JOIN album_photos ap ON p.photo_id = ap.photo_id
-- WHERE ap.album_id = $1 AND p.deleted_at IS NULL
-- ORDER BY ap.position;
-- Uses: idx_album_photos_album

-- ============================================================================
-- TRIGGERS (auto-update denormalized counts)
-- ============================================================================

-- Update photo count in albums
CREATE OR REPLACE FUNCTION update_album_photo_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE albums SET photo_count = photo_count + 1 WHERE album_id = NEW.album_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE albums SET photo_count = photo_count - 1 WHERE album_id = OLD.album_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_album_photos_count
AFTER INSERT OR DELETE ON album_photos
FOR EACH ROW EXECUTE FUNCTION update_album_photo_count();

-- Update storage used in users table
CREATE OR REPLACE FUNCTION update_user_storage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE users SET storage_used_bytes = storage_used_bytes + NEW.size_bytes 
        WHERE user_id = NEW.user_id;
    ELSIF TG_OP = 'DELETE' AND OLD.deleted_at IS NOT NULL THEN
        -- Only decrement when hard-deleted (after retention period)
        UPDATE users SET storage_used_bytes = storage_used_bytes - OLD.size_bytes 
        WHERE user_id = OLD.user_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_storage
AFTER INSERT OR DELETE ON photos
FOR EACH ROW EXECUTE FUNCTION update_user_storage();

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_photos_updated_at BEFORE UPDATE ON photos
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_albums_updated_at BEFORE UPDATE ON albums
FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- PARTITIONING (for large-scale deployments)
-- ============================================================================

-- If photos table grows > 100M rows, partition by user_id hash
-- CREATE TABLE photos_partitioned (LIKE photos INCLUDING ALL) PARTITION BY HASH(user_id);
-- CREATE TABLE photos_p0 PARTITION OF photos_partitioned FOR VALUES WITH (MODULUS 8, REMAINDER 0);
-- ... (7 more partitions)

-- ============================================================================
-- RETENTION & CLEANUP
-- ============================================================================

-- Cron job (pg_cron extension) or external scheduler:
-- 1. Hard-delete soft-deleted photos after 30 days:
--    UPDATE photos SET deleted_at = NULL WHERE deleted_at < NOW() - INTERVAL '30 days';
--    DELETE FROM photos WHERE deleted_at < NOW() - INTERVAL '30 days';
-- 2. Expire old shares:
--    UPDATE shares SET status = 'expired' WHERE expires_at < NOW() AND status = 'active';
-- 3. Cleanup failed upload sessions:
--    DELETE FROM upload_sessions WHERE status = 'failed' AND created_at < NOW() - INTERVAL '7 days';
