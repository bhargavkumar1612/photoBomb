import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null)
    const [loading, setLoading] = useState(true)
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    useEffect(() => {
        // Check for existing token on mount
        const token = localStorage.getItem('access_token')
        if (token) {
            // Verify token by fetching user
            api.get('/auth/me')
                .then(response => {
                    setUser(response.data)
                    setLoading(false)
                })
                .catch(() => {
                    // Token invalid, clear it
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    setLoading(false)
                })
        } else {
            setLoading(false)
        }
    }, [])

    const login = async (email, password) => {
        const response = await api.post('/auth/login', { email, password })
        const { access_token, refresh_token, user: userData } = response.data

        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)
        setUser(userData)

        navigate('/')
    }

    const register = async (email, password, full_name) => {
        const response = await api.post('/auth/register', { email, password, full_name })
        const { access_token, refresh_token, user: userData } = response.data

        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)
        setUser(userData)

        navigate('/')
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setUser(null)
        // Clear all cached data (photos, albums, etc.) so next user starts fresh
        queryClient.removeQueries()
        navigate('/login')
    }

    return (
        <AuthContext.Provider value={{ user, setUser, login, register, logout, loading }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context
}
