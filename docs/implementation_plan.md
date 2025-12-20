# Implementation Plan: Session 5 Polish & Future Roadmap

## Session 5: Polish & Fixes (Current)

### Goal
Enhance user experience with professional loading states, improved album visuals, and stability fixes.

### User Review Required
- [ ] Confirm collage layout preference (currently planning 1 main + 2 stacked side images).

### Proposed Changes

#### Frontend
- [NEW] `src/components/skeletons/PhotoCardSkeleton.jsx`: Shimmer loading placeholder.
- [NEW] `src/components/skeletons/AlbumCardSkeleton.jsx`: Shimmer for albums.
- [MODIFY] `src/pages/Timeline.jsx`: Integrate skeletons during `isLoading`.
- [MODIFY] `src/components/Lightbox.jsx`: Add spinner/pulse while high-res image loads.
- [MODIFY] `src/pages/Albums.jsx`: Update album card to support collage view.
- [MODIFY] `src/pages/Albums.css`: Styles for collage layout (1 main + 2 side stacked).

#### Backend
- [MODIFY] `app/api/albums.py`: Update `list_albums` to return `recent_photos` (first 3) for collage generation.
- [MODIFY] `app/schemas/album.py`: Update `AlbumResponse` schema to include `thumbnail_ids` list.

### Verification Plan
- [ ] Visual check of loading skeletons on slow network (simulated).
- [ ] Create album with 1, 2, 3, and 4 photos to verify collage adaptability.
- [ ] Check terminal logs for clean startup.

---

## Session 6: Advanced Features (Next)

### Trash/Restore
- [ ] Create `/trash` route
- [ ] Backend: list deleted photos (`deleted_at` is not null)
- [ ] Backend: restore endpoint
- [ ] Backend: permanent delete endpoint
- [ ] Restore button UI
- [ ] Permanent delete confirmation
- [ ] 30-day auto-delete (backend cron)

### Settings Page
- [ ] Create `/settings` route
- [ ] Account section (email, name)
- [ ] Storage usage visualization
- [ ] Privacy toggles
- [ ] Appearance preferences
- [ ] Delete account (danger zone)
- [ ] Save settings endpoint

## Session 7: Cloud & Deployment (Future)

- [ ] Dockerize application
- [ ] Configure specialized Celery workers
- [ ] Implement face recognition (deep learning model)
- [ ] EXIF data extraction and searching
- [ ] Map view for geotagged photos
