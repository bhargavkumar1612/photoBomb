import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Copy, Trash2, Globe, X, Eye } from 'lucide-react'
import api from '../services/api'
import './ShareModal.css'

export default function ShareModal({ isOpen, onClose, albumId }) {
    const queryClient = useQueryClient()
    const [isCreating, setIsCreating] = useState(false)
    const [activeTab, setActiveTab] = useState('links') // links | viewers

    // Fetch existing share links
    const { data: shareLinks, isLoading: isLoadingLinks } = useQuery({
        queryKey: ['shareLinks', albumId],
        queryFn: async () => {
            const res = await api.get(`/albums/${albumId}/share`)
            return res.data
        },
        enabled: isOpen && !!albumId
    })

    // Aggregate unique viewers from all share links
    const allViewers = useMemo(() => {
        if (!shareLinks) return []

        const viewerMap = new Map()

        shareLinks.forEach(link => {
            if (link.viewers && link.viewers.length > 0) {
                link.viewers.forEach(viewer => {
                    const existing = viewerMap.get(viewer.user_id)
                    // Keep the most recent view
                    if (!existing || new Date(viewer.viewed_at) > new Date(existing.viewed_at)) {
                        viewerMap.set(viewer.user_id, viewer)
                    }
                })
            }
        })

        // Convert to array and sort by most recent view
        return Array.from(viewerMap.values()).sort((a, b) =>
            new Date(b.viewed_at) - new Date(a.viewed_at)
        )
    }, [shareLinks])

    // Create share link mutation
    const createMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post(`/albums/${albumId}/share`, {
                is_public: true,
                expires_at: null
            })
            return res.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['shareLinks', albumId] })
            setIsCreating(false)
        }
    })

    // Revoke share link mutation
    const revokeMutation = useMutation({
        mutationFn: async (token) => {
            await api.delete(`/share/${token}`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['shareLinks', albumId] })
        }
    })

    const handleCreateLink = () => {
        setIsCreating(true)
        createMutation.mutate()
    }

    const handleCopyLink = (token) => {
        const link = `${window.location.origin}/shared/${token}`
        navigator.clipboard.writeText(link)
        alert('Link copied to clipboard!')
    }

    if (!isOpen) return null

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content share-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Share Album</h2>
                    <button className="btn-close" onClick={onClose}><X size={20} /></button>
                </div>

                <div className="modal-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'links' ? 'active' : ''}`}
                        onClick={() => setActiveTab('links')}
                    >
                        <Globe size={16} /> Public Links
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'viewers' ? 'active' : ''}`}
                        onClick={() => setActiveTab('viewers')}
                    >
                        <Eye size={16} /> Viewers
                    </button>
                </div>

                <div className="modal-body">
                    {activeTab === 'links' && (
                        <>
                            <div className="share-actions">
                                <button
                                    className="btn-primary"
                                    onClick={handleCreateLink}
                                    disabled={createMutation.isPending}
                                >
                                    {createMutation.isPending ? 'Creating...' : 'Create Public Link'}
                                </button>
                            </div>

                            <div className="active-links">
                                {isLoadingLinks ? (
                                    <p className="loading-text">Loading links...</p>
                                ) : shareLinks?.length === 0 ? (
                                    <p className="empty-text">No active share links.</p>
                                ) : (
                                    <div className="links-list">
                                        {shareLinks?.map(link => (
                                            <div key={link.token} className="link-item">
                                                <div className="link-main">
                                                    <div className="link-header">
                                                        <Globe size={16} className="link-icon" />
                                                        <span className="link-meta">
                                                            {link.views} views • Created {new Date(link.created_at).toLocaleDateString()}
                                                        </span>
                                                    </div>
                                                    <div className="link-url-container">
                                                        <div className="link-url-text">
                                                            {window.location.origin}/shared/{link.token}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="link-actions-row">
                                                    <button
                                                        className="btn-secondary btn-sm"
                                                        onClick={() => handleCopyLink(link.token)}
                                                    >
                                                        <Copy size={14} /> Copy
                                                    </button>
                                                    <button
                                                        className="btn-danger btn-sm"
                                                        onClick={() => {
                                                            if (window.confirm('Are you sure you want to delete this link?')) {
                                                                revokeMutation.mutate(link.token)
                                                            }
                                                        }}
                                                    >
                                                        <Trash2 size={14} /> Revoke
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {activeTab === 'viewers' && (
                        <div className="viewers-section">
                            {isLoadingLinks ? (
                                <p className="loading-text">Loading viewers...</p>
                            ) : allViewers.length === 0 ? (
                                <div className="empty-state">
                                    <Eye size={48} style={{ color: '#9ca3af', marginBottom: '12px' }} />
                                    <p className="empty-text">No one has viewed this album yet.</p>
                                    <p className="info-text" style={{ fontSize: '14px', marginTop: '8px' }}>
                                        Share a public link to see who views your album.
                                    </p>
                                </div>
                            ) : (
                                <div className="viewers-list-full">
                                    <div className="viewers-header">
                                        <h3>{allViewers.length} {allViewers.length === 1 ? 'Viewer' : 'Viewers'}</h3>
                                        <p className="info-text">People who have viewed your shared links</p>
                                    </div>
                                    <div className="viewers-grid">
                                        {allViewers.map((viewer, index) => (
                                            <div key={viewer.user_id || index} className="viewer-card">
                                                <div className="viewer-avatar">
                                                    {viewer.full_name?.charAt(0).toUpperCase() || '?'}
                                                </div>
                                                <div className="viewer-info">
                                                    <div className="viewer-name">{viewer.full_name || 'Anonymous'}</div>
                                                    <div className="viewer-time">
                                                        {new Date(viewer.viewed_at).toLocaleString()}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
