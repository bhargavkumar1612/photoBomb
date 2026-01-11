import { Link } from 'react-router-dom';
import { Menu, UploadCloud } from 'lucide-react';
import SearchBar from './SearchBar';
import UserProfile from './UserProfile';
import { useSearch } from '../context/SearchContext';
import './TopBar.css';

export default function TopBar({ onToggleSidebar }) {
    const { searchTerm, setSearchTerm, filters, setFilters } = useSearch();

    return (
        <header className="top-bar">
            {/* Mobile Sidebar Toggle */}
            <button className="mobile-menu-btn" onClick={onToggleSidebar}>
                <Menu size={24} />
            </button>

            {/* Search Bar - Centered */}
            <div className="top-bar-search">
                <SearchBar
                    onSearch={setSearchTerm}
                    onFilterChange={setFilters}
                    filters={filters}
                />
            </div>

            {/* Actions - Right */}
            <div className="top-bar-actions">
                <Link to="/upload" className="btn-upload-pill">
                    <UploadCloud size={18} />
                    <span>Upload</span>
                </Link>
                <UserProfile />
            </div>
        </header>
    );
}
