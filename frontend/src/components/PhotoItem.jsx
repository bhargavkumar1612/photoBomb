import { useState } from 'react'
import HorizontalLoader from './HorizontalLoader'

export default function PhotoItem({
    photo,
    selectionMode,
    isSelected,
    onToggleSelection,
    onLightbox,
    onFavorite,
    isDeleting,
    onDelete,
    onDownload,
    onInfo,
    onShare,
    onAddToAlbum
}) {
    const [imageLoaded, setImageLoaded] = useState(false)
    const token = localStorage.getItem('access_token')

    return (
        <div className={`photo-card ${isSelected ? 'selected' : ''}`}>
            {selectionMode && (
                <input
                    type="checkbox"
                    className="photo-checkbox"
                    checked={isSelected}
                    onChange={() => onToggleSelection(photo.photo_id)}
                />
            )}

            <div className="photo-mediabox" style={{ minHeight: imageLoaded ? 'auto' : '200px', position: 'relative' }}>
                {!imageLoaded && (
                    <div className="photo-loader" style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
                        <HorizontalLoader />
                    </div>
                )}

                <img
                    src={`/api/v1/photos/${photo.photo_id}/thumbnail/512?token=${token}`}
                    alt={photo.filename}
                    loading="lazy"
                    onClick={() => !selectionMode && onLightbox(photo)}
                    style={{
                        cursor: selectionMode ? 'default' : 'pointer',
                        opacity: imageLoaded ? 1 : 0,
                        transition: 'opacity 0.3s ease'
                    }}
                    onLoad={() => setImageLoaded(true)}
                    onError={(e) => {
                        e.target.src = `/api/v1/photos/${photo.photo_id}/download?token=${token}`
                        setImageLoaded(true)
                    }}
                />
            </div>

            {!selectionMode && (
                <div className="photo-overlay">
                    <button
                        className={`favorite-btn ${photo.favorite ? 'favorited' : ''}`}
                        onClick={(e) => { e.stopPropagation(); onFavorite(photo.photo_id) }}
                        title={photo.favorite ? "Remove from favorites" : "Add to favorites"}
                    >
                        {photo.favorite ? '⭐' : '☆'}
                    </button>

                    <button
                        className="delete-btn"
                        onClick={(e) => { e.stopPropagation(); onDelete(photo.photo_id, photo.filename) }}
                        disabled={isDeleting}
                        title="Delete"
                    >
                        {isDeleting ? '...' : '🗑️'}
                    </button>

                    <div className="overlay-bottom">
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onDownload(photo) }} title="Download">⬇️</button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onInfo(photo) }} title="Info">ℹ️</button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onShare(photo) }} title="Share">🔗</button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onAddToAlbum(photo) }} title="Add to album">➕</button>
                    </div>
                </div>
            )}
        </div>
    )
}
