import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import SearchBar from '../components/SearchBar'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import PhotoItem from '../components/PhotoItem'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import './Timeline.css'

export default function Timeline({ favoritesOnly = false }) {
    const { user } = useAuth()
    const queryClient = useQueryClient()
    const [deletingPhoto, setDeletingPhoto] = useState(null)
    const [selectedPhotos, setSelectedPhotos] = useState(new Set())
    const [selectionMode, setSelectionMode] = useState(false)
    const [gridSize, setGridSize] = useState(localStorage.getItem('gridSize') || 'comfortable')
    const [showFavoritesOnly, setShowFavoritesOnly] = useState(favoritesOnly)
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [cleaning, setCleaning] = useState(false)
    const [searchTerm, setSearchTerm] = useState('')
    const [filters, setFilters] = useState({
        sortBy: 'date-desc',
        fileTypes: [],
        dateFrom: '',
        dateTo: ''
    })
    const [showAlbumModal, setShowAlbumModal] = useState(false)
    const [photoToAddToAlbum, setPhotoToAddToAlbum] = useState(null)

    const { data, isLoading, error } = useQuery({
        queryKey: ['photos'],
        queryFn: async () => {
            const response = await api.get('/photos')
            return response.data
        }
    })

    const { data: albums } = useQuery({
        queryKey: ['albums'],
        queryFn: async () => {
            const response = await api.get('/albums')
            return response.data
        }
    })

    const addToAlbumMutation = useMutation({
        mutationFn: async ({ albumId, photoId }) => {
            await api.post(`/albums/${albumId}/photos/${photoId}`)
        },
        onSuccess: () => {
            setShowAlbumModal(false)
            setPhotoToAddToAlbum(null)
        }
    })

    const favoriteMutation = useMutation({
        mutationFn: (photoId) => api.patch(`/photos/${photoId}/favorite`),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['photos'] })
    })

    const handleCleanup = async () => {
        if (!window.confirm('Remove all broken photos (photos with missing files)? This will help clean up your library.')) return

        setCleaning(true)
        try {
            const response = await api.delete('/upload/cleanup/orphaned?dry_run=false')
            alert(`Cleaned up ${response.data.orphaned_count} broken photos`)
            queryClient.invalidateQueries({ queryKey: ['photos'] })
        } catch (error) {
            alert(`Cleanup failed: ${error.response?.data?.detail || error.message}`)
        } finally {
            setCleaning(false)
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
            alert(`Failed to delete: ${error.response?.data?.detail || error.message}`)
        } finally {
            setDeletingPhoto(null)
        }
    }

    const handleBulkDelete = async () => {
        if (!window.confirm(`Delete ${selectedPhotos.size} photos?`)) return

        for (const photoId of selectedPhotos) {
            try {
                await api.delete(`/photos/${photoId}`)
            } catch (e) { console.error(e) }
        }
        queryClient.invalidateQueries({ queryKey: ['photos'] })
        setSelectedPhotos(new Set())
        setSelectionMode(false)
    }

    const handleBulkFavorite = async () => {
        for (const photoId of selectedPhotos) {
            try {
                await favoriteMutation.mutateAsync(photoId)
            } catch (e) { console.error(e) }
        }
        setSelectedPhotos(new Set())
        setSelectionMode(false)
    }

    const toggleSelection = (photoId) => {
        const newSelection = new Set(selectedPhotos)
        newSelection.has(photoId) ? newSelection.delete(photoId) : newSelection.add(photoId)
        setSelectedPhotos(newSelection)
    }

    const handleDownload = async (photo) => {
        const url = `/api/v1/photos/${photo.photo_id}/download?token=${localStorage.getItem('access_token')}`
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    const handleShare = (photo) => {
        const url = `${window.location.origin}/api/v1/photos/${photo.photo_id}/download?token=${localStorage.getItem('access_token')}`
        if (navigator.share) {
            navigator.share({ title: photo.filename, url })
        } else {
            navigator.clipboard.writeText(url)
            alert('Link copied to clipboard!')
        }
    }

    const handleInfo = (photo) => {
        alert(`File: ${photo.filename}\nSize: ${(photo.size_bytes / 1024 / 1024).toFixed(2)} MB\nType: ${photo.mime_type}\nUploaded: ${new Date(photo.uploaded_at).toLocaleString()}`)
    }

    const handleAddToAlbum = (photo) => {
        setPhotoToAddToAlbum(photo)
        setShowAlbumModal(true)
    }

    const handleAlbumSelect = (albumId) => {
        if (photoToAddToAlbum) {
            addToAlbumMutation.mutate({
                albumId,
                photoId: photoToAddToAlbum.photo_id
            })
        }
    }

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        900: gridSize === 'compact' ? 3 : 2,
        600: 2
    }

    // Filter and sort photos (must be before early returns to preserve hook order)
    const filteredPhotos = useMemo(() => {
        let photos = showFavoritesOnly ? data?.photos?.filter(p => p.favorite) : data?.photos
        if (!photos) return []

        // Apply search filter
        if (searchTerm) {
            const term = searchTerm.toLowerCase()
            photos = photos.filter(p =>
                p.filename.toLowerCase().includes(term) ||
                (p.caption && p.caption.toLowerCase().includes(term)) ||
                (p.location_name && p.location_name.toLowerCase().includes(term))
            )
        }

        // Apply file type filter
        if (filters.fileTypes?.length > 0) {
            photos = photos.filter(p => filters.fileTypes.includes(p.mime_type))
        }

        // Apply date range filter
        if (filters.dateFrom) {
            const fromDate = new Date(filters.dateFrom)
            photos = photos.filter(p => new Date(p.uploaded_at) >= fromDate)
        }
        if (filters.dateTo) {
            const toDate = new Date(filters.dateTo)
            toDate.setHours(23, 59, 59)
            photos = photos.filter(p => new Date(p.uploaded_at) <= toDate)
        }

        // Apply sorting
        const sorted = [...photos]
        switch (filters.sortBy) {
            case 'date-desc':
                sorted.sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at))
                break
            case 'date-asc':
                sorted.sort((a, b) => new Date(a.uploaded_at) - new Date(b.uploaded_at))
                break
            case 'name':
                sorted.sort((a, b) => a.filename.localeCompare(b.filename))
                break
            case 'size':
                sorted.sort((a, b) => b.size_bytes - a.size_bytes)
                break
            default:
                break
        }

        return sorted
    }, [data?.photos, showFavoritesOnly, searchTerm, filters])

    if (isLoading) return <div className="loading">Loading photos...</div>
    if (error) return <div className="error">Error: {error.message}</div>

    return (
        <div className="timeline-wrapper">
            <SearchBar
                onSearch={setSearchTerm}
                onFilterChange={setFilters}
                filters={filters}
            />

            <div className="timeline-toolbar">
                <div className="toolbar-left">
                    <h1>{showFavoritesOnly ? 'Favorites' : 'Photos'}</h1>
                    <Link to="/upload" className="btn-upload">+ Upload</Link>
                    <button onClick={handleCleanup} disabled={cleaning} style={{ fontSize: '13px' }}>
                        {cleaning ? 'Cleaning...' : '🧹 Clean Up'}
                    </button>
                </div>

                <div className="toolbar-right">
                    <div className="grid-size-selector">
                        <button className={gridSize === 'compact' ? 'active' : ''} onClick={() => { setGridSize('compact'); localStorage.setItem('gridSize', 'compact') }}>▦</button>
                        <button className={gridSize === 'comfortable' ? 'active' : ''} onClick={() => { setGridSize('comfortable'); localStorage.setItem('gridSize', 'comfortable') }}>▣</button>
                        <button className={gridSize === 'cozy' ? 'active' : ''} onClick={() => { setGridSize('cozy'); localStorage.setItem('gridSize', 'cozy') }}>▢</button>
                    </div>

                    <button className={showFavoritesOnly ? 'active' : ''} onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}>
                        ⭐ {showFavoritesOnly ? 'All' : 'Favorites'}
                    </button>

                    {!selectionMode ? (
                        <button onClick={() => setSelectionMode(true)}>Select</button>
                    ) : (
                        <>
                            <button onClick={() => setSelectedPhotos(new Set(filteredPhotos.map(p => p.photo_id)))}>Select All</button>
                            {selectedPhotos.size > 0 && (
                                <>
                                    <button onClick={handleBulkFavorite}>⭐ ({selectedPhotos.size})</button>
                                    <button onClick={handleBulkDelete} className="danger">🗑️ ({selectedPhotos.size})</button>
                                </>
                            )}
                            <button onClick={() => { setSelectionMode(false); setSelectedPhotos(new Set()) }}>Cancel</button>
                        </>
                    )}
                </div>
            </div>

            <div className="timeline-content">
                {isLoading ? (
                    <Masonry
                        breakpointCols={breakpointColumns}
                        className="masonry-grid"
                        columnClassName="masonry-column"
                    >
                        {[...Array(12)].map((_, i) => (
                            <PhotoCardSkeleton key={i} />
                        ))}
                    </Masonry>
                ) : !filteredPhotos?.length ? (
                    <div className="empty-state">
                        <h2>{showFavoritesOnly ? 'No favorites' : 'No photos yet'}</h2>
                        <Link to="/upload" className="btn-primary">Upload Now</Link>
                    </div>
                ) : (
                    <Masonry
                        breakpointCols={breakpointColumns}
                        className="masonry-grid"
                        columnClassName="masonry-column"
                    >
                        {filteredPhotos.map((photo) => (
                            <PhotoItem
                                key={photo.photo_id}
                                photo={photo}
                                selectionMode={selectionMode}
                                isSelected={selectedPhotos.has(photo.photo_id)}
                                onToggleSelection={toggleSelection}
                                onLightbox={(p) => setLightboxPhoto(p)}
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

            {/* Album Selection Modal */}
            {showAlbumModal && (
                <div className="modal-overlay" onClick={() => setShowAlbumModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Add to Album</h2>
                            <button className="modal-close" onClick={() => setShowAlbumModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            {!albums || albums.length === 0 ? (
                                <div className="empty-picker">
                                    <p>No albums found.</p>
                                    <Link to="/albums" className="btn-link">Create an album first</Link>
                                </div>
                            ) : (
                                <div className="album-picker-list">
                                    {albums.map(album => (
                                        <button
                                            key={album.album_id}
                                            className="album-picker-item"
                                            onClick={() => handleAlbumSelect(album.album_id)}
                                        >
                                            <div className="album-picker-cover">
                                                {album.cover_photo_id ? (
                                                    <img
                                                        src={`/api/v1/photos/${album.cover_photo_id}/thumbnail/200?token=${localStorage.getItem('access_token')}`}
                                                        alt={album.name}
                                                    />
                                                ) : (
                                                    <div className="album-picker-placeholder">📁</div>
                                                )}
                                            </div>
                                            <div className="album-picker-info">
                                                <span className="album-picker-name">{album.name}</span>
                                                <span className="album-picker-count">{album.photo_count} photos</span>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
