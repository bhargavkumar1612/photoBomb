import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Mail, Clock, ChevronRight, Share2, Download, RefreshCw } from 'lucide-react'
import Masonry from 'react-masonry-css'
import Lightbox from '../components/Lightbox'
import api from '../services/api'
import ShareModal from '../components/ShareModal'
import PhotoItem from '../components/PhotoItem'
import { groupPhotosByDate } from '../utils/dateGrouping'
import './Timeline.css'
import './Sharing.css'

export default function Sharing() {
    const [activeTab, setActiveTab] = useState('inbox')
    const [selectedSender, setSelectedSender] = useState(null) // For Inbox Drill-down
    const [lightboxPhoto, setLightboxPhoto] = useState(null)
    const [isShareModalOpen, setIsShareModalOpen] = useState(false)

    // Inbox Query
    const { data: inbox, isLoading: inboxLoading } = useQuery({
        queryKey: ['sharing', 'inbox'],
        queryFn: async () => {
            const res = await api.get('/sharing/inbox')
            return res.data
        }
    })

    // Connections Query
    const { data: connections, isLoading: connectionsLoading } = useQuery({
        queryKey: ['sharing', 'connections'],
        queryFn: async () => {
            const res = await api.get('/sharing/connections')
            return res.data
        }
    })

    // Prepare photos for Lightbox/Drilldown
    // To show photos for a specific sender, we need to fetch them? 
    // The current InboxItem only has preview_thumbs. 
    // Actually, looking at the API, I implemented /Inbox to return summary.
    // I probably need an endpoint to get the actual photos from a sender?
    // Wait, the InboxItem in backend implementation:
    // It groups purely by sender. It doesn't return the full photo list in the list view (only previews).

    // Oh, I didn't verify the full payload of InboxItem in the router implementation.
    // Let's look at router...
    // Router logic:
    // It iterates `shares`. It DOES NOT attach the full photo list to `group`.
    // It only attaches `preview_thumbs`.
    // So I cannot show the full grid yet. 
    // I need to either:
    // 1. Modify /inbox to return ALL photos (heavy).
    // 2. Add GET /sharing/inbox/{sender_id} to get details.

    // For now, I'll modify the backend router to include `photos` in the response if it's manageable, 
    // OR I will simply add a "Photos" array to the InboxItem in the backend. 
    // Given the task is "Direct Photo Sharing", users likely want to see ALL photos shared by John.

    // Let's assume I will hot-fix the backend in the next step to include `photos` in InboxItem.
    // I'll write the frontend expecting `senderGroup.photos`.

    const handleSenderClick = (senderGroup) => {
        setSelectedSender(senderGroup)
    }

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString(undefined, {
            month: 'short', day: 'numeric', year: 'numeric'
        })
    }

    const handleDownload = (photo) => {
        const url = photo.thumb_urls.original
        const link = document.createElement('a')
        link.href = url
        link.download = photo.filename
        link.target = "_blank"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
    }

    const handleInfo = (photo) => {
        alert(`File: ${photo.filename}\nDate: ${new Date(photo.taken_at).toLocaleString()}`)
    }

    // Group photos for sender detail view
    const groupedSharedPhotos = selectedSender && selectedSender.photos ? groupPhotosByDate(selectedSender.photos, { dateField: 'shared_at' }) : []

    return (
        <div className="timeline-container sharing-page">
            {/* Header */}
            {/* Header - Only hide when drilling down? No, replace sharing header with drilldown header if selectedSender is present for better layout. Or just keep it and show breadcrumb. 
            Plan: Hide main header when drilling down to give full attention to sender content. */}
            {!selectedSender && (
                <div className="sharing-header">
                    <h1>Sharing</h1>
                    <div className="tabs">
                        <button
                            className={`tab-btn ${activeTab === 'inbox' ? 'active' : ''}`}
                            onClick={() => { setActiveTab('inbox'); setSelectedSender(null) }}
                        >
                            Inbox
                        </button>
                        <button
                            className={`tab-btn ${activeTab === 'connections' ? 'active' : ''}`}
                            onClick={() => { setActiveTab('connections'); setSelectedSender(null) }}
                        >
                            Connections
                        </button>
                    </div>
                </div>
            )}

            {/* Inbox View */}
            {activeTab === 'inbox' && (
                <div className="inbox-container">
                    {inboxLoading ? (
                        <div className="loading-state">
                            <RefreshCw className="animate-spin" /> Loading inbox...
                        </div>
                    ) : !inbox || inbox.length === 0 ? (
                        <div className="empty-state">
                            <Mail size={48} className="text-gray-300" />
                            <h3>No shared photos yet</h3>
                            <p>Photos sent to you directly will appear here.</p>
                        </div>
                    ) : selectedSender ? (
                        // Drilldown View
                        <div className="sender-detail-view">
                            <div className="detail-top-bar">
                                <button className="btn-back-large" onClick={() => setSelectedSender(null)}>
                                    <ChevronRight size={24} className="rotate-180" />
                                </button>
                                <div className="sender-profile">
                                    <div className="sender-avatar-large">
                                        {selectedSender.sender.full_name.charAt(0)}
                                    </div>
                                    <div className="sender-meta">
                                        <span>{selectedSender.sender.email}</span>
                                        <span className="dot">•</span>
                                        <span>
                                            {selectedSender.photo_count} photos
                                            {selectedSender.album_count > 0 && `, ${selectedSender.album_count} albums`}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Shared Albums Section */}
                            {selectedSender.albums && selectedSender.albums.length > 0 && (
                                <div className="detail-section">
                                    <h3>Shared Albums ({selectedSender.albums.length})</h3>
                                    <div className="albums-grid-small">
                                        {selectedSender.albums.map(album => (
                                            <div key={album.album_id} className="album-card-small" onClick={() => window.location.href = `/albums/${album.album_id}`}>
                                                <div className="album-cover">
                                                    {album.cover_photo_url ? (
                                                        <img src={album.cover_photo_url} alt={album.name} />
                                                    ) : (
                                                        <div className="placeholder-cover" />
                                                    )}
                                                </div>
                                                <div className="album-info">
                                                    <h4>{album.name}</h4>
                                                    <span>{new Date(album.created_at).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Photos Grid */}
                            <h3>Shared Photos ({selectedSender.photos?.length || 0})</h3>
                            {groupedSharedPhotos.length > 0 ? (
                                <div className="timeline-content">
                                    {groupedSharedPhotos.map((group) => (
                                        <div key={group.label} className="date-group">
                                            <h3 className="group-header">{group.label}</h3>
                                            <Masonry
                                                breakpointCols={{ default: 4, 1100: 3, 700: 2, 500: 1 }}
                                                className="my-masonry-grid photo-grid"
                                                columnClassName="my-masonry-grid_column"
                                            >
                                                {group.photos.map(photo => (
                                                    <PhotoItem
                                                        key={photo.photo_id}
                                                        photo={photo}
                                                        selectionMode={false}
                                                        isSelected={false}
                                                        onLightbox={setLightboxPhoto}
                                                        onDownload={handleDownload}
                                                        onInfo={handleInfo}
                                                        readonly={true}
                                                    />
                                                ))}
                                            </Masonry>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="empty-text">No direct photos shared.</p>
                            )}
                        </div>
                    ) : (
                        // List View
                        <div className="inbox-list">
                            {inbox.map((group, idx) => (
                                <div key={group.sender.user_id} className="inbox-item" onClick={() => handleSenderClick(group)}>
                                    <div className="sender-avatar">
                                        {group.sender.full_name.charAt(0)}
                                    </div>
                                    <div className="inbox-content">
                                        <div className="sender-name">
                                            {group.sender.full_name}
                                            <span className="count-badge">{(group.photo_count || 0) + (group.album_count || 0)}</span>
                                        </div>
                                        <div className="inbox-meta">
                                            <Clock size={12} /> {formatDate(group.latest_share_date)}
                                            <span className="email">{group.sender.email}</span>
                                        </div>
                                        <div className="preview-strip">
                                            {group.preview_thumbs && group.preview_thumbs.map((url, i) => (
                                                <img key={i} src={url} alt="preview" className="mini-thumb" />
                                            ))}
                                        </div>
                                    </div>
                                    <ChevronRight size={20} className="arrow-icon" />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Connections View */}
            {activeTab === 'connections' && (
                <div className="connections-container">
                    {connectionsLoading ? (
                        <div className="loading-state">Loading...</div>
                    ) : !connections || connections.length === 0 ? (
                        <div className="empty-state">
                            <Users size={48} className="text-gray-300" />
                            <h3>No connections yet</h3>
                            <p>Share photos with people to build your connections list.</p>
                        </div>
                    ) : (
                        <div className="connections-grid">
                            {connections.map(user => (
                                <div key={user.user_id} className="connection-card">
                                    <div className="card-avatar">
                                        {user.full_name.charAt(0)}
                                    </div>
                                    <div className="card-info">
                                        <h4>{user.full_name}</h4>
                                        <p>{user.email}</p>
                                    </div>
                                    <button className="btn-secondary btn-sm" onClick={() => setIsShareModalOpen(true)}>
                                        <Share2 size={14} /> Share
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <ShareModal isOpen={isShareModalOpen} onClose={() => setIsShareModalOpen(false)} />

            {lightboxPhoto && (
                <Lightbox
                    photo={lightboxPhoto}
                    photos={selectedSender?.photos || []}
                    onClose={() => setLightboxPhoto(null)}
                    onNavigate={setLightboxPhoto}
                />
            )}
        </div>
    )
}
