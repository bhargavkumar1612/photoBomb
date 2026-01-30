import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Plus, Folder, Loader2 } from 'lucide-react';
import api from '../services/api';
import { useModalKeyboard } from '../hooks/useModalKeyboard';
import './AddToAlbumModal.css';

export default function AddToAlbumModal({ isOpen, onClose, photoIds = [] }) {
    const [searchTerm, setSearchTerm] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [newAlbumName, setNewAlbumName] = useState('');
    const queryClient = useQueryClient();

    // Fetch existing albums
    const { data: albums, isLoading } = useQuery({
        queryKey: ['albums-list'],
        queryFn: async () => {
            const response = await api.get('/albums');
            return response.data;
        },
        enabled: isOpen
    });

    // Add to existing album mutation
    const addToAlbumMutation = useMutation({
        mutationFn: async ({ albumId, photos }) => {
            await api.post(`/albums/${albumId}/photos`, photos);
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['albums']);
            onClose();
            alert('Photos added to album successfully!');
        },
        onError: (err) => {
            alert('Failed to add photos: ' + err.message);
        }
    });

    // Create new album mutation
    const createAlbumMutation = useMutation({
        mutationFn: async (name) => {
            const response = await api.post('/albums', { name });
            return response.data;
        },
        onSuccess: (newAlbum) => {
            // Immediately add photos to the new album
            addToAlbumMutation.mutate({
                albumId: newAlbum.album_id,
                photos: photoIds
            });
        }
    });

    if (!isOpen) return null;

    const filteredAlbums = albums?.filter(a =>
        a.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

    const handleCreate = (e) => {
        e.preventDefault();
        if (!newAlbumName.trim()) return;
        createAlbumMutation.mutate(newAlbumName);
    };

    const handleSelectAlbum = (albumId) => {
        addToAlbumMutation.mutate({ albumId, photos: photoIds });
    };

    const isProcessing = addToAlbumMutation.isPending || createAlbumMutation.isPending;

    useModalKeyboard({ isOpen, onClose })

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <div className="modal-header">
                    <h3>Add {photoIds.length} Photo{photoIds.length !== 1 ? 's' : ''} to Album</h3>
                    <button onClick={onClose} className="btn-close"><X size={20} /></button>
                </div>

                <div className="modal-body">
                    {/* Create New Album Section */}
                    <div className="create-section">
                        {!isCreating ? (
                            <button className="btn-new-album" onClick={() => setIsCreating(true)}>
                                <Plus size={18} />
                                Create New Album
                            </button>
                        ) : (
                            <form onSubmit={handleCreate} className="create-form">
                                <input
                                    type="text"
                                    placeholder="Album Name"
                                    value={newAlbumName}
                                    onChange={e => setNewAlbumName(e.target.value)}
                                    autoFocus
                                />
                                <button type="submit" className="btn-save" disabled={!newAlbumName.trim() || isProcessing}>
                                    {isProcessing ? <Loader2 size={16} className="spin" /> : 'Create & Add'}
                                </button>
                                <button type="button" className="btn-cancel-create" onClick={() => setIsCreating(false)}>
                                    Cancel
                                </button>
                            </form>
                        )}
                    </div>

                    <div className="divider"><span>OR SELECT EXISTING</span></div>

                    {/* Search Field */}
                    <input
                        type="text"
                        placeholder="Search albums..."
                        className="search-albums"
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                    />

                    {/* Albums List */}
                    <div className="albums-list">
                        {isLoading ? (
                            <div className="loading-state"><Loader2 className="spin" /> Loading albums...</div>
                        ) : filteredAlbums.length === 0 ? (
                            <div className="empty-state">No albums found</div>
                        ) : (
                            filteredAlbums.map(album => (
                                <div
                                    key={album.album_id}
                                    className="album-item"
                                    onClick={() => handleSelectAlbum(album.album_id)}
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            handleSelectAlbum(album.album_id)
                                        }
                                    }}
                                >
                                    <div className="album-icon">
                                        {album.cover_photo_url ? (
                                            <img src={album.cover_photo_url} alt="" />
                                        ) : (
                                            <Folder size={24} />
                                        )}
                                    </div>
                                    <div className="album-info">
                                        <span className="album-name">{album.name}</span>
                                        <span className="album-count">{album.photo_count} photos</span>
                                    </div>
                                    {isProcessing && <Loader2 size={16} className="spin" />}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
