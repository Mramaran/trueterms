/**
 * ArchivePage.jsx
 */

export default function ArchivePage() {
  return (
    <div className="page">
      <div className="page-header-simple">
        <h1 className="page-title">Archive</h1>
        <p className="page-sub">Your archived conversations</p>
      </div>
      <div className="empty-state">
        <h2>No Archived Chats</h2>
        <p>Archived conversations will appear here.</p>
      </div>
    </div>
  )
}
