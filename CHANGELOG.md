# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Viewer Tracking**: Detailed view tracking for shared album links with `ShareLinkView` model storing individual view events (user, timestamp).
- **Contributor Management**: Album-level contributor management with dedicated UI in album detail page (moved from Share Modal).
- **Storage Provider Abstraction**: Configurable storage backend supporting both Backblaze B2 and S3-compatible services (Cloudflare R2, AWS S3) via `storage_factory.py`.
- **Hybrid Storage Support**: `storage_provider` column in `Photo` model enables simultaneous use of multiple storage backends with automatic provider selection per photo.
- **Place Recognition**: GPS data extraction from EXIF, reverse geocoding to location names, and interactive Map view with clustered markers (Leaflet).
- **Face Recognition**: Automatic face detection using `face_recognition` library, DBSCAN clustering to group faces into people, People gallery page with rename functionality, and pgvector storage for 128-dimensional face embeddings.
- **Object & Scene Detection (Visual Hashtags)**: Upgraded CLIP-based zero-shot classification system. Rebranded "Documents" category to "Visual Hashtags" for a more intuitive user experience. Unified animal and document detections under the "Hashtags" feature.
- **Supabase Keep-Alive**: Implemented a periodic Celery heartbeat task (`keep_db_alive`) that runs every 2 hours to prevent the Supabase database from going dormant.
- **Database Indexing**: Added critical performance indexes on `tags.category`, `photo_tags.tag_id`, and `photo_tags.tag_confidence` to optimize hashtag-based search and filtering.
- **Hashtag API Optimizations**: Resolved N+1 query bottlenecks in the hashtags listing API using batch fetching and introduced limit/offset pagination to the hashtag photos endpoint for significantly faster page loads.
- **Google Login**: Support for users to sign in/up with their Google accounts via OAuth2.
- **Trash & Restore**: Soft delete functionality for photos with a Trash view and Restore/Permanent Delete options.
- **Secure Image Serving**: Implemented Ahead-Of-Time (AOT) Presigned URLs to serve all images securely without JWTs in URLs.
- **Share Modal Improvements**: Enhanced UI with tabbed interface separating "Public Links" and "Viewers", displaying aggregated viewer list across all share links.
- **Keyboard Accessibility**: Full keyboard navigation support across the application. Implemented global focus rings, `Escape` to close modals, `Enter` to confirm actions, and focusable photo grid items.
- **Direct Photo Sharing**: Implemented end-to-end photo sharing via email, including "Inbox" and "Connections" tabs, secure invite links for non-users, and claim functionality upon registration.
- **Animal Detection Parity**: Fully implemented Animal detection with dedicated API endpoints, filtering, and UI (feature parity with People).
- **Admin Dashboard**: Comprehensive admin interface with multi-user selection (checklist UI), maintenance triggers (clustering, re-scanning), and live system logs.
- **GCE Deployment Script**: Added `deploy_gce_worker.sh` to automate the update and restart process for remote Celery workers on Google Compute Engine.
- **Self-Hosted Redis**: Migrated from Upstash to self-hosted Redis on GCE (35.226.33.89:6379) with password authentication for improved stability and cost reduction.
- **Admin Job Tracking**: Added `AdminJob` model and database table to track maintenance job history (clustering, re-scanning) with status tracking and error logging.
- **Admin Performance Indexes**: Added B-Tree indexes on `admin_jobs.status`, `admin_jobs.created_at`, and `admin_jobs.user_id` for faster job queries and filtering.
- **Production Docker Compose**: Created `docker-compose.prod.yml` without code volume mounts to ensure production deployments use image code, not host code.
- **GitHub Actions Workflows**: Split deployment workflows into `build-and-deploy-gce.yml` (full stack), `build-and-deploy-worker-only.yml` (worker-specific), and `deploy-redis-only.yml` (Redis-specific) for granular deployment control.

### Fixed
- **Admin API Validation**: Resolved `ResponseValidationError` by handling `NULL` values for `is_admin` in the database.
- **Admin Routing**: Fixed 404 error on `/admin/users` endpoint by correctly registering and implementing the listing function.
- **Security**: Enforced strict role-based access control (RBAC) on admin routes in both Frontend (`AdminRoute`) and Backend.
- **Celery Task Sending**: Fixed critical `ImportError` in `process_clustering_job()` where `async_session_factory` (non-existent) was imported instead of `AsyncSessionLocal`. This caused BackgroundTasks to fail silently before any debug logs ran, preventing tasks from reaching the GCE worker.
- **BackgroundTask Silent Failures**: Added comprehensive debug logging with `print(..., flush=True)` and broker connection tests to expose Celery connection failures that Starlette's BackgroundTasks were silently swallowing.
- **Admin API Performance**: Refactored `/admin/cluster` endpoint to use `BackgroundTasks` instead of synchronous processing, eliminating timeout issues for users with large photo collections.
- **Worker Code Deployment**: Fixed production worker deployments by creating `docker-compose.prod.yml` without `./backend:/app` volume mounts, ensuring workers run image code instead of potentially empty/outdated host directories.
- **GitHub Actions Triggers**: Updated workflow `paths` filters to include `docker-compose.prod.yml` and fixed deployment script permissions (`chmod +x start_worker.sh`).

### Changed
- **Hashtag UI**: refined Hashtag Detail view to hide raw UUIDs, displaying a fallback title if the tag name is unresolvable, and sorting tags by confidence score.

### Fixed
- **UI Z-Index & Initials**: Fixed z-index stacking issue for User Profile dropdown and corrected fallback initials generation.
- **Broken Thumbnails**: Fixed "NoSuchKey" errors in `rescan_photos.py` and successfully repaired 65+ broken thumbnails/orphaned files.
- **Hashtag Display**: Resolved "0 Photos" bug for certain hashtags by enabling UUID-based lookup in frontend routing.
- **OCR Tagging**: Restored Tesseract OCR functionality, enabling text extraction for documents (e.g., #invoice, #receipt).
- **Gallery UI Overhaul**: Complete redesign of the photo timeline with premium glassmorphism aesthetics, contextual selection headers, and refined spacing.
- **View Settings**: Consolidated grid density (Compact/Comfortable/Large) and date grouping (Day/Month/Year) controls into a unified Jira-style dropdown menu.
- **Hashtag Display**: Updated hashtag visibility logic to remain hidden by default and fade in smoothly on hover to reduce visual clutter.
- **Optimistic UI**: Implemented instant feedback for "Favorite" actions using robust optimistic cache updates, eliminating perceived API latency.
- **Viewer Display**: Refactored Share Modal to show aggregated viewers in dedicated "Viewers" tab instead of inline under each link.
- **Contributor Management**: Moved contributor invitation and management from Share Modal to album detail page for better UX and clearer separation of concerns.
- **Storage Architecture**: Migrated from single B2 provider to pluggable storage architecture supporting B2, S3, and R2 with per-photo provider tracking.
- **Thumbnail Generation**: Fully implemented libvips worker with support for WhatsApp filename date extraction.
- **Documentation**: Updated README, PROGRESS, and Architecture docs to reflect MVP complete status.
- **Deployment Guide**: Updated GITHUB_DEPLOYMENT.md to reflect split architecture (Cloudflare + VPS).
- **Storage Migration**: Replaced all Backblaze B2 references with Cloudflare R2 across documentation (README, Architecture, Cost Model, Checklists).
- **Documentation Audit**: Synchronized all docs with codebase reality - marked Albums as Complete, Face Recognition & Sharing as In Progress.
- **Visual Hashtags Rebranding**: Renamed "Documents" feature to "Hashtags" across backend APIs, frontend routes, and UI components. Updated sidebar and detail views to use the new nomenclature and icons.
- **SQLAlchemy Optimization**: Resolved SQLAlchemy `SAWarning` related to overlapping relationships by adding the `overlaps` parameter to `Tag` and `Photo` models.
- **Sharing Permissions**: Enforced stricter permissions for shared content. Recipients cannot re-share items or add them to other albums. Contributors to shared albums can only delete their own photos.
- **Shared Album Navigation**: Improved navigation flow with dynamic "Back" buttons and exclusion of shared albums from the main "Albums" listing to reduce clutter.

### Fixed
- **Selection Mode Crash**: Resolved `ReferenceError` for `CheckSquare` icon in PhotoItem component.
- **Favorite API**: Fixed malformed API URL generation (`/ photos /` -> `/photos/`) preventing favorite actions.
- **Delete Button**: Corrected positioning and styling of the delete button in the photo overlay.
- **Shared Link Access**: Added error handling for viewer tracking to prevent shared link failures when database writes fail.
- **Storage Provider Selection**: Fixed photo retrieval to use correct storage provider per photo for hybrid storage scenarios.
- **Missing Thumbnails**: Fixed issue where face/animal crops were generated but not saved to storage. Created `regenerate_crops.py` to restore missing files.
- **Render Deployment**: Fixed deployment timeout by correctly exposing port 10000 in Dockerfile to match Render's environment.
- **Frontend Build**: Fixed `react-leaflet-cluster` peer dependency conflicts to ensure successful CI/CD builds.
- **Backend Build Time**: Reduced build time by implementing a pre-baked base image (`bhargavkumar1612/photobomb-base:v1`) containing heavy ML dependencies.
- **Database Migrations**: Refactored Alembic migrations to be idempotent and robust against re-runs.
- **Security**: Added `Cross-Origin-Opener-Policy` (COOP) header to backend responses.
- **Process Management**: Optimized Uvicorn worker count and added interaction checks to maintenance scripts.
- **Date Handling**: Fixed `Invalid Date` errors in sharing views by implementing `shared_at` timestamp and fallback logic for `uploaded_at`.
- **Album Covers**: Added fallback logic to use the first photo as a thumbnail if an album has no explicit cover photo set.

## [0.1.0] - 2024-12-10
### Added
- Initial MVP Release.
- Core Upload & View functionality.
- B2 Storage integration with Presigned URLs.
- JWT Authentication.
- PWA Offline support with Service Worker.
