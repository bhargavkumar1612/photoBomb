import { useState, useEffect, useRef } from 'react'
import { ListFilter } from 'lucide-react'
import './SearchBar.css'

export default function SearchBar({ onSearch, onFilterChange, filters }) {
    const [searchTerm, setSearchTerm] = useState('')
    const [showFilters, setShowFilters] = useState(false)
    const [tempFilters, setTempFilters] = useState(filters)

    const filtersRef = useRef(null)
    const toggleRef = useRef(null)

    // Sync tempFilters with main filters when they change externally (e.g. initial load)
    // BUT user wanted draft state to persist if closed without applying.
    // We only sync if the "Applied" filters change (which happens when we click Apply).
    useEffect(() => {
        // Only sync if they are actually applied?
        // Actually, if we initialize state once, it persists.
        // We will manually sync when Apply is clicked? No, parent passes new props.
        // Let's rely on props updating to sync? 
        // No, if we sync on prop change, we overwrite the draft if the parent re-renders.
        // But the parent only re-renders filters when WE call onFilterChange.
        // So it's safe to sync.
        setTempFilters(filters)
    }, [filters])
    // Wait, if I change temp, don't apply, close. 
    // filters prop is unchanged. useEffect [filters] doesn't fire. temp follows draft. Correct.
    // If I click Apply -> onFilterChange -> parent updates filters -> useEffect fires -> temp syncs (but they are equal). Correct.

    const handleSearchChange = (e) => {
        const value = e.target.value
        setSearchTerm(value)
        onSearch(value)
    }

    const handleSortChange = (sortType) => {
        setTempFilters(prev => ({ ...prev, sortBy: sortType }))
    }

    const handleTypeChange = (type) => {
        setTempFilters(prev => {
            const currentTypes = prev.fileTypes || []
            if (currentTypes.includes(type)) {
                return { ...prev, fileTypes: currentTypes.filter(t => t !== type) }
            } else {
                return { ...prev, fileTypes: [...currentTypes, type] }
            }
        })
    }

    const handleDateChange = (field, value) => {
        setTempFilters(prev => ({ ...prev, [field]: value }))
    }

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (
                showFilters &&
                filtersRef.current &&
                !filtersRef.current.contains(event.target) &&
                toggleRef.current &&
                !toggleRef.current.contains(event.target)
            ) {
                setShowFilters(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showFilters])

    // Close on Escape key
    useEffect(() => {
        const handleEsc = (e) => {
            if (e.key === 'Escape') setShowFilters(false);
        };
        if (showFilters) {
            document.addEventListener('keydown', handleEsc);
        }
        return () => document.removeEventListener('keydown', handleEsc);
    }, [showFilters]);

    // Check if dirty
    const isDirty = JSON.stringify(tempFilters) !== JSON.stringify(filters)

    return (
        <div className="search-bar-container">
            <div className="search-input-wrapper">
                <span className="search-icon">🔍</span>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search photos by filename, date, or location..."
                    value={searchTerm}
                    onChange={handleSearchChange}
                />
                {searchTerm && (
                    <button className="clear-search" onClick={() => { setSearchTerm(''); onSearch('') }}>
                        ×
                    </button>
                )}
                <button
                    ref={toggleRef}
                    className={`filter-toggle ${showFilters ? 'active' : ''}`}
                    onClick={() => setShowFilters(!showFilters)}
                >
                    <ListFilter size={18} style={{ marginRight: 6 }} />
                    Filters
                </button>
            </div>

            {showFilters && (
                <div className="filters-panel" ref={filtersRef}>
                    <div className="filters-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>Filters</h3>
                        <button
                            onClick={() => setShowFilters(false)}
                            style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', color: '#6b7280' }}
                        >
                            ×
                        </button>
                    </div>

                    <div className="filter-section">
                        <label>Sort By</label>
                        <div className="filter-buttons">
                            <button
                                className={tempFilters.sortBy === 'date-desc' ? 'active' : ''}
                                onClick={() => handleSortChange('date-desc')}
                            >
                                Newest First
                            </button>
                            <button
                                className={tempFilters.sortBy === 'date-asc' ? 'active' : ''}
                                onClick={() => handleSortChange('date-asc')}
                            >
                                Oldest First
                            </button>
                            <button
                                className={tempFilters.sortBy === 'name' ? 'active' : ''}
                                onClick={() => handleSortChange('name')}
                            >
                                Name
                            </button>
                            <button
                                className={tempFilters.sortBy === 'size' ? 'active' : ''}
                                onClick={() => handleSortChange('size')}
                            >
                                Size
                            </button>
                        </div>
                    </div>

                    <div className="filter-section">
                        <label>File Type</label>
                        <div className="filter-checkboxes">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={tempFilters.fileTypes?.includes('image/jpeg')}
                                    onChange={() => handleTypeChange('image/jpeg')}
                                />
                                JPEG
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={tempFilters.fileTypes?.includes('image/png')}
                                    onChange={() => handleTypeChange('image/png')}
                                />
                                PNG
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={tempFilters.fileTypes?.includes('image/gif')}
                                    onChange={() => handleTypeChange('image/gif')}
                                />
                                GIF
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={tempFilters.fileTypes?.includes('image/webp')}
                                    onChange={() => handleTypeChange('image/webp')}
                                />
                                WebP
                            </label>
                        </div>
                    </div>

                    <div className="filter-section">
                        <label>Date Range</label>
                        <div className="date-inputs">
                            <input
                                type="date"
                                value={tempFilters.dateFrom || ''}
                                onChange={(e) => handleDateChange('dateFrom', e.target.value)}
                                placeholder="From"
                            />
                            <span>to</span>
                            <input
                                type="date"
                                value={tempFilters.dateTo || ''}
                                onChange={(e) => handleDateChange('dateTo', e.target.value)}
                                placeholder="To"
                            />
                        </div>
                    </div>

                    <div className="filter-actions">
                        <button
                            className="btn-reset"
                            onClick={() => setTempFilters({ sortBy: 'date-desc', fileTypes: [], dateFrom: '', dateTo: '' })}
                        >
                            Reset Filters
                        </button>
                        <button
                            className="btn-primary-small"
                            disabled={!isDirty}
                            onClick={() => {
                                onFilterChange(tempFilters)
                                setShowFilters(false)
                            }}
                            style={{
                                background: isDirty ? '#4f46e5' : '#9ca3af',
                                color: 'white',
                                border: 'none',
                                padding: '8px 16px',
                                borderRadius: '6px',
                                cursor: isDirty ? 'pointer' : 'not-allowed',
                                marginLeft: 'auto',
                                opacity: isDirty ? 1 : 0.7
                            }}
                        >
                            Apply
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
