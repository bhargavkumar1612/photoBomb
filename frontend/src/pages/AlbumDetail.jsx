import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import { Plus, Share2, ArrowLeft, Users, UserPlus, X } from 'lucide-react'
import Lightbox from '../components/Lightbox'
import PhotoPickerModal from '../components/PhotoPickerModal'
import ShareModal from '../components/ShareModal'
import PhotoItem from '../components/PhotoItem'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import ConfirmationModal from '../components/ConfirmationModal'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'
import { usePhotoFilter } from '../hooks/usePhotoFilter'
import './Timeline.css' // Reuse Timeline styles for Masonry/Grid
import './AlbumDetail.css'

export default function AlbumDetail() {
    const { albumId } = useParams()
    const { user } = useAuth()
    const navigate = useNavigate()
    const queryClient = useQueryClient()
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [isPickerOpen, setIsPickerOpen] = useState(false)
    const [isShareModalOpen, setIsShareModalOpen] = useState(false)
    const [isContributorModalOpen, setIsContributorModalOpen] = useState(false)
    const [contributorEmail, setContributorEmail] = useState('')
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

    // Add Contributor Mutation
    const addContributorMutation = useMutation({
        mutationFn: async (email) => {
            const res = await api.post(`/albums/${albumId}/contributors`, { email })
            return res.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['album', albumId] })
            setContributorEmail('')
            setIsContributorModalOpen(false)
        },
        onError: (error) => {
            alert(error.response?.data?.detail || 'Failed to add contributor')
        }
    })


    const [photoToRemove, setPhotoToRemove] = useState(null)
    const [sharePhotoIds, setSharePhotoIds] = useState(null)

    const handleRemoveFromAlbum = (photoId) => {
        setPhotoToRemove(photoId)
    }

    const confirmRemove = () => {
        if (photoToRemove) {
            removeMutation.mutate(photoToRemove)
            setPhotoToRemove(null)
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

    const handleShare = (photo) => {
        setSharePhotoIds([photo.photo_id])
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
                <button className="btn-back" onClick={() => navigate(album.is_owner ? '/albums' : '/sharing')}>
                    <ArrowLeft size={18} />
                    {album.is_owner ? 'Back to Albums' : 'Back to Sharing'}
                </button>
                <div className="album-detail-info">
                    <h1>{album.name}</h1>
                    {album.description && <p>{album.description}</p>}
                    <div className="album-meta-row">
                        <span className="album-detail-count">{album.photo_count} photos</span>
                        {album.contributors && album.contributors.length > 0 && (
                            <div className="album-contributors-badge" title="Contributors">
                                <Users size={14} className="icon-contributors" />
                                <div className="contributors-avatars">
                                    {album.contributors.slice(0, 3).map(c => (
                                        <div key={c.user_id} className="mini-avatar" title={c.full_name}>
                                            {c.full_name.charAt(0)}
                                        </div>
                                    ))}
                                    {album.contributors.length > 3 && (
                                        <div className="mini-avatar more">+{album.contributors.length - 3}</div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
                <div className="album-detail-actions">
                    {album.is_owner && (
                        <>
                            <button className="btn-secondary" onClick={() => setIsShareModalOpen(true)}>
                                <Share2 size={18} style={{ marginRight: 6 }} />
                                Share
                            </button>
                            <button className="btn-secondary" onClick={() => setIsContributorModalOpen(true)}>
                                <UserPlus size={18} style={{ marginRight: 6 }} />
                                Manage Contributors
                            </button>
                        </>
                    )}
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
                            onDelete={(album.is_owner || (user && photo.owner && photo.owner.user_id === user.id)) ? (id) => handleRemoveFromAlbum(id) : undefined}
                            isRemoveAction={true}
                            onDownload={handleDownload}
                            onInfo={() => alert(`File: ${photo.filename}`)}
                            onShare={handleShare}
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
                isOpen={isShareModalOpen || !!sharePhotoIds}
                onClose={() => { setIsShareModalOpen(false); setSharePhotoIds(null); }}
                albumId={sharePhotoIds ? null : albumId}
                photoIds={sharePhotoIds || []}
            />

            {/* Contributor Management Modal */}
            {isContributorModalOpen && (
                <div className="modal-overlay" onClick={() => setIsContributorModalOpen(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
                        <div className="modal-header">
                            <h2>Manage Contributors</h2>
                            <button className="btn-close" onClick={() => setIsContributorModalOpen(false)}>
                                <X size={20} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <form
                                onSubmit={(e) => {
                                    e.preventDefault()
                                    if (contributorEmail) addContributorMutation.mutate(contributorEmail)
                                }}
                                style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}
                            >
                                <input
                                    type="email"
                                    placeholder="Enter user email"
                                    value={contributorEmail}
                                    onChange={e => setContributorEmail(e.target.value)}
                                    required
                                    style={{
                                        flex: 1,
                                        padding: '10px 14px',
                                        border: '1px solid #d1d5db',
                                        borderRadius: '8px',
                                        fontSize: '14px',
                                        outline: 'none'
                                    }}
                                />
                                <button
                                    type="submit"
                                    className="btn-primary"
                                    disabled={addContributorMutation.isPending}
                                    style={{ whiteSpace: 'nowrap' }}
                                >
                                    <UserPlus size={16} style={{ marginRight: 6 }} />
                                    {addContributorMutation.isPending ? 'Adding...' : 'Invite'}
                                </button>
                            </form>

                            <div>
                                <h3 style={{ fontSize: '14px', color: '#6b7280', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    Contributors ({album?.contributors?.length || 0})
                                </h3>
                                {!album?.contributors || album.contributors.length === 0 ? (
                                    <p style={{ textAlign: 'center', color: '#9ca3af', padding: '20px 0' }}>
                                        No contributors yet.
                                    </p>
                                ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                        {album.contributors.map(c => (
                                            <div
                                                key={c.user_id}
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '12px',
                                                    padding: '12px',
                                                    background: '#f9fafb',
                                                    border: '1px solid #e5e7eb',
                                                    borderRadius: '8px'
                                                }}
                                            >
                                                <div style={{
                                                    width: '40px',
                                                    height: '40px',
                                                    borderRadius: '50%',
                                                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                    color: 'white',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    fontWeight: 700,
                                                    fontSize: '16px'
                                                }}>
                                                    {c.full_name.charAt(0)}
                                                </div>
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ fontSize: '14px', fontWeight: 600, color: '#111827' }}>
                                                        {c.full_name}
                                                    </div>
                                                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                                                        {c.email}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Confirmation Modal */}
            <ConfirmationModal
                isOpen={!!photoToRemove}
                onClose={() => setPhotoToRemove(null)}
                onConfirm={confirmRemove}
                title="Remove from Album"
                message="Are you sure you want to remove this photo from the album? It will remain in your library."
                confirmText="Remove"
                cancelText="Keep"
                isDestructive={false}
            />
        </div>
    )
}
