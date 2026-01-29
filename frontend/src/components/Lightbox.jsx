import { useState, useEffect, useRef } from 'react'
import HorizontalLoader from './HorizontalLoader'
import { X, ChevronLeft, ChevronRight, Download, Calendar, HardDrive, FileType, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch'
import './Lightbox.css'

export default function Lightbox({ photo, photos, onClose, onNavigate }) {
    const [currentIndex, setCurrentIndex] = useState(0)
    const [loading, setLoading] = useState(true)
    const [hasError, setHasError] = useState(false)
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

    // Reset loading/error state when photo changes
    useEffect(() => {
        setLoading(true)
        setHasError(false)
    }, [currentIndex])

    // Pre-cache surrounding images (+/- 5)
    // Pre-cache surrounding images (+/- 5) sequentially to avoid network stress
    useEffect(() => {
        if (!photos || photos.length === 0) return
        const apiBaseUrl = import.meta.env.VITE_API_URL || '/api/v1'
        let isCancelled = false

        // Create a prioritization queue: immediate neighbors first, then further out
        const queue = []
        for (let i = 1; i <= 5; i++) {
            if (currentIndex + i < photos.length) queue.push(currentIndex + i)
            if (currentIndex - i >= 0) queue.push(currentIndex - i)
        }

        const processQueue = async () => {
            if (isCancelled || queue.length === 0) return

            const index = queue.shift()
            const photo = photos[index]
            const src = photo.thumb_urls.original || `${apiBaseUrl}/photos/${photo.photo_id}/download`

            // Load one image
            await new Promise((resolve) => {
                const img = new Image()
                img.onload = resolve
                img.onerror = resolve // Continue even if error
                img.src = src

                // Safety timeout to prevent stalling the queue
                setTimeout(resolve, 2000)
            })

            // Proceed to next if not cancelled
            if (!isCancelled) {
                processQueue()
            }
        }

        processQueue()

        return () => {
            isCancelled = true
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

                <TransformWrapper
                    initialScale={1}
                    minScale={0.5}
                    maxScale={8}
                    centerZoomedOut={true}
                    limitToBounds={true}
                    wheel={{ step: 0.5 }}
                    pinch={{ step: 5 }}
                    doubleClick={{ mode: 'reset' }}
                    key={currentPhoto.photo_id} // Force reset on photo change
                    onPanning={resetControlsTimer}
                    onZooming={resetControlsTimer}
                    onPinching={resetControlsTimer}
                    onWheel={resetControlsTimer}
                >
                    {({ zoomIn, zoomOut, resetTransform }) => (
                        <>
                            {/* Header Overlay */}
                            <div className={`lightbox-header ${showControls ? 'visible' : ''}`}>
                                <div className="lightbox-title">
                                    <h3>{currentPhoto.filename}</h3>
                                    <p>{currentIndex + 1} of {photos.length}</p>
                                </div>
                                <div className="lightbox-controls-group">
                                    <button className="lightbox-control-btn" onClick={() => zoomIn()}>
                                        <ZoomIn size={20} />
                                    </button>
                                    <button className="lightbox-control-btn" onClick={() => zoomOut()}>
                                        <ZoomOut size={20} />
                                    </button>
                                    <button className="lightbox-control-btn" onClick={() => resetTransform()}>
                                        <RotateCcw size={20} />
                                    </button>
                                    <div className="lightbox-divider"></div>
                                    <button className="lightbox-close-btn" onClick={onClose}>
                                        <X size={24} />
                                    </button>
                                </div>
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

                                <TransformComponent
                                    wrapperClass="lightbox-transform-wrapper"
                                    contentClass="lightbox-transform-content"
                                >
                                    {hasError ? (
                                        <div className="lightbox-error-placeholder" style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            opacity: 0.8
                                        }}>
                                            <Info size={48} style={{ marginBottom: '16px' }} />
                                            <h3 style={{ margin: 0, marginBottom: '8px' }}>Image Unavailable</h3>
                                            <p style={{ margin: 0, opacity: 0.7 }}>Migration in progress or file missing</p>
                                        </div>
                                    ) : (
                                        <img
                                            src={currentPhoto.thumb_urls.original || `${apiBaseUrl}/photos/${currentPhoto.photo_id}/download`}
                                            alt={currentPhoto.filename}
                                            className={`lightbox-image ${loading ? 'loading' : 'loaded'}`}
                                            onLoad={() => setLoading(false)}
                                            onError={() => {
                                                setLoading(false)
                                                setHasError(true)
                                            }}
                                        />
                                    )}
                                </TransformComponent>

                                {currentIndex < photos.length - 1 && (
                                    <button
                                        className={`lightbox-nav lightbox-next ${showControls ? 'visible' : ''}`}
                                        onClick={(e) => { e.stopPropagation(); onNavigate(photos[currentIndex + 1]) }}
                                    >
                                        <ChevronRight size={40} />
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </TransformWrapper>

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
