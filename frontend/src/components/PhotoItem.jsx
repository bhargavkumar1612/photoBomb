import { useState } from 'react'
import HorizontalLoader from './HorizontalLoader'
import { Heart, Trash2, Download, Info, Share2, FolderPlus, Loader2 } from 'lucide-react'

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
    onAddToAlbum,
    readonly = false
}) {
    const [imageLoaded, setImageLoaded] = useState(false)
    const [hasError, setHasError] = useState(false)
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

            {!selectionMode && photo.tags && photo.tags.length > 0 && (
                <div className="visual-hashtags">
                    {photo.tags.slice(0, 3).map(tag => (
                        <div key={tag} className="visual-hashtag">#{tag}</div>
                    ))}
                    {photo.tags.length > 3 && (
                        <div className="visual-hashtag">+{photo.tags.length - 3}</div>
                    )}
                </div>
            )}

            <div className="photo-mediabox" style={{ minHeight: imageLoaded ? 'auto' : '200px', position: 'relative' }}>
                {!imageLoaded && !hasError && (
                    <div className="photo-loader" style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
                        <HorizontalLoader />
                    </div>
                )}

                {hasError ? (
                    <div
                        className="photo-error-placeholder"
                        style={{
                            width: '100%',
                            height: '100%',
                            minHeight: '200px',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: '#f3f4f6',
                            color: '#6b7280',
                            borderRadius: '8px',
                            textAlign: 'center',
                            padding: '1rem'
                        }}
                    >
                        <Info size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
                        <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Image Migrating</span>
                        <span style={{ fontSize: '0.75rem', opacity: 0.75 }}>Check back later</span>
                    </div>
                ) : (
                    <img
                        src={photo.thumb_urls.thumb_512}
                        alt={photo.filename}
                        loading="lazy"
                        onClick={() => !selectionMode && onLightbox(photo)}
                        style={{
                            cursor: selectionMode ? 'default' : 'pointer',
                            opacity: imageLoaded ? 1 : 0,
                            transition: 'opacity 0.3s ease',
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover'
                        }}
                        onLoad={() => setImageLoaded(true)}
                        onError={(e) => {
                            // Try original if thumbnail fails, but prevent infinite loop if original also fails
                            if (e.target.src !== photo.thumb_urls.original && photo.thumb_urls.original) {
                                e.target.src = photo.thumb_urls.original
                            } else {
                                setHasError(true)
                                setImageLoaded(true)
                            }
                        }}
                    />
                )}
            </div>

            {!selectionMode && (
                <div className="photo-overlay">
                    {!readonly && (
                        <>
                            <button
                                className={`favorite-btn ${photo.favorite ? 'favorited' : ''}`}
                                onClick={(e) => { e.stopPropagation(); onFavorite(photo.photo_id) }}
                                title={photo.favorite ? "Remove from favorites" : "Add to favorites"}
                            >
                                <Heart size={20} fill={photo.favorite ? "currentColor" : "none"} strokeWidth={2} />
                            </button>

                            {onDelete && (
                                <button
                                    className="delete-btn"
                                    onClick={(e) => { e.stopPropagation(); onDelete(photo.photo_id, photo.filename) }}
                                    disabled={isDeleting}
                                    title="Delete"
                                >
                                    {isDeleting ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={20} />}
                                </button>
                            )}
                        </>
                    )}

                    <div className="overlay-bottom">
                        {photo.owner && (
                            <div className="photo-owner-badge" title={`Uploaded by ${photo.owner.name}`} style={{ marginRight: 'auto', background: 'rgba(0,0,0,0.4)', color: 'white', padding: '4px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>
                                {photo.owner.name}
                            </div>
                        )}
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onDownload(photo) }} title="Download">
                            <Download size={18} />
                        </button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onInfo(photo) }} title="Info">
                            <Info size={18} />
                        </button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onShare(photo) }} title="Share">
                            <Share2 size={18} />
                        </button>
                        <button className="overlay-btn" onClick={(e) => { e.stopPropagation(); onAddToAlbum(photo) }} title="Add to album">
                            <FolderPlus size={18} />
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
