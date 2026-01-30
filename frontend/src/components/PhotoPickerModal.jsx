import { useQuery } from '@tanstack/react-query';
import Masonry from 'react-masonry-css';
import { X, Check } from 'lucide-react';
import api from '../services/api';
import { useModalKeyboard } from '../hooks/useModalKeyboard';
import './PhotoPickerModal.css';

export default function PhotoPickerModal({ isOpen, onClose, onAdd, existingPhotoIds = [] }) {
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [searchTerm, setSearchTerm] = useState('');

    const handleAdd = () => {
        if (selectedIds.size > 0) {
            onAdd(Array.from(selectedIds));
        }
    };

    useModalKeyboard({ isOpen, onClose, onConfirm: handleAdd, confirmOnEnter: true })

    // Reuse photos query
    const { data, isLoading } = useQuery({
        queryKey: ['photos'],
        queryFn: async () => {
            const response = await api.get('/photos');
            return response.data;
        }
    });

    // Reset selection when opened
    useEffect(() => {
        if (isOpen) setSelectedIds(new Set());
    }, [isOpen]);

    if (!isOpen) return null;

    const toggleSelection = (id) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        setSelectedIds(newSet);
    };

    // ... (rest of filtering logic, no changes needed to logic itself, just re-rendering)

    // Filter out already added photos
    const availablePhotos = data?.photos?.filter(p => !existingPhotoIds.includes(p.photo_id)) || [];

    // Filter by search (simple filename match)
    const filteredPhotos = availablePhotos.filter(p =>
        !searchTerm || p.filename.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const breakpointColumns = {
        default: 4,
        1100: 3,
        700: 2,
        500: 2 // Keep 2 on mobile for picking
    };

    return (
        <div className="picker-overlay">
            <div className="picker-modal">
                <div className="picker-header">
                    <h3>Add Photos to Album</h3>
                    <div className="picker-actions">
                        <span className="selection-count">{selectedIds.size} selected</span>
                        <button onClick={onClose} className="btn-close"><X size={20} /></button>
                    </div>
                </div>

                <div className="picker-content">
                    {isLoading ? (
                        <div className="loading">Loading photos...</div>
                    ) : filteredPhotos.length === 0 ? (
                        <div className="empty-state">No more photos to add!</div>
                    ) : (
                        <Masonry
                            breakpointCols={breakpointColumns}
                            className="picker-grid"
                            columnClassName="picker-grid_column"
                        >
                            {filteredPhotos.map(photo => {
                                const isSelected = selectedIds.has(photo.photo_id);
                                return (
                                    <div
                                        key={photo.photo_id}
                                        className={`picker-card ${isSelected ? 'selected' : ''}`}
                                        onClick={() => toggleSelection(photo.photo_id)}
                                        tabIndex={0}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') {
                                                e.stopPropagation(); // prevent modal confirm
                                                toggleSelection(photo.photo_id);
                                            }
                                        }}
                                    >
                                        <img
                                            src={photo.thumb_urls.thumb_512}
                                            alt={photo.filename}
                                            loading="lazy"
                                        />
                                        <div className="selection-overlay">
                                            {isSelected && <div className="check-circle"><Check size={16} color="white" /></div>}
                                        </div>
                                    </div>
                                );
                            })}
                        </Masonry>
                    )}
                </div>

                <div className="picker-footer">
                    <button className="btn-cancel" onClick={onClose}>Cancel</button>
                    <button
                        className="btn-add"
                        disabled={selectedIds.size === 0}
                        onClick={handleAdd}
                    >
                        Add {selectedIds.size} Photos
                    </button>
                </div>
            </div>
        </div>
    );
}
