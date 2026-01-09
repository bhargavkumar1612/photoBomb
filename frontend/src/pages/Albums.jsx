import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import AlbumCardSkeleton from '../components/skeletons/AlbumCardSkeleton'
import api from '../services/api'
import './Albums.css'

export default function Albums() {
    const queryClient = useQueryClient()
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [newAlbumName, setNewAlbumName] = useState('')
    const [newAlbumDescription, setNewAlbumDescription] = useState('')

    const { data: albums, isLoading } = useQuery({
        queryKey: ['albums'],
        queryFn: async () => {
            const response = await api.get('/albums')
            return response.data
        }
    })

    const createMutation = useMutation({
        mutationFn: async (albumData) => {
            const response = await api.post('/albums', albumData)
            return response.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['albums'] })
            setShowCreateModal(false)
            setNewAlbumName('')
            setNewAlbumDescription('')
        }
    })

    const deleteMutation = useMutation({
        mutationFn: async (albumId) => {
            await api.delete(`/albums/${albumId}`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['albums'] })
        }
    })

    const handleCreateAlbum = () => {
        if (!newAlbumName.trim()) {
            alert('Album name is required')
            return
        }

        createMutation.mutate({
            name: newAlbumName,
            description: newAlbumDescription || null
        })
    }

    const handleDeleteAlbum = (albumId, albumName) => {
        if (window.confirm(`Delete album "${albumName}"? Photos will not be deleted.`)) {
            deleteMutation.mutate(albumId)
        }
    }

    // if (isLoading) return <div className="loading">Loading albums...</div>

    return (
        <div className="albums-container">
            <div className="albums-header">
                <h1>Albums</h1>
                <button className="btn-create-album" onClick={() => setShowCreateModal(true)}>
                    + New Album
                </button>
            </div>

            {isLoading ? (
                <div className="albums-grid">
                    {[...Array(6)].map((_, i) => (
                        <AlbumCardSkeleton key={i} />
                    ))}
                </div>
            ) : !albums || albums.length === 0 ? (
                <div className="empty-state">
                    <h2>No albums yet</h2>
                    <p>Create your first album to organize your photos</p>
                    <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
                        + Create Album
                    </button>
                </div>
            ) : (
                <div className="albums-grid">
                    {albums.map((album) => (
                        <div key={album.album_id} className="album-card">
                            <Link to={`/albums/${album.album_id}`} className="album-link">
                                <div className="album-cover">
                                    {album.thumbnail_urls && album.thumbnail_urls.length > 0 ? (
                                        <div className={`album-collage count-${Math.min(album.thumbnail_urls.length, 3)}`}>
                                            <div className="collage-main">
                                                <img
                                                    src={album.thumbnail_urls[0]}
                                                    alt={album.name}
                                                />
                                            </div>
                                            {album.thumbnail_urls.length > 1 && (
                                                <div className="collage-side">
                                                    <img
                                                        src={album.thumbnail_urls[1]}
                                                        alt={album.name}
                                                    />
                                                    {album.thumbnail_urls.length > 2 && (
                                                        <img
                                                            src={album.thumbnail_urls[2]}
                                                            alt={album.name}
                                                        />
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ) : album.cover_photo_url ? (
                                        <img
                                            src={album.cover_photo_url}
                                            alt={album.name}
                                        />
                                    ) : (
                                        <div className="album-placeholder">
                                            📁
                                        </div>
                                    )}
                                    <div className="album-count">{album.photo_count} photos</div>
                                </div>
                                <div className="album-info">
                                    <h3>{album.name}</h3>
                                    {album.description && (
                                        <p className="album-description">{album.description}</p>
                                    )}
                                </div>
                            </Link>
                            <div className="album-actions">
                                <button
                                    className="btn-delete-album"
                                    onClick={(e) => {
                                        e.preventDefault() // Prevent navigation
                                        handleDeleteAlbum(album.album_id, album.name)
                                    }}
                                    title="Delete Album"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Create Album Modal */}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Create New Album</h2>
                            <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            <div className="form-group">
                                <label>Album Name *</label>
                                <input
                                    type="text"
                                    value={newAlbumName}
                                    onChange={(e) => setNewAlbumName(e.target.value)}
                                    placeholder="My Album"
                                    autoFocus
                                />
                            </div>
                            <div className="form-group">
                                <label>Description</label>
                                <textarea
                                    value={newAlbumDescription}
                                    onChange={(e) => setNewAlbumDescription(e.target.value)}
                                    placeholder="Optional description..."
                                    rows={3}
                                />
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>
                                Cancel
                            </button>
                            <button
                                className="btn-primary"
                                onClick={handleCreateAlbum}
                                disabled={createMutation.isLoading}
                            >
                                {createMutation.isLoading ? 'Creating...' : 'Create Album'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
