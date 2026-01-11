import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Settings, User } from 'lucide-react';
import { Link } from 'react-router-dom';
import './UserProfile.css';

export default function UserProfile() {
    const { user, logout } = useAuth();
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Close dropdown on outside click
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const getInitials = (name) => {
        return name ? name.charAt(0).toUpperCase() : 'U';
    };

    return (
        <div className="user-profile" ref={dropdownRef}>
            <button
                className="profile-trigger"
                onClick={() => setIsOpen(!isOpen)}
                title={user?.name || 'User Profile'}
            >
                {user?.picture ? (
                    <img src={user.picture} alt="Profile" className="profile-avatar" />
                ) : (
                    <div className="profile-initials">
                        {getInitials(user?.name)}
                    </div>
                )}
            </button>

            {isOpen && (
                <div className="profile-dropdown">
                    <div className="dropdown-header">
                        <div className="user-info">
                            <span className="user-name">{user?.name}</span>
                            <span className="user-email">{user?.email}</span>
                        </div>
                    </div>

                    <div className="dropdown-divider" />

                    <Link to="/settings" className="dropdown-item" onClick={() => setIsOpen(false)}>
                        <Settings size={16} />
                        <span>Settings</span>
                    </Link>

                    <div className="dropdown-divider" />

                    <button className="dropdown-item danger" onClick={logout}>
                        <LogOut size={16} />
                        <span>Log Out</span>
                    </button>
                </div>
            )}
        </div>
    );
}
