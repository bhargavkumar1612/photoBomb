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

### Changed
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

### Fixed
- **Shared Link Access**: Added error handling for viewer tracking to prevent shared link failures when database writes fail.
- **Storage Provider Selection**: Fixed photo retrieval to use correct storage provider per photo for hybrid storage scenarios.

## [0.1.0] - 2024-12-10
### Added
- Initial MVP Release.
- Core Upload & View functionality.
- B2 Storage integration with Presigned URLs.
- JWT Authentication.
- PWA Offline support with Service Worker.
