import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
    CheckSquare,
    LayoutGrid,
    Grid3X3,
    Square,
    MoreVertical,
    CheckCircle2,
    X,
    Trash2,
    FolderPlus,
    Settings
} from 'lucide-react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import SearchBar from '../components/SearchBar'
import AddToAlbumModal from '../components/AddToAlbumModal'
import ShareModal from '../components/ShareModal'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import PhotoItem from '../components/PhotoItem'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { useSearch } from '../context/SearchContext'
import { groupPhotosByDate, groupPhotosByMonth, groupPhotosByYear } from '../utils/dateGrouping'
import { usePhotoFilter } from '../hooks/usePhotoFilter'
import './Timeline.css'

export default function Timeline({ favoritesOnly = false }) {
    const { user } = useAuth()
    const { searchTerm, filters, setFilters } = useSearch()
    const queryClient = useQueryClient()

    // View States
    const [viewMode, setViewMode] = useState('day')

    const [deletingPhoto, setDeletingPhoto] = useState(null)
    const [selectedPhotos, setSelectedPhotos] = useState(new Set())
    const [selectionMode, setSelectionMode] = useState(false)
    const [gridSize, setGridSize] = useState(localStorage.getItem('gridSize') || 'comfortable')
    const [showViewSettings, setShowViewSettings] = useState(false)
    const [showFavoritesOnly, setShowFavoritesOnly] = useState(favoritesOnly)
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [showAlbumModal, setShowAlbumModal] = useState(false)
    const [batchAlbumPhotoIds, setBatchAlbumPhotoIds] = useState([])
    const [sharePhotoIds, setSharePhotoIds] = useState(null)

    const { data, isLoading, error } = useQuery({
        queryKey: ['photos'],
        queryFn: async () => {
            const response = await api.get('/photos')
            return response.data
        }
    })

    const favoriteMutation = useMutation({
        mutationFn: (photoId) => api.patch(`/photos/${photoId}/favorite`),
        onMutate: async (photoId) => {
            // Cancel any outgoing refetches
            await queryClient.cancelQueries({ queryKey: ['photos'] })

            // Snapshot the previous value
            const previousPhotos = queryClient.getQueryData(['photos'])

            // Optimistically update to the new value
            queryClient.setQueryData(['photos'], (old) => {
                if (!old) return old

                // Handle case where data is { photos: [...], ... }
                if (old.photos && Array.isArray(old.photos)) {
                    return {
                        ...old,
                        photos: old.photos.map(photo =>
                            photo.photo_id === photoId
                                ? { ...photo, favorite: !photo.favorite }
                                : photo
                        )
                    }
                }

                // Fallback for array structure (if API changes back)
                if (Array.isArray(old)) {
                    return old.map(photo =>
                        photo.photo_id === photoId
                            ? { ...photo, favorite: !photo.favorite }
                            : photo
                    )
                }

                return old
            })

            // Return a context object with the snapshotted value
            return { previousPhotos }
        },
        onError: (err, photoId, context) => {
            if (context?.previousPhotos) {
                queryClient.setQueryData(['photos'], context.previousPhotos)
            }
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['photos'] })
        }
    })

    const handleCleanup = async () => {
        if (!window.confirm('Remove all broken photos (photos with missing files)? This will help clean up your library.')) return
        try {
            await api.delete('/upload/cleanup/orphaned?dry_run=false')
            queryClient.invalidateQueries({ queryKey: ['photos'] })
        } catch (error) {
            alert(`Cleanup failed: ${error.message}`)
        }
    }

    const handleDelete = async (photoId, photoName) => {
        if (!window.confirm(`Delete ${photoName}? This cannot be undone.`)) return
        setDeletingPhoto(photoId)
        try {
            await api.delete(`/photos/${photoId}`)
            queryClient.invalidateQueries({ queryKey: ['photos'] })
            if (lightboxPhoto?.photo_id === photoId) setLightboxPhoto(null)
        } catch (error) {
            alert(`Failed to delete: ${error.message}`)
        } finally {
            setDeletingPhoto(null)
        }
    }

    const handleBulkDelete = async () => {
        if (!window.confirm(`Delete ${selectedPhotos.size} photos? This cannot be undone.`)) return
        try {
            await api.post('/photos/batch/delete', { photo_ids: Array.from(selectedPhotos) })
            queryClient.invalidateQueries({ queryKey: ['photos'] })
            setSelectedPhotos(new Set())
            setSelectionMode(false)
        } catch (error) {
            alert(`Failed to delete photos: ${error.message}`)
        }
    }

    const handleDownload = async (photo) => {
        const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'
        const url = photo.thumb_urls.original || `${apiBaseUrl}/photos/${photo.photo_id}/download`
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        link.target = "_blank"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    const handleShare = (photo) => {
        setSharePhotoIds([photo.photo_id])
    }

    const handleInfo = (photo) => {
        alert(`File: ${photo.filename}\nType: ${photo.mime_type}\nDate: ${new Date(photo.taken_at || photo.uploaded_at).toLocaleString()}`)
    }

    const handleAddToAlbum = (photo) => {
        setBatchAlbumPhotoIds([photo.photo_id])
        setShowAlbumModal(true)
    }

    const handleBulkAddToAlbum = () => {
        setBatchAlbumPhotoIds(Array.from(selectedPhotos))
        setShowAlbumModal(true)
    }

    const toggleSelection = (photoId) => {
        if (!selectionMode) setSelectionMode(true)
        const newSelection = new Set(selectedPhotos)
        newSelection.has(photoId) ? newSelection.delete(photoId) : newSelection.add(photoId)
        setSelectedPhotos(newSelection)
    }

    const cancelSelection = () => {
        setSelectedPhotos(new Set())
        setSelectionMode(false)
    }

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        900: gridSize === 'compact' ? 3 : 2,
        600: gridSize === 'compact' ? 3 : gridSize === 'comfortable' ? 2 : 1
    }

    const basePhotos = useMemo(() => {
        return showFavoritesOnly || favoritesOnly ? data?.photos?.filter(p => p.favorite) : data?.photos
    }, [data?.photos, showFavoritesOnly, favoritesOnly])

    const filteredPhotos = usePhotoFilter(basePhotos)

    const groupedPhotos = useMemo(() => {
        switch (viewMode) {
            case 'month':
                return groupPhotosByMonth(filteredPhotos);
            case 'year':
                return groupPhotosByYear(filteredPhotos);
            case 'day':
            default:
                return groupPhotosByDate(filteredPhotos);
        }
    }, [filteredPhotos, viewMode])

    if (error) return <div className="error">Error: {error.message}</div>

    return (
        <div className="timeline-wrapper">
            {/* Note: TopBar handles Search now, so SearchBar is just filtered list here if we want filtering */}
            {/* Actually, user feedback implies filters panel is used. We can keep SearchBar just for filtering without input if needed,
                 OR we rely on TopBar. But SearchBar state is shared via Context now.
                 The Timeline needs the Layout to provide the TopBar. Timeline itself is just content.
                 If we put SearchBar here, it might duplicate or be the intended place for filters only.
                 The user screenshot shows filters.
                 I will keep SearchBar hidden or styled minimally if it's cleaner, but for now removing duplicate UI is safer.
                 Wait, the SearchBar component HAS the filter UI. So we need it rendered somewhere.
                 TopBar renders SearchBar. So we don't need it here.
             */}

            {/* Main Layout for Timeline with Sidebar-like filtering */}
            <div className="timeline-layout-container">
                <div className={`timeline-sub-header ${selectionMode ? 'selection-mode' : ''}`}>
                    {!selectionMode ? (
                        <>
                            <div className="sub-header-left">
                                <h1
                                    className={`header-tab ${!showFavoritesOnly ? 'active' : ''}`}
                                    onClick={() => setShowFavoritesOnly(false)}
                                    tabIndex={0}
                                    role="button"
                                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowFavoritesOnly(false); } }}
                                >
                                    Photos
                                </h1>
                                <h1
                                    className={`header-tab ${showFavoritesOnly ? 'active' : ''}`}
                                    onClick={() => setShowFavoritesOnly(true)}
                                    tabIndex={0}
                                    role="button"
                                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowFavoritesOnly(true); } }}
                                >
                                    Favorites
                                </h1>
                            </div>

                            <div className="sub-header-center">
                                {/* View mode tabs removed, now in dropdown */}
                            </div>

                            <div className="sub-header-right">
                                <button
                                    className="btn-icon-round"
                                    onClick={() => setSelectionMode(true)}
                                    title="Select Photos"
                                >
                                    <CheckSquare size={18} />
                                </button>

                                <div className="view-settings-wrapper">
                                    <button
                                        className="btn-icon-round"
                                        onClick={() => setShowViewSettings(!showViewSettings)}
                                        title="View Settings"
                                    >
                                        <Settings size={18} />
                                    </button>

                                    {showViewSettings && (
                                        <>
                                            <div
                                                className="view-settings-backdrop"
                                                onClick={() => setShowViewSettings(false)}
                                            />
                                            <div className="view-settings-dropdown">
                                                <div className="dropdown-section">
                                                    <div className="dropdown-label">Group By</div>
                                                    <div className="dropdown-options">
                                                        <button
                                                            className={viewMode === 'day' ? 'active' : ''}
                                                            onClick={() => { setViewMode('day'); setShowViewSettings(false); }}
                                                        >
                                                            Day
                                                        </button>
                                                        <button
                                                            className={viewMode === 'month' ? 'active' : ''}
                                                            onClick={() => { setViewMode('month'); setShowViewSettings(false); }}
                                                        >
                                                            Month
                                                        </button>
                                                        <button
                                                            className={viewMode === 'year' ? 'active' : ''}
                                                            onClick={() => { setViewMode('year'); setShowViewSettings(false); }}
                                                        >
                                                            Year
                                                        </button>
                                                    </div>
                                                </div>

                                                <div className="dropdown-divider" />

                                                <div className="dropdown-section">
                                                    <div className="dropdown-label">Grid Density</div>
                                                    <div className="dropdown-options">
                                                        <button
                                                            className={gridSize === 'compact' ? 'active' : ''}
                                                            onClick={() => { setGridSize('compact'); setShowViewSettings(false); }}
                                                        >
                                                            <Grid3X3 size={16} />
                                                            <span>Compact</span>
                                                        </button>
                                                        <button
                                                            className={gridSize === 'comfortable' ? 'active' : ''}
                                                            onClick={() => { setGridSize('comfortable'); setShowViewSettings(false); }}
                                                        >
                                                            <LayoutGrid size={16} />
                                                            <span>Comfortable</span>
                                                        </button>
                                                        <button
                                                            className={gridSize === 'cozy' ? 'active' : ''}
                                                            onClick={() => { setGridSize('cozy'); setShowViewSettings(false); }}
                                                        >
                                                            <Square size={16} />
                                                            <span>Large</span>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="sub-header-left">
                                <button className="btn-icon-round cancel" onClick={cancelSelection}>
                                    <X size={20} />
                                </button>
                                <div className="selection-count">
                                    <span>{selectedPhotos.size} selected</span>
                                </div>
                            </div>

                            <div className="sub-header-center">
                                <button
                                    className="btn-text-select-all"
                                    onClick={() => {
                                        const allIds = filteredPhotos.map(p => p.photo_id)
                                        if (selectedPhotos.size === allIds.length) {
                                            setSelectedPhotos(new Set())
                                        } else {
                                            setSelectedPhotos(new Set(allIds))
                                        }
                                    }}
                                >
                                    {selectedPhotos.size === filteredPhotos.length ? 'Deselect All' : 'Select All'}
                                </button>
                            </div>

                            <div className="sub-header-right">
                                {selectedPhotos.size > 0 && (
                                    <div className="selection-actions">
                                        <button className="btn-secondary" onClick={() => setSharePhotoIds(Array.from(selectedPhotos))}>
                                            <Share2 size={16} />
                                            <span>Share</span>
                                        </button>
                                        <button className="btn-secondary" onClick={handleBulkAddToAlbum}>
                                            <FolderPlus size={16} />
                                            <span>Add to Album</span>
                                        </button>
                                        <button className="btn-secondary danger" onClick={handleBulkDelete}>
                                            <Trash2 size={16} />
                                            <span>Delete</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>

                <div className="timeline-content">
                    {isLoading ? (
                        <Masonry breakpointCols={breakpointColumns} className="masonry-grid" columnClassName="masonry-column">
                            {[...Array(12)].map((_, i) => <PhotoCardSkeleton key={i} />)}
                        </Masonry>
                    ) : filteredPhotos.length === 0 ? (
                        <div className="empty-state">
                            <h3>No photos found</h3>
                        </div>
                    ) : (
                        groupedPhotos.map((group) => {
                            const groupPhotoIds = group.photos.map(p => p.photo_id)
                            const isGroupSelected = groupPhotoIds.every(id => selectedPhotos.has(id))
                            const isGroupPartiallySelected = !isGroupSelected && groupPhotoIds.some(id => selectedPhotos.has(id))

                            return (
                                <div key={group.label} className="date-group">
                                    <h3 className="group-header">
                                        {selectionMode && (
                                            <div
                                                className={`group-checkbox ${isGroupSelected ? 'selected' : ''} ${isGroupPartiallySelected ? 'partial' : ''}`}
                                                tabIndex={0}
                                                role="checkbox"
                                                aria-checked={isGroupSelected ? "true" : isGroupPartiallySelected ? "mixed" : "false"}
                                                onClick={() => {
                                                    const newSelection = new Set(selectedPhotos)
                                                    if (isGroupSelected) {
                                                        groupPhotoIds.forEach(id => newSelection.delete(id))
                                                    } else {
                                                        groupPhotoIds.forEach(id => newSelection.add(id))
                                                    }
                                                    setSelectedPhotos(newSelection)
                                                }}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter' || e.key === ' ') {
                                                        e.preventDefault()
                                                        const newSelection = new Set(selectedPhotos)
                                                        if (isGroupSelected) {
                                                            groupPhotoIds.forEach(id => newSelection.delete(id))
                                                        } else {
                                                            groupPhotoIds.forEach(id => newSelection.add(id))
                                                        }
                                                        setSelectedPhotos(newSelection)
                                                    }
                                                }}
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: '20px',
                                                    height: '20px',
                                                    border: '2px solid #d1d5db',
                                                    borderRadius: '4px',
                                                    marginRight: '12px',
                                                    cursor: 'pointer',
                                                    backgroundColor: isGroupSelected || isGroupPartiallySelected ? '#3b82f6' : 'white',
                                                    borderColor: isGroupSelected || isGroupPartiallySelected ? '#3b82f6' : '#d1d5db',
                                                    verticalAlign: 'middle'
                                                }}
                                            >
                                                {isGroupSelected && <CheckSquare size={14} color="white" />}
                                                {isGroupPartiallySelected && <div style={{ width: '10px', height: '2px', background: 'white' }} />}
                                            </div>
                                        )}
                                        {group.label}
                                    </h3>
                                    <Masonry
                                        breakpointCols={breakpointColumns}
                                        className={`my-masonry-grid photo-grid ${gridSize}`}
                                        columnClassName="my-masonry-grid_column"
                                    >
                                        {group.photos.map(photo => (
                                            <PhotoItem
                                                key={photo.photo_id}
                                                photo={photo}
                                                selectionMode={selectionMode}
                                                isSelected={selectedPhotos.has(photo.photo_id)}
                                                onToggleSelection={toggleSelection}
                                                onLightbox={setLightboxPhoto}
                                                onFavorite={(id) => favoriteMutation.mutate(id)}
                                                isDeleting={deletingPhoto === photo.photo_id}
                                                onDelete={handleDelete}
                                                onDownload={handleDownload}
                                                onInfo={handleInfo}
                                                onShare={handleShare}
                                                onAddToAlbum={handleAddToAlbum}
                                            />
                                        ))}
                                    </Masonry>
                                </div>
                            )
                        })
                    )}
                </div>

                {lightboxPhoto && (
                    <Lightbox
                        photo={lightboxPhoto}
                        photos={filteredPhotos}
                        onClose={() => setLightboxPhoto(null)}
                        onNavigate={setLightboxPhoto}
                    />
                )}

                <AddToAlbumModal
                    isOpen={showAlbumModal}
                    onClose={() => setShowAlbumModal(false)}
                    photoIds={batchAlbumPhotoIds}
                />

                <ShareModal
                    isOpen={!!sharePhotoIds}
                    onClose={() => setSharePhotoIds(null)}
                    photoIds={sharePhotoIds || []}
                />
            </div>
        </div>
    )
}
