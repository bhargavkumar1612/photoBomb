import { useState, useMemo, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Copy, Trash2, Globe, X, Eye, Mail, User, Send } from 'lucide-react'
import api from '../services/api'
import { useModalKeyboard } from '../hooks/useModalKeyboard'
import './ShareModal.css'

export default function ShareModal({ isOpen, onClose, albumId, photoIds = [] }) {
    useModalKeyboard({ isOpen, onClose })

    const queryClient = useQueryClient()
    const [activeTab, setActiveTab] = useState('email') // email | links | viewers
    const [email, setEmail] = useState('')
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [shareResult, setShareResult] = useState(null) // { status: 'shared' | 'link', link: string, message: string }
    const dropdownRef = useRef(null)

    // Determine mode
    const isAlbumMode = !!albumId
    const isPhotoMode = !isAlbumMode && photoIds.length > 0

    // Set default tab based on mode
    useEffect(() => {
        if (isOpen) {
            setShareResult(null)
            setEmail('')
            if (isPhotoMode) setActiveTab('email')
            else if (isAlbumMode && activeTab === 'email') setActiveTab('links') // Default to links for album for now? Or email?
            // Let's allow email for albums too if we implement it, but for now Album email sharing wasn't explicitly built in backend for /sharing/photos
            // The backend /sharing/photos takes photo_ids. 
            // So if AlbumMode, we probably stick to Links.
        }
    }, [isOpen, isPhotoMode, isAlbumMode])

    // --- Connections (Autocomplete) ---
    const { data: connections } = useQuery({
        queryKey: ['sharing', 'connections'],
        queryFn: async () => {
            const res = await api.get('/sharing/connections')
            return res.data
        },
        enabled: isOpen && isPhotoMode
    })

    const filteredConnections = useMemo(() => {
        if (!email || !connections) return []
        const term = email.toLowerCase()
        return connections.filter(c =>
            c.email.toLowerCase().includes(term) ||
            c.full_name.toLowerCase().includes(term)
        ).slice(0, 5)
    }, [email, connections])


    // --- Photo Sharing Mutation ---
    const sharePhotosMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post('/sharing/photos', {
                photo_ids: photoIds,
                target_email: email
            })
            return res.data
        },
        onSuccess: (data) => {
            setShareResult(data)
            queryClient.invalidateQueries({ queryKey: ['sharing', 'inbox'] }) // In case we shared to self?
            queryClient.invalidateQueries({ queryKey: ['sharing', 'connections'] })
        },
        onError: (err) => {
            alert(err.response?.data?.detail || "Failed to share")
        }
    })

    // --- Album Links Query ---
    const { data: shareLinks, isLoading: isLoadingLinks } = useQuery({
        queryKey: ['shareLinks', albumId],
        queryFn: async () => {
            const res = await api.get(`/albums/${albumId}/share`)
            return res.data
        },
        enabled: isOpen && isAlbumMode
    })

    // Aggregate unique viewers (Album Mode)
    const allViewers = useMemo(() => {
        if (!shareLinks) return []
        const viewerMap = new Map()
        shareLinks.forEach(link => {
            if (link.viewers) {
                link.viewers.forEach(viewer => {
                    const existing = viewerMap.get(viewer.user_id)
                    if (!existing || new Date(viewer.viewed_at) > new Date(existing.viewed_at)) {
                        viewerMap.set(viewer.user_id, viewer)
                    }
                })
            }
        })
        return Array.from(viewerMap.values()).sort((a, b) => new Date(b.viewed_at) - new Date(a.viewed_at))
    }, [shareLinks])

    // Album Link Mutations
    const createLinkMutation = useMutation({
        mutationFn: async () => {
            const res = await api.post(`/albums/${albumId}/share`, { is_public: true })
            return res.data
        },
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shareLinks', albumId] })
    })

    const revokeLinkMutation = useMutation({
        mutationFn: async (token) => api.delete(`/share/${token}`),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['shareLinks', albumId] })
    })

    // Handlers
    const handleShareSubmit = (e) => {
        e.preventDefault()
        if (!email) return
        sharePhotosMutation.mutate()
    }

    const selectConnection = (conn) => {
        setEmail(conn.email)
        setShowSuggestions(false)
    }

    const handleCopyLink = (token) => {
        const link = `${window.location.origin}/shared/${token}`
        navigator.clipboard.writeText(link)
        alert('Link copied!')
    }

    const handleCopyInviteLink = () => {
        if (shareResult?.link) {
            navigator.clipboard.writeText(shareResult.link)
            alert('Invite link copied!')
        }
    }

    if (!isOpen) return null

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content share-modal" onClick={e => { e.stopPropagation(); setShowSuggestions(false); }}>
                <div className="modal-header">
                    <h2>{isAlbumMode ? 'Share Album' : 'Share Photos'}</h2>
                    <button className="btn-close" onClick={onClose}><X size={20} /></button>
                </div>

                <div className="modal-tabs">
                    {isPhotoMode && (
                        <button className="tab-btn" onClick={() => setActiveTab('email')}>
                            <Mail size={16} /> Email
                        </button>
                    )}
                    {isAlbumMode && (
                        <>
                            <button className={`tab-btn ${activeTab === 'links' ? 'active' : ''}`} onClick={() => setActiveTab('links')}>
                                <Globe size={16} /> Public Links
                            </button>
                            <button className={`tab-btn ${activeTab === 'viewers' ? 'active' : ''}`} onClick={() => setActiveTab('viewers')}>
                                <Eye size={16} /> Viewers
                            </button>
                        </>
                    )}
                </div>

                <div className="modal-body">
                    {/* --- EMAIL SHARING TAB --- */}
                    {activeTab === 'email' && (
                        <div className="share-email-section">
                            {shareResult ? (
                                <div className="share-success">
                                    <div className="success-icon"><Send size={32} /></div>
                                    <h3>{shareResult.status === 'shared' ? 'Shared Successfully!' : 'Invite Link Generated'}</h3>
                                    <p>{shareResult.message}</p>

                                    {shareResult.link && (
                                        <div className="invite-link-box">
                                            <input type="text" readOnly value={shareResult.link} />
                                            <button className="btn-secondary" onClick={handleCopyInviteLink}>
                                                <Copy size={16} />
                                            </button>
                                        </div>
                                    )}

                                    <button className="btn-primary" onClick={() => { setShareResult(null); setEmail(''); onClose(); }}>
                                        Done
                                    </button>
                                </div>
                            ) : (
                                <form onSubmit={handleShareSubmit}>
                                    <p className="description">
                                        Share {photoIds.length} photo{photoIds.length !== 1 ? 's' : ''} directly with a user.
                                    </p>

                                    <div className="form-group" style={{ position: 'relative' }}>
                                        <label>Recipient Email</label>
                                        <div className="input-wrapper">
                                            <input
                                                type="email"
                                                value={email}
                                                onChange={(e) => { setEmail(e.target.value); setShowSuggestions(true); }}
                                                placeholder="friend@example.com"
                                                autoFocus
                                            />
                                        </div>

                                        {/* Autocomplete Dropdown */}
                                        {showSuggestions && filteredConnections.length > 0 && (
                                            <div className="autocomplete-dropdown" ref={dropdownRef}>
                                                {filteredConnections.map(conn => (
                                                    <div key={conn.user_id} className="suggestion-item" onClick={(e) => { e.stopPropagation(); selectConnection(conn); }}>
                                                        <div className="suggestion-avatar">
                                                            {conn.full_name.charAt(0)}
                                                        </div>
                                                        <div className="suggestion-info">
                                                            <div className="name">{conn.full_name}</div>
                                                            <div className="email">{conn.email}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    <div className="modal-actions">
                                        <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
                                        <button
                                            type="submit"
                                            className="btn-primary"
                                            disabled={!email || sharePhotosMutation.isPending}
                                        >
                                            {sharePhotosMutation.isPending ? 'Sending...' : 'Send'}
                                        </button>
                                    </div>
                                </form>
                            )}
                        </div>
                    )}

                    {/* --- ALBUM LINKS TAB --- */}
                    {activeTab === 'links' && isAlbumMode && (
                        <>
                            <div className="share-actions">
                                <button className="btn-primary" onClick={() => createLinkMutation.mutate()} disabled={createLinkMutation.isPending}>
                                    {createLinkMutation.isPending ? 'Creating...' : 'Create Public Link'}
                                </button>
                            </div>
                            <div className="active-links">
                                {isLoadingLinks ? <p>Loading...</p> : shareLinks?.length === 0 ? <p className="empty-text">No active links.</p> : (
                                    <div className="links-list">
                                        {shareLinks?.map(link => (
                                            <div key={link.token} className="link-item">
                                                <div className="link-main">
                                                    <div className="link-header">
                                                        <span className="link-meta">{link.views} views • {new Date(link.created_at).toLocaleDateString()}</span>
                                                    </div>
                                                    <div className="link-url-text">{window.location.origin}/shared/{link.token}</div>
                                                </div>
                                                <div className="link-actions-row">
                                                    <button className="btn-secondary btn-sm" onClick={() => handleCopyLink(link.token)}><Copy size={14} /></button>
                                                    <button className="btn-danger btn-sm" onClick={() => { if (confirm('Delete link?')) revokeMutation.mutate(link.token) }}><Trash2 size={14} /></button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* --- VIEWERS TAB --- */}
                    {activeTab === 'viewers' && isAlbumMode && (
                        <div className="viewers-section">
                            {allViewers.length === 0 ? <p className="empty-text">No views yet.</p> : (
                                <div className="viewers-grid">
                                    {allViewers.map((viewer, i) => (
                                        <div key={i} className="viewer-card">
                                            <div className="viewer-avatar">{viewer.full_name?.charAt(0) || '?'}</div>
                                            <div className="viewer-info">
                                                <div className="viewer-name">{viewer.full_name || 'Anonymous'}</div>
                                                <div className="viewer-time">{new Date(viewer.viewed_at).toLocaleDateString()}</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
