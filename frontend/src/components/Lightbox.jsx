import { useState, useEffect } from 'react'
import HorizontalLoader from './HorizontalLoader'
import './Lightbox.css'

export default function Lightbox({ photo, photos, onClose, onNavigate }) {
    const [currentIndex, setCurrentIndex] = useState(0)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (photo && photos && photos.length > 0) {
            const index = photos.findIndex(p => p.photo_id === photo.photo_id)
            if (index !== -1) {
                setCurrentIndex(index)
            }
        }
    }, [photo?.photo_id])

    useEffect(() => {
        setLoading(true)
    }, [currentIndex])

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                onClose()
            } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
                onNavigate(photos[currentIndex - 1])
            } else if (e.key === 'ArrowRight' && currentIndex < photos.length - 1) {
                onNavigate(photos[currentIndex + 1])
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [currentIndex, photos, onClose, onNavigate])

    if (!photo || !photos || photos.length === 0) return null

    const currentPhoto = photos[currentIndex]

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const formatSize = (bytes) => {
        if (!bytes) return '0 B'
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    return (
        <div className="lightbox-overlay" onClick={onClose}>
            <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
                <div className="lightbox-header">
                    <div className="lightbox-title">
                        <h3>{currentPhoto.filename}</h3>
                        <p>{currentIndex + 1} of {photos.length}</p>
                    </div>
                    <button className="lightbox-close" onClick={onClose}>×</button>
                </div>

                <div className="lightbox-image-container">
                    {loading && (
                        <div className="lightbox-loader">
                            <HorizontalLoader />
                        </div>
                    )}

                    {currentIndex > 0 && (
                        <button className="lightbox-nav lightbox-prev" onClick={() => onNavigate(photos[currentIndex - 1])}>
                            ←
                        </button>
                    )}

                    <img
                        src={`/api/v1/photos/${currentPhoto.photo_id}/download?token=${localStorage.getItem('access_token')}`}
                        alt={currentPhoto.filename}
                        className={`lightbox-image ${loading ? 'hidden' : ''}`}
                        onLoad={() => setLoading(false)}
                    />

                    {currentIndex < photos.length - 1 && (
                        <button className="lightbox-nav lightbox-next" onClick={() => onNavigate(photos[currentIndex + 1])}>
                            →
                        </button>
                    )}
                </div>

                <div className="lightbox-footer">
                    <div className="lightbox-metadata">
                        <span>📅 {formatDate(currentPhoto.uploaded_at)}</span>
                        <span>📏 {formatSize(currentPhoto.size_bytes)}</span>
                        <span>📄 {currentPhoto.mime_type}</span>
                    </div>
                    <div className="lightbox-actions">
                        <a
                            href={`/api/v1/photos/${currentPhoto.photo_id}/download?token=${localStorage.getItem('access_token')}`}
                            download={currentPhoto.filename}
                            className="lightbox-btn"
                        >
                            ⬇️ Download
                        </a>
                    </div>
                </div>
            </div>
        </div>
    )
}
