import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import { Plus, Share2, ArrowLeft } from 'lucide-react'
import Lightbox from '../components/Lightbox'
import PhotoPickerModal from '../components/PhotoPickerModal'
import ShareModal from '../components/ShareModal'
import PhotoItem from '../components/PhotoItem'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import api from '../services/api'
import { usePhotoFilter } from '../hooks/usePhotoFilter'
import './Timeline.css' // Reuse Timeline styles for Masonry/Grid
import './AlbumDetail.css'

export default function AlbumDetail() {
    const { albumId } = useParams()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [isPickerOpen, setIsPickerOpen] = useState(false)
    const [isShareModalOpen, setIsShareModalOpen] = useState(false)
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

    const filteredPhotos = usePhotoFilter(album?.photos)

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
        // Use signed URL
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

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        1000: gridSize === 'compact' ? 3 : gridSize === 'comfortable' ? 2 : 1,
        700: 2,
        500: 1
    }

    if (isLoading) {
        return (
            <div className="timeline-container album-detail-container">
                <div className="album-detail-header shim-header" style={{ marginBottom: 40 }}>
                    {/* Minimal header skeleton */}
                    <div className="skeleton-shimmer" style={{ width: 100, height: 20, marginBottom: 20 }}></div>
                    <div className="skeleton-shimmer" style={{ width: 300, height: 40, marginBottom: 12 }}></div>
                    <div className="skeleton-shimmer" style={{ width: 100, height: 20 }}></div>
                </div>
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {[...Array(12)].map((_, i) => (
                        <PhotoCardSkeleton key={i} />
                    ))}
                </Masonry>
            </div>
        )
    }
    if (error) return <div className="error">Error loading album: {error.message}</div>
    if (!album) return <div className="error">Album not found</div>

    return (
        <div className="timeline-container album-detail-container">
            {/* Header */}
            <div className="album-detail-header">
                <button className="btn-back" onClick={() => navigate('/albums')}>
                    <ArrowLeft size={18} />
                    Back to Albums
                </button>
                <div className="album-detail-info">
                    <h1>{album.name}</h1>
                    {album.description && <p>{album.description}</p>}
                    <span className="album-detail-count">{album.photo_count} photos</span>
                </div>
                <div className="album-detail-actions">
                    <button className="btn-secondary" onClick={() => setIsShareModalOpen(true)}>
                        <Share2 size={18} style={{ marginRight: 6 }} />
                        Share
                    </button>
                    <button className="btn-primary" onClick={() => setIsPickerOpen(true)}>
                        <Plus size={18} style={{ marginRight: 6 }} />
                        Add Photos
                    </button>
                </div>
            </div>

            {/* Photos Grid */}
            {/* Only show empty state if NO photos exist in album logic AND we are not uploading */}
            {/* If we have photos but filteredPhotos is empty, user should see "No photos match filter", not "Album is empty" */}

            {(album.photos.length === 0 && uploadingCount === 0) ? (
                <div className="empty-state">
                    <h3>Album is empty</h3>
                    <p>Add photos from your timeline to see them here.</p>
                    <button className="btn-primary" onClick={() => setIsPickerOpen(true)}>Add Photos</button>
                </div>
            ) : (filteredPhotos.length === 0 && uploadingCount === 0) ? (
                <div className="empty-state">
                    <h3>No photos match your filter</h3>
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

                    {filteredPhotos.map(photo => (
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
                    photos={filteredPhotos} // Enable navigation within filtered set
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

            {/* Share Modal */}
            <ShareModal
                isOpen={isShareModalOpen}
                onClose={() => setIsShareModalOpen(false)}
                albumId={albumId}
            />
        </div>
    )
}
