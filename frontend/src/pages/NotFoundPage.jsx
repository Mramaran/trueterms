/**
 * NotFoundPage.jsx — 404 page
 */
import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="not-found-page">
      <div className="not-found-content">
        <div className="not-found-code">404</div>
        <h1 className="not-found-title">Page not found</h1>
        <p className="not-found-sub">The page you're looking for doesn't exist or was moved.</p>
        <button className="btn-primary" onClick={() => navigate('/')}>
          ← Back to Chat
        </button>
      </div>
    </div>
  )
}
