import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import api from '../services/api'
import './Timeline.css' // Reuse Timeline styles

export default function AlbumDetail() {
    const { albumId } = useParams()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [gridSize, setGridSize] = useState(localStorage.getItem('gridSize') || 'comfortable')

    // Fetch album details
    const { data: album, isLoading, error } = useQuery({
        queryKey: ['album', albumId],
        queryFn: async () => {
            const response = await api.get(`/albums/${albumId}`)
            return response.data
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
                    {/* Could add Edit Album / Delete Album buttons here */}
                </div>
            </div>

            {/* Photos Grid */}
            {!album.photos || album.photos.length === 0 ? (
                <div className="empty-state">
                    <h3>Album is empty</h3>
                    <p>Add photos from your timeline to see them here.</p>
                    <button className="btn-primary" onClick={() => navigate('/')}>Go to Timeline</button>
                </div>
            ) : (
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {album.photos.map(photo => (
                        <div key={photo.photo_id} className="photo-card">
                            <img
                                src={`/api/v1/photos/${photo.photo_id}/thumbnail/512?token=${localStorage.getItem('access_token')}`}
                                alt={photo.filename}
                                loading="lazy"
                                onClick={() => setLightboxPhoto(photo)}
                                onError={(e) => { e.target.src = `/api/v1/photos/${photo.photo_id}/download?token=${localStorage.getItem('access_token')}` }}
                            />
                            <div className="photo-overlay">
                                <button
                                    className="delete-btn"
                                    onClick={(e) => { e.stopPropagation(); handleRemoveFromAlbum(photo.photo_id) }}
                                    title="Remove from album"
                                >
                                    ✕
                                </button>
                                <div className="overlay-bottom">
                                    <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); handleDownload(photo) }}>⬇️</button>
                                </div>
                            </div>
                        </div>
                    ))}
                </Masonry>
            )}

            {/* Lightbox */}
            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    onClose={() => setLightboxPhoto(null)}
                />
            )}
        </div>
    )
}
