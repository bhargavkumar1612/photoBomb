import { useState, useEffect } from 'react'
import { ListFilter } from 'lucide-react'
import './SearchBar.css'

export default function SearchBar({ onSearch, onFilterChange, filters }) {
    const [searchTerm, setSearchTerm] = useState('')
    const [showFilters, setShowFilters] = useState(false)

    const handleSearchChange = (e) => {
        const value = e.target.value
        setSearchTerm(value)
        onSearch(value)
    }

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

    // Close on click outside (optional helper, if needed, but user specifically asked for Esc and Close button)
    // We'll stick to the requested explicit close button inside the panel + Esc.

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
                    className={`filter-toggle ${showFilters ? 'active' : ''}`}
                    onClick={() => setShowFilters(!showFilters)}
                >
                    <ListFilter size={18} style={{ marginRight: 6 }} />
                    Filters
                </button>
            </div>

            {showFilters && (
                <div className="filters-panel">
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
                                className={filters.sortBy === 'date-desc' ? 'active' : ''}
                                onClick={() => handleSortChange('date-desc')}
                            >
                                Newest First
                            </button>
                            <button
                                className={filters.sortBy === 'date-asc' ? 'active' : ''}
                                onClick={() => handleSortChange('date-asc')}
                            >
                                Oldest First
                            </button>
                            <button
                                className={filters.sortBy === 'name' ? 'active' : ''}
                                onClick={() => handleSortChange('name')}
                            >
                                Name
                            </button>
                            <button
                                className={filters.sortBy === 'size' ? 'active' : ''}
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
                                    checked={filters.fileTypes?.includes('image/jpeg')}
                                    onChange={() => handleTypeChange('image/jpeg')}
                                />
                                JPEG
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={filters.fileTypes?.includes('image/png')}
                                    onChange={() => handleTypeChange('image/png')}
                                />
                                PNG
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={filters.fileTypes?.includes('image/gif')}
                                    onChange={() => handleTypeChange('image/gif')}
                                />
                                GIF
                            </label>
                            <label>
                                <input
                                    type="checkbox"
                                    checked={filters.fileTypes?.includes('image/webp')}
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
                                value={filters.dateFrom || ''}
                                onChange={(e) => onFilterChange({ ...filters, dateFrom: e.target.value })}
                                placeholder="From"
                            />
                            <span>to</span>
                            <input
                                type="date"
                                value={filters.dateTo || ''}
                                onChange={(e) => onFilterChange({ ...filters, dateTo: e.target.value })}
                                placeholder="To"
                            />
                        </div>
                    </div>

                    <div className="filter-actions">
                        <button
                            className="btn-reset"
                            onClick={() => onFilterChange({ sortBy: 'date-desc', fileTypes: [], dateFrom: '', dateTo: '' })}
                        >
                            Reset Filters
                        </button>
                        <button
                            className="btn-primary-small"
                            onClick={() => setShowFilters(false)}
                            style={{
                                background: '#4f46e5',
                                color: 'white',
                                border: 'none',
                                padding: '8px 16px',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                marginLeft: 'auto'
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
