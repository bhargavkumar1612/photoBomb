import { NavLink, Link } from 'react-router-dom';
import {
    Image,
    Search,
    Share2,
    FolderHeart,
    Users,
    MapPin,
    Trash2,
    Settings,
    Camera,
    PawPrint,
    Hash,
    Mountain
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import './Sidebar.css';

export default function Sidebar({ isOpen, onClose }) {
    const { user } = useAuth();
    const navItems = [
        { path: '/', icon: <Image size={20} />, label: 'Photos' },
        { path: '/explore', icon: <Search size={20} />, label: 'Explore' },
        { path: '/sharing', icon: <Share2 size={20} />, label: 'Sharing' },
        { path: '/albums', icon: <FolderHeart size={20} />, label: 'Albums' },
        { path: '/places', icon: <MapPin size={20} />, label: 'Places' },
        { path: '/people', icon: <Users size={20} />, label: 'People' },
        { path: '/animals', icon: <PawPrint size={20} />, label: 'Animals' },
        { path: '/hashtags', icon: <Hash size={20} />, label: 'Hashtags' },
        { path: '/trash', icon: <Trash2 size={20} />, label: 'Trash' },
    ];

    return (
        <>
            {/* Mobile Overlay */}
            <div
                className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
                onClick={onClose}
            />

            <aside className={`sidebar ${isOpen ? '' : 'collapsed'}`}>
                {/* Logo */}
                <Link to="/" className="sidebar-logo">
                    <div className="sidebar-logo-icon">
                        <Camera color="#4f46e5" size={28} />
                    </div>
                    <span className="sidebar-logo-text">PhotoBomb</span>
                </Link>

                {/* Navigation */}
                <nav className="sidebar-nav">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            onClick={() => window.innerWidth <= 768 && onClose()}
                        >
                            <span className="nav-item-icon">{item.icon}</span>
                            <span className="nav-item-text">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Footer / Settings */}
                <div className="sidebar-footer">
                    {user?.is_admin && (
                        <NavLink
                            to="/admin"
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            onClick={() => window.innerWidth <= 768 && onClose()}
                        >
                            <span className="nav-item-icon"><Mountain size={20} /></span>
                            <span className="nav-item-text">Admin</span>
                        </NavLink>
                    )}
                    <NavLink
                        to="/settings"
                        className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                        onClick={() => window.innerWidth <= 768 && onClose()}
                    >
                        <span className="nav-item-icon"><Settings size={20} /></span>
                        <span className="nav-item-text">Settings</span>
                    </NavLink>
                </div>
            </aside>
        </>
    );
}
