import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import { Plus } from 'lucide-react'
import Lightbox from '../components/Lightbox'
import PhotoPickerModal from '../components/PhotoPickerModal'
import PhotoItem from '../components/PhotoItem'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import api from '../services/api'
import './Timeline.css' // Reuse Timeline styles

export default function AlbumDetail() {
    const { albumId } = useParams()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [isPickerOpen, setIsPickerOpen] = useState(false)
    const [uploadingCount, setUploadingCount] = useState(0)
    const [gridSize, setGridSize] = useState(localStorage.getItem('gridSize') || 'comfortable')

    // Fetch album details
    const { data: album, isLoading, error } = useQuery({
        queryKey: ['album', albumId],
        queryFn: async () => {
            const response = await api.get(`/albums/${albumId}`)
            return response.data
        }
    })

    // Add photos to album mutation
    const addPhotosMutation = useMutation({
        mutationFn: async (photoIds) => {
            await api.post(`/albums/${albumId}/photos`, photoIds)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['album', albumId] })
            queryClient.invalidateQueries({ queryKey: ['albums'] }) // to update cover/counts
            setIsPickerOpen(false)
            setUploadingCount(0)
        },
        onError: (err) => {
            alert('Failed to add photos: ' + err.message)
            setUploadingCount(0)
        }
    })

    // Remove photo from album mutation
    const removeMutation = useMutation({
        mutationFn: async (photoId) => {
            await api.delete(`/albums/${albumId}/photos/${photoId}`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['album', albumId] })
        }
    })

    // Update album mutation
    const updateMutation = useMutation({
        mutationFn: async (data) => {
            await api.patch(`/albums/${albumId}`, data)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['album', albumId] })
            queryClient.invalidateQueries({ queryKey: ['albums'] }) // Refresh list too
        }
    })

    const handleRemoveFromAlbum = (photoId) => {
        if (window.confirm('Remove photo from album?')) {
            removeMutation.mutate(photoId)
        }
    }

    const handleAddPhotos = (photoIds) => {
        setUploadingCount(photoIds.length)
        addPhotosMutation.mutate(photoIds)
    }

    const handleDownload = (photo) => {
        const url = `/api/v1/photos/${photo.photo_id}/download?token=${localStorage.getItem('access_token')}`
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        1000: gridSize === 'compact' ? 3 : gridSize === 'comfortable' ? 2 : 1,
        700: 2,
        500: 1
    }

    if (isLoading) return <div className="loading">Loading album...</div>
    if (error) return <div className="error">Error loading album: {error.message}</div>
    if (!album) return <div className="error">Album not found</div>

    return (
        <div className="timeline-container">
            {/* Header */}
            <div className="album-detail-header">
                <button className="btn-back" onClick={() => navigate('/albums')}>
                    ← Back to Albums
                </button>
                <div className="album-detail-info">
                    <h1>{album.name}</h1>
                    {album.description && <p>{album.description}</p>}
                    <span className="album-detail-count">{album.photo_count} photos</span>
                </div>
                <div className="album-detail-actions">
                    <button className="btn-primary" onClick={() => setIsPickerOpen(true)}>
                        <Plus size={18} style={{ marginRight: 6 }} />
                        Add Photos
                    </button>
                </div>
            </div>

            {/* Photos Grid */}
            {(!album.photos || album.photos.length === 0) && uploadingCount === 0 ? (
                <div className="empty-state">
                    <h3>Album is empty</h3>
                    <p>Add photos from your timeline to see them here.</p>
                    <button className="btn-primary" onClick={() => setIsPickerOpen(true)}>Add Photos</button>
                </div>
            ) : (
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {/* Show skeletons while uploading */}
                    {[...Array(uploadingCount)].map((_, i) => (
                        <PhotoCardSkeleton key={`skeleton-${i}`} />
                    ))}

                    {album.photos && album.photos.map(photo => (
                        <PhotoItem
                            key={photo.photo_id}
                            photo={photo}
                            selectionMode={false} // No selection mode in album view yet
                            isSelected={false}
                            onToggleSelection={() => { }}
                            onLightbox={setLightboxPhoto}
                            onFavorite={() => { }} // TODO: Add favorite mutation if needed, or pass empty
                            isDeleting={false}
                            onDelete={(id) => handleRemoveFromAlbum(id)}
                            onDownload={handleDownload}
                            onInfo={() => alert(`File: ${photo.filename}`)}
                            onShare={() => { }}
                            onAddToAlbum={() => { }} // Disable or implement later
                        />
                    ))}
                </Masonry>
            )}

            {/* Lightbox */}
            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    photos={album.photos} // Enable navigation
                    onClose={() => setLightboxPhoto(null)}
                    onNavigate={setLightboxPhoto}
                />
            )}

            {/* Photo Picker Modal */}
            <PhotoPickerModal
                isOpen={isPickerOpen}
                onClose={() => setIsPickerOpen(false)}
                onAdd={handleAddPhotos}
                existingPhotoIds={album.photos ? album.photos.map(p => p.photo_id) : []}
            />
        </div>
    )
}
