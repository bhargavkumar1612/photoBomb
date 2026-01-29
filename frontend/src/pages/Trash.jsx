import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Masonry from 'react-masonry-css'
import { RefreshCw, Trash2, AlertTriangle, CheckSquare } from 'lucide-react'
import api from '../services/api'
import PhotoCardSkeleton from '../components/skeletons/PhotoCardSkeleton'
import './Timeline.css' // Reuse general grid styles
import './Trash.css'

export default function Trash() {
    const queryClient = useQueryClient()
    const [actionLoading, setActionLoading] = useState(null) // photo_id of item being processed
    const [selectedPhotos, setSelectedPhotos] = useState(new Set())
    const [selectionMode, setSelectionMode] = useState(false)

    // Fetch trash items
    const { data: trashData, isLoading, error } = useQuery({
        queryKey: ['trash'],
        queryFn: async () => {
            const response = await api.get('/photos/trash/list')
            return response.data
        }
    })

    // Restore mutation
    const restoreMutation = useMutation({
        mutationFn: async (photoId) => {
            setActionLoading(photoId)
            await api.post(`/photos/${photoId}/restore`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trash'] })
            queryClient.invalidateQueries({ queryKey: ['photos'] })
            setActionLoading(null)
        },
        onError: () => setActionLoading(null)
    })

    // Permanent delete mutation
    const deletePermanentMutation = useMutation({
        mutationFn: async (photoId) => {
            setActionLoading(photoId)
            await api.delete(`/photos/${photoId}/permanent`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trash'] })
            queryClient.invalidateQueries({ queryKey: ['user-info'] })
            setActionLoading(null)
        },
        onError: () => setActionLoading(null)
    })

    const handleRestore = (photoId) => {
        restoreMutation.mutate(photoId)
    }

    const handleDeletePermanent = (photoId) => {
        if (window.confirm('Are you sure you want to permanently delete this photo? This cannot be undone.')) {
            deletePermanentMutation.mutate(photoId)
        }
    }

    const toggleSelection = (photoId) => {
        const newSelection = new Set(selectedPhotos)
        if (newSelection.has(photoId)) {
            newSelection.delete(photoId)
        } else {
            newSelection.add(photoId)
        }
        setSelectedPhotos(newSelection)
    }

    const handleBulkRestore = async () => {
        if (!window.confirm(`Restore ${selectedPhotos.size} photos?`)) return
        try {
            await api.post('/photos/batch/restore', { photo_ids: Array.from(selectedPhotos) })
            queryClient.invalidateQueries({ queryKey: ['trash'] })
            queryClient.invalidateQueries({ queryKey: ['photos'] })
            setSelectedPhotos(new Set())
            setSelectionMode(false)
        } catch (e) {
            alert(`Failed to restore: ${e.message}`)
        }
    }

    const handleBulkDeletePermanent = async () => {
        if (!window.confirm(`Permanently delete ${selectedPhotos.size} photos? This cannot be undone.`)) return
        try {
            await api.post('/photos/batch/permanent', { photo_ids: Array.from(selectedPhotos) })
            queryClient.invalidateQueries({ queryKey: ['trash'] })
            queryClient.invalidateQueries({ queryKey: ['user-info'] })
            setSelectedPhotos(new Set())
            setSelectionMode(false)
        } catch (e) {
            alert(`Failed to delete: ${e.message}`)
        }
    }

    const breakpointColumns = {
        default: 4,
        1400: 3,
        1000: 2,
        700: 2,
        500: 1
    }

    if (error) return <div className="error">Error loading trash: {error.message}</div>

    return (
        <div className="timeline-container">
            <header className="trash-header">
                <div className="trash-title">
                    <h1>Trash</h1>
                    <span className="trash-badge">{trashData?.photos?.length || 0} items</span>
                </div>

                <div className="trash-actions-bar">
                    <button
                        className={`btn-icon-round ${selectionMode ? 'active' : ''}`}
                        onClick={() => {
                            if (selectionMode) {
                                setSelectionMode(false)
                                setSelectedPhotos(new Set())
                            } else {
                                setSelectionMode(true)
                            }
                        }}
                        title={selectionMode ? 'Cancel Selection' : 'Select Photos'}
                    >
                        <CheckSquare size={18} />
                    </button>

                    {selectionMode && (
                        <button
                            className="btn-secondary small"
                            style={{ marginRight: '8px' }}
                            onClick={() => {
                                if (selectedPhotos.size === trashData?.photos?.length) {
                                    setSelectedPhotos(new Set())
                                } else {
                                    const allIds = trashData?.photos?.map(p => p.photo_id) || []
                                    setSelectedPhotos(new Set(allIds))
                                }
                            }}
                        >
                            {selectedPhotos.size === trashData?.photos?.length ? 'Deselect All' : 'Select All'}
                        </button>
                    )}

                    {selectionMode && selectedPhotos.size > 0 && (
                        <div className="bulk-actions">
                            <span className="selection-count">{selectedPhotos.size} selected</span>
                            <button className="btn-secondary" onClick={handleBulkRestore}>
                                <RefreshCw size={14} /> Restore
                            </button>
                            <button className="btn-secondary danger" onClick={handleBulkDeletePermanent}>
                                <Trash2 size={14} /> Delete Forever
                            </button>
                        </div>
                    )}
                </div>

                {!selectionMode && (
                    <div className="trash-info">
                        <AlertTriangle size={16} />
                        <span>Items in trash are automatically deleted after 30 days.</span>
                    </div>
                )}
            </header>

            {isLoading ? (
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {[...Array(8)].map((_, i) => (
                        <PhotoCardSkeleton key={i} />
                    ))}
                </Masonry>
            ) : !trashData || trashData.photos.length === 0 ? (
                <div className="empty-state">
                    <Trash2 size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
                    <h3>Trash is empty</h3>
                    <p>Deleted photos will appear here.</p>
                </div>
            ) : (
                <Masonry
                    breakpointCols={breakpointColumns}
                    className="my-masonry-grid"
                    columnClassName="my-masonry-grid_column"
                >
                    {trashData.photos.map(photo => (
                        <div
                            key={photo.photo_id}
                            className={`photo-card trash-card ${selectedPhotos.has(photo.photo_id) ? 'selected' : ''}`}
                            onClick={() => selectionMode && toggleSelection(photo.photo_id)}
                        >
                            <div className="photo-wrapper">
                                <img
                                    src={photo.thumb_urls.thumb_512}
                                    alt={photo.filename}
                                    className="photo-img"
                                    loading="lazy"
                                />
                                {selectionMode && (
                                    <div className={`selection-overlay ${selectedPhotos.has(photo.photo_id) ? 'selected' : ''}`}>
                                        <CheckSquare size={24} color={selectedPhotos.has(photo.photo_id) ? "#3b82f6" : "white"} />
                                    </div>
                                )}

                                {actionLoading === photo.photo_id && (
                                    <div className="loading-overlay">
                                        <div className="spinner"></div>
                                    </div>
                                )}

                                {!selectionMode && (
                                    <div className="trash-actions">
                                        <button
                                            className="btn-trash-action restore"
                                            onClick={(e) => { e.stopPropagation(); handleRestore(photo.photo_id); }}
                                            title="Restore"
                                            disabled={actionLoading === photo.photo_id}
                                        >
                                            <RefreshCw size={16} />
                                        </button>
                                        <button
                                            className="btn-trash-action delete-forever"
                                            onClick={(e) => { e.stopPropagation(); handleDeletePermanent(photo.photo_id); }}
                                            title="Delete Permanently"
                                            disabled={actionLoading === photo.photo_id}
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </Masonry>
            )}
        </div>
    )
}
