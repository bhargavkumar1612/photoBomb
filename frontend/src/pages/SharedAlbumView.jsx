import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import PhotoItem from '../components/PhotoItem'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import api from '../services/api'
import './Timeline.css'
import './AlbumDetail.css'

export default function SharedAlbumView() {
    const { token } = useParams()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [gridSize, setGridSize] = useState(localStorage.getItem('gridSize') || 'comfortable')

    // Fetch shared album data
    const { data: album, isLoading, error } = useQuery({
        queryKey: ['sharedAlbum', token],
        queryFn: async () => {
            const response = await api.get(`/shared/${token}`)
            return response.data
        }
    })

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        1000: gridSize === 'compact' ? 3 : gridSize === 'comfortable' ? 2 : 1,
        700: 2,
        500: 1
    }

    const handleDownload = (photo) => {
        // Shared view uses the signed URL provided in response
        const url = photo.thumb_urls.original
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        link.target = "_blank"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    if (isLoading) {
        return (
            <div className="timeline-container album-detail-container">
                <div className="album-detail-header shim-header" style={{ marginBottom: 40 }}>
                    <div className="skeleton-shimmer" style={{ width: 300, height: 40, marginBottom: 12 }}></div>
                    <div className="skeleton-shimmer" style={{ width: 150, height: 20 }}></div>
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

    if (error) return (
        <div className="error-container" style={{ padding: 40, textAlign: 'center' }}>
            <h2>Unable to load album</h2>
            <p className="error-message">{error.response?.data?.detail || error.message}</p>
        </div>
    )

    return (
        <div className="timeline-container album-detail-container">
            {/* Header */}
            <div className="album-detail-header">
                <div className="album-detail-info">
                    <h1>{album.album_name}</h1>
                    <p style={{ color: '#6b7280', fontSize: '14px' }}>Shared by {album.owner_name}</p>
                    {album.album_description && <p>{album.album_description}</p>}
                    <span className="album-detail-count">{album.photos.length} photos</span>
                </div>
            </div>

            {/* Photos Grid */}
            <Masonry
                breakpointCols={breakpointColumns}
                className="my-masonry-grid"
                columnClassName="my-masonry-grid_column"
            >
                {album.photos.map(photo => (
                    <PhotoItem
                        key={photo.photo_id}
                        photo={photo}
                        selectionMode={false}
                        isSelected={false}
                        onToggleSelection={() => { }}
                        onLightbox={setLightboxPhoto}
                        onFavorite={() => { }} // Disabled in readonly
                        isDeleting={false}
                        onDelete={() => { }} // Disabled in readonly
                        onDownload={handleDownload}
                        onInfo={() => alert(`File: ${photo.filename}\nType: Shared`)}
                        onShare={() => { }}
                        onAddToAlbum={() => { }}
                        readonly={true}
                    />
                ))}
            </Masonry>

            {/* Lightbox */}
            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    photos={album.photos}
                    onClose={() => setLightboxPhoto(null)}
                    onNavigate={setLightboxPhoto}
                    isSharedView={true}
                />
            )}
        </div>
    )
}
