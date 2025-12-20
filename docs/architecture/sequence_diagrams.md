# Sequence Diagrams

## 1. Direct Browser Upload with Presigned URL

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant ServiceWorker as Service Worker
    participant FastAPI
    participant Postgres as PostgreSQL
    participant B2 as Backblaze B2
    participant Queue as Redis Queue
    participant Worker as Image Worker
    participant CDN as Cloudflare CDN

    User->>Browser: Select photo(s)
    Browser->>Browser: Compute SHA256 (client-side, FileReader API)
    
    Browser->>FastAPI: POST /api/v1/upload/presign<br/>{filename, size, sha256, mime_type}
    
    FastAPI->>Postgres: SELECT FROM photos WHERE sha256=$1
    
    alt Duplicate found
        Postgres-->>FastAPI: Existing photo record
        FastAPI-->>Browser: 409 Conflict<br/>{photo_id, message: "Duplicate"}
        Browser->>User: Show "Already uploaded"
    else New upload
        Postgres-->>FastAPI: No match
        FastAPI->>FastAPI: Generate upload_id (UUID)
        FastAPI->>B2: CreateUploadURL(bucket, key=upload_id)
        B2-->>FastAPI: Presigned URL (15min TTL)
        FastAPI->>Postgres: INSERT upload_session (upload_id, status='pending')
        FastAPI-->>Browser: 200 OK<br/>{upload_id, presigned_url, multipart_config}
        
        Browser->>Browser: Split file into 5MB chunks
        
        loop Each chunk
            Browser->>B2: PUT chunk (with range header)
            B2-->>Browser: 200 OK (chunk ETag)
            Browser->>ServiceWorker: Update progress (IndexedDB)
            ServiceWorker-->>Browser: Progress event
            Browser->>User: Show upload % (progress bar)
        end
        
        Browser->>B2: POST CompleteMultipartUpload
        B2-->>Browser: 200 OK
        
        Browser->>FastAPI: POST /api/v1/upload/confirm<br/>{upload_id, etags[]}
        FastAPI->>Postgres: UPDATE upload_session SET status='uploaded'
        FastAPI->>Queue: RPUSH processing_queue<br/>{upload_id, priority=high}
        FastAPI-->>Browser: 202 Accepted<br/>{photo_id (placeholder)}
        
        Browser->>User: Show "Processing..."
        
        Note over Queue,Worker: Async processing starts
        
        Queue->>Worker: LPOP processing_queue
        Worker->>B2: GET object (via presigned URL)
        B2-->>Worker: Original image bytes
        
        Worker->>Worker: libvips: Generate thumbnails<br/>256px, 512px, 1024px (WebP + AVIF)
        Worker->>Worker: Compute pHash (perceptual hash)
        Worker->>Worker: Extract EXIF (exiftool)<br/>(date, GPS, camera model)
        
        Worker->>B2: PUT thumbnails (thumb_256/, thumb_512/, ...)
        B2-->>Worker: 200 OK
        
        Worker->>Postgres: BEGIN TRANSACTION
        Worker->>Postgres: INSERT INTO photos<br/>(upload_id, sha256, phash, exif, sizes)
        Worker->>Postgres: INSERT INTO photo_files<br/>(photo_id, variant, b2_key, size_bytes)
        Worker->>Postgres: COMMIT
        
        Worker->>CDN: POST /_purge<br/>{keys: [thumb URLs]}
        CDN-->>Worker: 200 OK
        
        Worker->>FastAPI: POST /internal/webhooks/processing_complete<br/>{upload_id, photo_id}
        FastAPI->>FastAPI: Emit SSE event (Server-Sent Events)
        FastAPI-->>Browser: SSE: {event: 'photo_ready', photo_id}
        
        Browser->>FastAPI: GET /api/v1/photos/{photo_id}
        FastAPI->>Postgres: SELECT with thumbnail URLs
        Postgres-->>FastAPI: Photo metadata + signed CDN URLs
        FastAPI-->>Browser: 200 OK {photo_id, thumb_urls, exif}
        
        Browser->>User: Update UI: "Processed ✓"
    end
```

## 2. Client Sync with Offline Queue & Resume

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant ServiceWorker as Service Worker
    participant IndexedDB
    participant BackgroundSync as Background Sync API
    participant FastAPI
    participant B2

    Note over User,B2: Scenario: User goes offline mid-upload

    User->>Browser: Select 5 photos
    Browser->>Browser: Network status: OFFLINE
    
    loop For each photo
        Browser->>ServiceWorker: postMessage('queue_upload', {file, metadata})
        ServiceWorker->>IndexedDB: PUT pending_uploads<br/>{id, file_blob, status='queued', retry_count=0}
        ServiceWorker-->>Browser: {queued: true, local_id}
        Browser->>User: Show "Queued (offline)"
    end
    
    ServiceWorker->>BackgroundSync: register('upload-sync')
    BackgroundSync-->>ServiceWorker: Registered
    
    Note over Browser,B2: Network restored
    
    BackgroundSync->>ServiceWorker: 'sync' event triggered
    
    ServiceWorker->>IndexedDB: GET pending_uploads WHERE status='queued'
    IndexedDB-->>ServiceWorker: [upload1, upload2, ...]
    
    loop For each pending upload
        ServiceWorker->>ServiceWorker: Compute SHA256
        ServiceWorker->>FastAPI: POST /api/v1/upload/presign
        
        alt API success
            FastAPI-->>ServiceWorker: {upload_id, presigned_url}
            
            ServiceWorker->>B2: PUT with resumable upload (Range header)
            
            alt Upload success
                B2-->>ServiceWorker: 200 OK
                ServiceWorker->>FastAPI: POST /api/v1/upload/confirm
                FastAPI-->>ServiceWorker: 202 Accepted
                ServiceWorker->>IndexedDB: UPDATE status='completed'
                ServiceWorker->>Browser: postMessage('upload_complete')
                Browser->>User: Show "Uploaded ✓"
            else Upload fails (network error)
                B2-->>ServiceWorker: 5xx or timeout
                ServiceWorker->>IndexedDB: UPDATE retry_count += 1
                
                alt retry_count < 3
                    ServiceWorker->>ServiceWorker: Schedule retry (exponential backoff)
                else retry_count >= 3
                    ServiceWorker->>IndexedDB: UPDATE status='failed'
                    ServiceWorker->>Browser: postMessage('upload_failed')
                    Browser->>User: Show "Upload failed (retry manually)"
                end
            end
            
        else API fails
            FastAPI-->>ServiceWorker: 5xx or network error
            ServiceWorker->>IndexedDB: Keep status='queued'
            ServiceWorker->>BackgroundSync: Re-register for next sync attempt
        end
    end
    
    Note over ServiceWorker,IndexedDB: Cleanup completed uploads after 7 days
    ServiceWorker->>IndexedDB: DELETE FROM pending_uploads<br/>WHERE status='completed' AND created_at < now() - 7 days
```

## 3. Share Link Flow with Signed Short-Lived URLs

```mermaid
sequenceDiagram
    actor Owner
    participant OwnerBrowser as Owner's Browser
    participant FastAPI
    participant Postgres as PostgreSQL
    actor Visitor
    participant VisitorBrowser as Visitor's Browser
    participant CDN as Cloudflare CDN
    participant B2 as Backblaze B2

    Note over Owner,B2: Owner creates share link

    Owner->>OwnerBrowser: Click "Share" on album
    OwnerBrowser->>OwnerBrowser: Show share options dialog
    Owner->>OwnerBrowser: Set: expiry=7days, password=optional, allow_download=true
    
    OwnerBrowser->>FastAPI: POST /api/v1/shares<br/>{photo_ids: [1,2,3], expiry_hours: 168, password_hash, options}
    
    FastAPI->>Postgres: BEGIN TRANSACTION
    FastAPI->>FastAPI: Generate share_token (UUID v4)
    FastAPI->>FastAPI: Generate share_slug (base62, 8 chars, for short URL)
    FastAPI->>Postgres: INSERT INTO shares<br/>(token, slug, owner_id, photo_ids, expires_at, password_hash, options)
    FastAPI->>Postgres: INSERT INTO share_access_log (share_id, event='created')
    FastAPI->>Postgres: COMMIT
    
    FastAPI-->>OwnerBrowser: 201 Created<br/>{share_url: "app.com/s/{slug}", token}
    OwnerBrowser->>Owner: Show shareable link + QR code
    
    Note over Visitor,B2: Visitor accesses share link
    
    Owner->>Visitor: Send share URL (WhatsApp, email, etc.)
    Visitor->>VisitorBrowser: Open app.com/s/{slug}
    
    VisitorBrowser->>FastAPI: GET /s/{slug}
    
    FastAPI->>Postgres: SELECT FROM shares WHERE slug=$1 AND expires_at > now()
    
    alt Share valid
        Postgres-->>FastAPI: Share record (incl password_hash if set)
        
        alt Password protected
            FastAPI-->>VisitorBrowser: 200 OK (render password form)
            Visitor->>VisitorBrowser: Enter password
            VisitorBrowser->>FastAPI: POST /s/{slug}/unlock<br/>{password}
            FastAPI->>FastAPI: Verify bcrypt hash
            
            alt Password correct
                FastAPI->>FastAPI: Generate session JWT (1hr TTL, claim: share_id)
                FastAPI-->>VisitorBrowser: Set-Cookie: share_session={JWT}
            else Password wrong
                FastAPI-->>VisitorBrowser: 401 Unauthorized
                VisitorBrowser->>Visitor: Show "Incorrect password"
            end
        end
        
        FastAPI->>Postgres: SELECT photos WHERE id = ANY(share.photo_ids)
        Postgres-->>FastAPI: Photo metadata (keys, sizes)
        
        FastAPI->>FastAPI: Generate time-limited signed URLs<br/>(HMAC-SHA256, 1hr expiry)<br/>For each thumbnail variant
        
        FastAPI->>Postgres: INSERT INTO share_access_log<br/>(share_id, visitor_ip, user_agent, event='viewed')
        
        FastAPI-->>VisitorBrowser: 200 OK<br/>HTML page with signed thumbnail URLs
        
        VisitorBrowser->>Visitor: Render gallery (lazy load)
        
        loop For each visible thumbnail
            VisitorBrowser->>CDN: GET /thumb/{photo_id}/512.webp?sig={signature}&exp={timestamp}
            
            CDN->>CDN: Validate signature (HMAC with secret key)
            CDN->>CDN: Check expiry timestamp
            
            alt Valid signature & not expired
                alt Cache hit
                    CDN-->>VisitorBrowser: 200 OK (from cache)
                else Cache miss
                    CDN->>B2: GET thumb/{photo_id}/512.webp<br/>(signed B2 request)
                    B2-->>CDN: Image bytes
                    CDN->>CDN: Cache (TTL = min(1hr, URL expiry - now))
                    CDN-->>VisitorBrowser: 200 OK (from origin)
                end
            else Invalid or expired
                CDN-->>VisitorBrowser: 403 Forbidden
                VisitorBrowser->>VisitorBrowser: Show broken image icon
            end
        end
        
        alt Visitor wants to download
            Visitor->>VisitorBrowser: Click "Download original"
            VisitorBrowser->>FastAPI: GET /s/{slug}/download/{photo_id}
            FastAPI->>FastAPI: Verify share_session JWT
            FastAPI->>Postgres: CHECK allow_download option
            
            alt Download allowed
                FastAPI->>B2: Generate presigned download URL (5min TTL)
                B2-->>FastAPI: Presigned URL
                FastAPI-->>VisitorBrowser: 302 Redirect to presigned URL
                VisitorBrowser->>B2: GET original/{photo_id}.jpg
                B2-->>VisitorBrowser: Full-resolution file
                VisitorBrowser->>Visitor: Browser download
                
                FastAPI->>Postgres: INSERT share_access_log<br/>(event='downloaded', photo_id)
            else Download disabled
                FastAPI-->>VisitorBrowser: 403 Forbidden {message: "Downloads disabled by owner"}
            end
        end
        
    else Share expired or not found
        Postgres-->>FastAPI: No rows or expired
        FastAPI-->>VisitorBrowser: 404 Not Found<br/>"This link has expired or doesn't exist"
    end
    
    Note over FastAPI,Postgres: Background job: Auto-expire shares
    
    FastAPI->>Postgres: UPDATE shares SET status='expired'<br/>WHERE expires_at < now() AND status='active'
```

## Implementation Notes

### Upload Flow
- **Chunked uploads**: Split files > 5MB to support resume on network failure (AWS S3 multipart upload pattern works with B2)
- **Client-side SHA256**: Prevent duplicate uploads before sending bytes (use WebCrypto API for performance)
- **Idempotency**: `upload_id` as key ensures duplicate confirm calls don't create duplicate jobs
- **SSE for progress**: Server-Sent Events preferred over WebSocket for simple one-way updates (lower overhead)

**Alternative**: Use GraphQL subscriptions instead of SSE (more complex but unified with existing GraphQL API)

### Offline Sync Flow
- **Background Sync API**: Supported Chrome/Edge/Samsung Internet; fallback to visibility change event for iOS Safari
- **Retry strategy**: Exponential backoff 2^n seconds (max 32s) to avoid thundering herd
- **IndexedDB quota**: Request persistent storage to avoid eviction (navigator.storage.persist())
- **Tradeoff**: Full-resolution photos stored locally can fill quota fast; consider storing only metadata + thumbnail locally

**iOS Safari limitation**: Background Sync API not supported; uploads resume only when app is in foreground. Mitigation: Prompt user to keep app open during upload.

### Share Link Flow
- **Signed URLs**: HMAC-SHA256 with server secret, embed expiry timestamp to allow stateless validation at CDN edge
- **Short slugs**: base62 encoding for human-friendly URLs (e.g., app.com/s/aB3xY9k2)
- **Password hashing**: bcrypt with cost factor 12 (100-200ms to hash, defends against brute force)
- **Rate limiting**: Cloudflare Worker enforces 10 requests/min per IP on share unlock endpoint

**Security consideration**: Share JWTs are HttpOnly cookies to prevent XSS; same-site=strict to prevent CSRF

**Tradeoff**: Signed URLs expire after 1hr, requiring page refresh for long viewing sessions. Alternative: Use CDN with custom auth worker that validates against DB (higher DB load but no expiry).
