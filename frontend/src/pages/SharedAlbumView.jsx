import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import { Download } from 'lucide-react'
import Lightbox from '../components/Lightbox'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import api from '../services/api'
import './Timeline.css'
import './SharedAlbumView.css'

export default function SharedAlbumView() {
    const { token } = useParams()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [gridSize, setGridSize] = useState('comfortable')

    // Fetch shared album data
    const { data: album, isLoading, error } = useQuery({
        queryKey: ['sharedAlbum', token],
        queryFn: async () => {
            // Note: Public endpoint
            const response = await api.get(`/shared/${token}`)
            return response.data
        }
    })

    const breakpointColumns = {
        default: gridSize === 'compact' ? 5 : gridSize === 'comfortable' ? 4 : 3,
        1400: gridSize === 'compact' ? 4 : gridSize === 'comfortable' ? 3 : 2,
        900: gridSize === 'compact' ? 3 : 2,
        600: 2
    }

    const handleDownload = (photo) => {
        const url = photo.thumb_urls.original
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        link.target = "_blank"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    if (isLoading) return (
        <div className="shared-view-loading">
            <div className="loader"></div>
            <p>Loading shared album...</p>
        </div>
    )

    if (error) return (
        <div className="shared-view-error">
            <h2>Unable to load album</h2>
            <p>{error.response?.data?.detail || error.message}</p>
        </div>
    )

    return (
        <div className="shared-album-container">
            <header className="shared-header">
                <div className="shared-header-content">
                    <div>
                        <h1>{album.album_name}</h1>
                        <p className="shared-by">Shared by {album.owner_name}</p>
                        {album.album_description && <p className="shared-desc">{album.album_description}</p>}
                    </div>
                </div>
            </header>

            <div className="shared-content">
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {album.photos.map(photo => (
                        <div key={photo.photo_id} className="photo-item shared-photo-item">
                            <div className="photo-wrapper" onClick={() => setLightboxPhoto(photo)}>
                                <img
                                    src={photo.thumb_urls.medium || photo.thumb_urls.original}
                                    alt={photo.filename}
                                    loading="lazy"
                                />
                                <div className="photo-overlay">
                                    <div className="overlay-top">
                                        {/* No selection in shared view */}
                                    </div>
                                    <div className="overlay-bottom">
                                        <button
                                            className="action-btn"
                                            onClick={(e) => { e.stopPropagation(); handleDownload(photo) }}
                                            title="Download"
                                        >
                                            <Download size={18} />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </Masonry>
            </div>

            {/* Lightbox for Shared View - Pass only necessary props/actions */}
            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    photos={album.photos}
                    onClose={() => setLightboxPhoto(null)}
                    onNavigate={setLightboxPhoto}
                    isSharedView={true} // Hint to lightbox to hide edit/delete actions
                />
            )}
        </div>
    )
}
