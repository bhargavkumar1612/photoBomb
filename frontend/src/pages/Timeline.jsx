import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { CheckSquare } from 'lucide-react'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import SearchBar from '../components/SearchBar'
import AddToAlbumModal from '../components/AddToAlbumModal'
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
    const [showFavoritesOnly, setShowFavoritesOnly] = useState(favoritesOnly)
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [showAlbumModal, setShowAlbumModal] = useState(false)
    const [batchAlbumPhotoIds, setBatchAlbumPhotoIds] = useState([])

    const { data, isLoading, error } = useQuery({
        queryKey: ['photos'],
        queryFn: async () => {
            const response = await api.get('/photos')
            return response.data
        }
    })

    const favoriteMutation = useMutation({
        mutationFn: (photoId) => api.patch(`/photos/${photoId}/favorite`),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['photos'] })
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
        for (const photoId of selectedPhotos) {
            try { await api.delete(`/photos/${photoId}`) } catch (e) { console.error(e) }
        }
        queryClient.invalidateQueries({ queryKey: ['photos'] })
        setSelectedPhotos(new Set())
        setSelectionMode(false)
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
        const apiBaseUrl = import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`
        const url = photo.thumb_urls.original || `${apiBaseUrl}/photos/${photo.photo_id}/download`
        if (navigator.share) {
            navigator.share({ title: photo.filename, url })
        } else {
            navigator.clipboard.writeText(url)
            alert('Link copied!')
        }
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
        600: 2
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
                <div className="timeline-sub-header">
                    <div className="sub-header-left">
                        <h1
                            className={`header-tab ${!showFavoritesOnly ? 'active' : ''}`}
                            onClick={() => setShowFavoritesOnly(false)}
                        >
                            Photos
                        </h1>
                        <h1
                            className={`header-tab ${showFavoritesOnly ? 'active' : ''}`}
                            onClick={() => setShowFavoritesOnly(true)}
                        >
                            Favorites
                        </h1>
                    </div>

                    <div className="sub-header-center">
                        <div className="segmented-control">
                            <button
                                className={viewMode === 'day' ? 'active' : ''}
                                onClick={() => setViewMode('day')}
                            >Day</button>
                            <button
                                className={viewMode === 'month' ? 'active' : ''}
                                onClick={() => setViewMode('month')}
                            >Month</button>
                            <button
                                className={viewMode === 'year' ? 'active' : ''}
                                onClick={() => setViewMode('year')}
                            >Year</button>
                        </div>
                    </div>

                    <div className="sub-header-right">
                        <button
                            className={`btn-icon-round ${selectionMode ? 'active' : ''}`}
                            onClick={() => {
                                if (selectionMode) cancelSelection();
                                else setSelectionMode(true);
                            }}
                            title={selectionMode ? 'Cancel Selection' : 'Select Photos'}
                        >
                            <CheckSquare size={18} />
                        </button>

                        <div className="segmented-control small">
                            <button className={gridSize === 'compact' ? 'active' : ''} onClick={() => setGridSize('compact')} title="Compact">▦</button>
                            <button className={gridSize === 'comfortable' ? 'active' : ''} onClick={() => setGridSize('comfortable')} title="Comfortable">▣</button>
                            <button className={gridSize === 'cozy' ? 'active' : ''} onClick={() => setGridSize('cozy')} title="Large">▢</button>
                        </div>

                        {selectionMode && selectedPhotos.size > 0 && (
                            <div className="selection-actions">
                                <span>{selectedPhotos.size} selected</span>
                                <button className="btn-secondary" onClick={handleBulkAddToAlbum}>Add to Album</button>
                                <button className="btn-secondary danger" onClick={handleBulkDelete}>Delete</button>
                            </div>
                        )}
                    </div>
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
                        groupedPhotos.map((group) => (
                            <div key={group.label} className="date-group">
                                <h3 className="group-header">{group.label}</h3>
                                <Masonry
                                    breakpointCols={breakpointColumns}
                                    className="my-masonry-grid"
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
                        ))
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
            </div>
        </div>
    )
}
