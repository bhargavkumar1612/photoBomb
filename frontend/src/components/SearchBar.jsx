import { useState } from 'react'
import './SearchBar.css'

export default function SearchBar({ onSearch, onFilterChange, filters }) {
    const [searchTerm, setSearchTerm] = useState('')
    const [showFilters, setShowFilters] = useState(false)

    const handleSearchChange = (e) => {
        const value = e.target.value
        setSearchTerm(value)
        onSearch(value)
    }

    const handleSortChange = (sortBy) => {
        onFilterChange({ ...filters, sortBy })
    }

    const handleTypeChange = (fileType) => {
        const newTypes = filters.fileTypes?.includes(fileType)
            ? filters.fileTypes.filter(t => t !== fileType)
            : [...(filters.fileTypes || []), fileType]
        onFilterChange({ ...filters, fileTypes: newTypes })
    }

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
                    ⚙️ Filters
                </button>
            </div>

            {showFilters && (
                <div className="filters-panel">
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
                    </div>
                </div>
            )}
        </div>
    )
}
