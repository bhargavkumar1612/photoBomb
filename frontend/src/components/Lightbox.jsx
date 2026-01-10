import { useState, useEffect, useRef } from 'react'
import HorizontalLoader from './HorizontalLoader'
import { X, ChevronLeft, ChevronRight, Download, Calendar, HardDrive, FileType } from 'lucide-react'
import './Lightbox.css'

export default function Lightbox({ photo, photos, onClose, onNavigate }) {
    const [currentIndex, setCurrentIndex] = useState(0)
    const [loading, setLoading] = useState(true)
    const [showControls, setShowControls] = useState(true)
    const controlsTimeoutRef = useRef(null)

    useEffect(() => {
        if (photo && photos && photos.length > 0) {
            const index = photos.findIndex(p => p.photo_id === photo.photo_id)
            if (index !== -1) {
                setCurrentIndex(index)
            }
        }
    }, [photo?.photo_id])

    // Reset loading state when photo changes
    useEffect(() => {
        setLoading(true)
    }, [currentIndex])

    // Pre-cache surrounding images (+/- 5)
    useEffect(() => {
        if (!photos || photos.length === 0) return
        const token = localStorage.getItem('access_token')
        const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'

        const preloadImage = (index) => {
            if (index >= 0 && index < photos.length) {
                const img = new Image()
                const photo = photos[index]
                img.src = photo.thumb_urls.original || `${apiBaseUrl}/photos/${photo.photo_id}/download`
            }
        }

        for (let i = 1; i <= 5; i++) {
            preloadImage(currentIndex + i)
            preloadImage(currentIndex - i)
        }
    }, [currentIndex, photos])

    // Auto-hide controls logic
    const resetControlsTimer = () => {
        setShowControls(true)
        if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current)
        controlsTimeoutRef.current = setTimeout(() => {
            setShowControls(false)
        }, 5000)
    }

    useEffect(() => {
        resetControlsTimer()
        window.addEventListener('mousemove', resetControlsTimer)
        return () => {
            window.removeEventListener('mousemove', resetControlsTimer)
            if (controlsTimeoutRef.current) clearTimeout(controlsTimeoutRef.current)
        }
    }, [])

    useEffect(() => {
        const handleKeyDown = (e) => {
            resetControlsTimer() // Show controls on interaction
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
    const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'

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
        <div className="lightbox-overlay" onClick={onClose} onMouseMove={resetControlsTimer}>
            <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>

                {/* Header Overlay */}
                <div className={`lightbox-header ${showControls ? 'visible' : ''}`}>
                    <div className="lightbox-title">
                        <h3>{currentPhoto.filename}</h3>
                        <p>{currentIndex + 1} of {photos.length}</p>
                    </div>
                    <button className="lightbox-close-btn" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                <div className="lightbox-image-container">
                    {loading && (
                        <div className="lightbox-loader">
                            <HorizontalLoader />
                        </div>
                    )}

                    {currentIndex > 0 && (
                        <button
                            className={`lightbox-nav lightbox-prev ${showControls ? 'visible' : ''}`}
                            onClick={(e) => { e.stopPropagation(); onNavigate(photos[currentIndex - 1]) }}
                        >
                            <ChevronLeft size={40} />
                        </button>
                    )}

                    <img
                        key={currentPhoto.photo_id}
                        src={currentPhoto.thumb_urls.original || `${apiBaseUrl}/photos/${currentPhoto.photo_id}/download`}
                        alt={currentPhoto.filename}
                        className={`lightbox-image ${loading ? 'loading' : 'loaded'}`}
                        onLoad={() => setLoading(false)}
                    />

                    {currentIndex < photos.length - 1 && (
                        <button
                            className={`lightbox-nav lightbox-next ${showControls ? 'visible' : ''}`}
                            onClick={(e) => { e.stopPropagation(); onNavigate(photos[currentIndex + 1]) }}
                        >
                            <ChevronRight size={40} />
                        </button>
                    )}
                </div>

                {/* Footer Metadata Overlay */}
                <div className={`lightbox-footer ${showControls ? 'visible' : ''}`}>
                    <div className="lightbox-metadata">
                        <span><Calendar size={14} /> {formatDate(currentPhoto.uploaded_at)}</span>
                        <span><HardDrive size={14} /> {formatSize(currentPhoto.size_bytes)}</span>
                        <span><FileType size={14} /> {currentPhoto.mime_type}</span>
                    </div>
                    <div className="lightbox-actions">
                        <a
                            href={currentPhoto.thumb_urls.original || `${apiBaseUrl}/photos/${currentPhoto.photo_id}/download`}
                            download={currentPhoto.filename}
                            className="lightbox-action-btn"
                            title="Download"
                        >
                            <Download size={20} />
                        </a>
                    </div>
                </div>
            </div>
        </div>
    )
}
