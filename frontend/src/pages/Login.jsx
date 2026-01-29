import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { GoogleLogin } from '@react-oauth/google'
import api from '../services/api'
import './Auth.css'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const { login, setUser } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            await login(email, password)
        } catch (err) {
            setError(err.response?.data?.detail || 'Login failed. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleGoogleSuccess = async (credentialResponse) => {
        setError('')
        setLoading(true)

        try {
            const response = await api.post('/auth/google', {
                credential: credentialResponse.credential
            })

            const { access_token, refresh_token, user } = response.data

            // Store tokens
            localStorage.setItem('access_token', access_token)
            localStorage.setItem('refresh_token', refresh_token)

            // Update context and navigate
            setUser(user)
            navigate('/')
        } catch (err) {
            setError(err.response?.data?.detail || 'Google sign-in failed. Please try again.')
            setLoading(false)
        }
    }

    const handleGoogleError = () => {
        setError('Google sign-in failed. Please try again.')
    }

    return (
        <div className="auth-container">
            <div className="auth-card">
                <div className="auth-header">
                    <h1>PhotoBomb</h1>
                    <p>Sign in to your account</p>
                </div>

                {error && <div className="error-message">{error}</div>}

                {/* Google Sign-In Button */}
                <div className="google-signin-wrapper">
                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={handleGoogleError}
                        ux_mode="popup"
                        text="signin_with"
                        shape="rectangular"
                        logo_alignment="left"
                    />
                </div>

                <div className="divider">
                    <span>or</span>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">

                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            autoComplete="email"
                            placeholder="you@example.com"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                            placeholder="••••••••"
                        />
                    </div>

                    <button type="submit" className="btn-primary" disabled={loading}>
                        {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>
                        Don't have an account?{' '}
                        <Link to="/register">Sign up</Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
