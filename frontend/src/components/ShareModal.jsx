import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Copy, Trash2, Globe, Lock, X } from 'lucide-react'
import api from '../services/api'
import './ShareModal.css'

export default function ShareModal({ isOpen, onClose, albumId }) {
    const queryClient = useQueryClient()
    const [isCreating, setIsCreating] = useState(false)

    // Fetch existing share links
    const { data: shareLinks, isLoading } = useQuery({
        queryKey: ['shareLinks', albumId],
        queryFn: async () => {
            const res = await api.get(`/albums/${albumId}/share`)
            return res.data
        },
        enabled: isOpen && !!albumId
    })

    // Create share link mutation
    const createMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post(`/albums/${albumId}/share`, {
                is_public: true, // Default to public for now
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

                <div className="modal-body">
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
                        <h3>Active Links</h3>
                        {isLoading ? (
                            <p className="loading-text">Loading links...</p>
                        ) : shareLinks?.length === 0 ? (
                            <p className="empty-text">No active share links.</p>
                        ) : (
                            <div className="links-list">
                                {shareLinks.map(link => (
                                    <div key={link.token} className="link-item">
                                        <div className="link-info">
                                            <Globe size={16} className="link-icon" />
                                            <div className="link-details">
                                                <span className="link-url">
                                                    {window.location.origin}/shared/{link.token.substring(0, 8)}...
                                                </span>
                                                <span className="link-meta">
                                                    {link.views} views • Created {new Date(link.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="link-actions">
                                            <button
                                                className="btn-icon"
                                                onClick={() => handleCopyLink(link.token)}
                                                title="Copy Link"
                                            >
                                                <Copy size={16} />
                                            </button>
                                            <button
                                                className="btn-icon danger"
                                                onClick={() => {
                                                    if (window.confirm('Revoke this link? Users with this link will no longer be able to view the album.')) {
                                                        revokeMutation.mutate(link.token)
                                                    }
                                                }}
                                                title="Revoke Link"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
