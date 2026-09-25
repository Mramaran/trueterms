/**
 * ChatPage.jsx — Main chat page
 */

import { useTranslation } from 'react-i18next'
import ChatWindow from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'

function ChatSkeleton() {
  return (
    <div className="chat-skeleton">
      {[1,2,3].map(i => (
        <div key={i} className={`skeleton-row ${i % 2 === 0 ? 'user' : 'ai'}`}>
          <div className="skeleton-avatar" />
          <div className="skeleton-lines">
            <div className="skeleton-line" style={{width: i % 2 === 0 ? '40%' : '80%'}} />
            <div className="skeleton-line" style={{width: i % 2 === 0 ? '30%' : '65%'}} />
            {i % 2 !== 0 && <div className="skeleton-line" style={{width:'50%'}} />}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ChatPage({ messages, loading, onSend, onStop, onEdit, onRegenerate, onVoiceContract }) {
  const { t } = useTranslation()

  return (
    <div className="chat-page">
      {messages.length === 0 ? (
        <div className="landing">
          <div className="landing-bg" />
          <div className="landing-content">
            {/* ACTUS branding */}
            <div className="landing-brand">
              <div className="landing-brand-logo">
                {/*
                  Pixel-grid icon — exact style from reference image:
                  diamond/rhombus shape made of rounded square dots,
                  gradient from soft lilac (top-left) to deep indigo (centre) to violet (bottom-right)
                  Dots fade out at edges, brightest in centre
                */}
<svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" style={{display:'block'}}>
                  <defs>
                    <linearGradient id="orbitGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stopColor="#4F52D0" />
                      <stop offset="100%" stopColor="#818CF8" />
                    </linearGradient>
                    <linearGradient id="ringGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                      <stop offset="0%" stopColor="#6366F1" stopOpacity="1" />
                      <stop offset="60%" stopColor="#818CF8" stopOpacity="0.6" />
                      <stop offset="100%" stopColor="#C7D2FE" stopOpacity="0.2" />
                    </linearGradient>
                  </defs>
                  {/* Outer precision ring */}
                  <circle cx="40" cy="40" r="37" stroke="url(#ringGrad)" strokeWidth="2" fill="none" />
                  {/* Inner subtle ring */}
                  <circle cx="40" cy="40" r="30" stroke="#6366F1" strokeWidth="0.75" fill="none" strokeOpacity="0.25" strokeDasharray="3 5" />
                  {/* Orbit node — top (12 o'clock) */}
                  <circle cx="40" cy="3" r="3.5" fill="#6366F1" />
                  {/* Orbit node — bottom right */}
                  <circle cx="71" cy="56" r="2.5" fill="#818CF8" fillOpacity="0.7" />
                  {/* Orbit node — bottom left */}
                  <circle cx="9" cy="56" r="2.5" fill="#818CF8" fillOpacity="0.7" />
                  {/* TT monogram — bold, centered */}
                  <text
                    x="40" y="47"
                    textAnchor="middle"
                    fontFamily="'Poppins', 'Inter', sans-serif"
                    fontSize="24"
                    fontWeight="800"
                    letterSpacing="1"
                    fill="url(#orbitGrad)"
                  >TT</text>
                </svg>
                <span className="landing-brand-text">TrueTerms</span>
              </div>
              <span className="landing-brand-tagline">FINANCE SPEAKS ONE LANGUAGE</span>
            </div>

            <h1 className="landing-title">
              Learning ACTUS,{' '}
              <span className="landing-title-accent">together.</span>
            </h1>



          </div>
        </div>
      ) : (
        <ChatWindow messages={messages} loading={loading} onEdit={onEdit} onRegenerate={onRegenerate} />
      )}

      <div className="input-bar">
        <ChatInput
          onSend={onSend}
          loading={loading}
          messages={messages}
          onStop={onStop}
          onVoiceContract={(contract, params) => {
            const msg = `I just generated a ${contract.contractType} contract via voice. Please explain it and confirm all parameters are correct:\n\n\`\`\`json\n${JSON.stringify(contract, null, 2)}\n\`\`\``
            onSend(msg)
          }}
        />
      </div>
    </div>
  )
}
