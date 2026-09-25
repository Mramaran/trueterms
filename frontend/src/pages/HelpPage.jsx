/**
 * HelpPage.jsx
 * =============
 * FAQ & Help page for TrueTerms
 */

import { useState } from 'react'
import { HelpCircle, ChevronDown, ChevronUp, Search, BookOpen, MessageSquare, Zap, FileText } from 'lucide-react'

const FAQ_SECTIONS = [
  {
    section: 'Getting Started',
    icon: <Zap size={18} />,
    color: '#2563eb',
    faqs: [
      {
        q: 'What is TrueTerms?',
        a: 'TrueTerms is an AI-powered assistant that helps you understand and generate ACTUS financial contracts. You can ask questions in English, Tamil, or Tanglish, and it will answer based on the ACTUS standard documentation.',
      },
      {
        q: 'How do I start a conversation?',
        a: 'Click "New Chat" in the sidebar, then type your question in the input box at the bottom and press Enter. You can also click one of the quick action buttons on the home screen.',
      },
      {
        q: 'What languages can I use?',
        a: 'You can ask questions in English, Tamil, or Tanglish (Tamil + English mixed). The AI understands all three! You can also change the UI language using the Language option in Settings — 12 languages are supported.',
      },
      {
        q: 'Can I use voice input?',
        a: 'Yes! Click the microphone 🎤 icon in the chat input. It supports Tamil, English, and Tanglish voice input. Click it again to stop listening.',
      },
    ],
  },
  {
    section: 'ACTUS Contracts',
    icon: <FileText size={18} />,
    color: '#16a34a',
    faqs: [
      {
        q: 'What is a PAM contract?',
        a: 'PAM (Principal At Maturity) is the most basic ACTUS contract type. The principal is paid back at maturity while interest is paid periodically. Example: a bullet loan or bond.',
      },
      {
        q: 'What is an ANN contract?',
        a: 'ANN (Annuity) is a contract where equal periodic payments cover both principal and interest. The outstanding principal decreases over time. Example: a mortgage.',
      },
      {
        q: 'What is a risk factor?',
        a: 'A risk factor in ACTUS represents an external market variable like an interest rate curve or yield curve that affects the contract cash flows. When you generate a contract with risk factor enabled, it includes market rate references.',
      },
      {
        q: 'What are the 32 ACTUS contract types?',
        a: 'ACTUS defines 32 contract types grouped into families: Basic/Fixed Income (PAM, ANN, LAM, NAM etc.), Basic/Ownership (STK, COM), Combined/Symmetric (SWAPS, FXOUT), Combined/Asymmetric (OPTNS, FUTUR, CAPFL), Securitization (SCRCR, SCRMR), and Credit Enhancement (CEG, CEC, MAR, REP).',
      },
      {
        q: 'What is nominalInterestRate?',
        a: 'nominalInterestRate is the stated interest rate of a contract before adjustments for compounding or fees. It is one of the key ACTUS contract terms used to calculate interest payments.',
      },
    ],
  },
  {
    section: 'Contract Generator',
    icon: <BookOpen size={18} />,
    color: '#9333ea',
    faqs: [
      {
        q: 'How do I generate a contract?',
        a: 'Go to "Contract Generator" in the sidebar. Select a contract type, toggle the risk factor if needed, optionally add requirements, then click Generate. The contract JSON will appear on the right.',
      },
      {
        q: 'What is the "with Risk Factor" toggle?',
        a: 'When enabled, the generated contract will include a market rate risk factor reference (yield curve or interest rate index). This is needed when you want to simulate how changing market rates affect the contract.',
      },
      {
        q: 'Can I download the generated contract?',
        a: 'Yes! After generating a contract, go to "Contract History" in the sidebar. There you can view, copy, or download any contract as a .json file.',
      },
      {
        q: 'What do I do with the generated JSON?',
        a: 'The generated JSON is ready to POST directly to an ACTUS server (e.g. the ACTUS Web Service at demo.actusfrf.org) to compute cash flow events for the contract.',
      },
    ],
  },
  {
    section: 'Chat & Features',
    icon: <MessageSquare size={18} />,
    color: '#ea580c',
    faqs: [
      {
        q: 'What do the Pipeline Info details mean?',
        a: 'Each AI response shows Pipeline Info (click the arrow to expand): Route tells you if the answer came from the local knowledge base (vectorstore) or web search. Grounded tells you if the answer was verified against source documents. Iterations shows how many times the AI refined the answer.',
      },
      {
        q: 'How do I attach a file to my question?',
        a: 'Click the + button in the chat input, then select "Add files or photos". You can attach .txt, .json, .pdf, .csv, or image files.',
      },
      {
        q: 'What are the Tools?',
        a: 'Click the 🔧 wrench icon (in the + menu or directly) to open Tools. You can use the Contract Validator to check if JSON is valid, the JSON Formatter to prettify/minify JSON, and the Share option to copy or download your conversation.',
      },
      {
        q: 'How do I switch between dark and light mode?',
        a: 'Click the moon/sun icon 🌙 in the top of the sidebar to toggle between dark and light mode. Your preference is saved automatically.',
      },
      {
        q: 'Why is the backend not responding?',
        a: 'Make sure the backend is running. Double-click start_uvicorn.bat in your project folder to start the API server on port 8000. The frontend needs the backend to answer questions.',
      },
    ],
  },
]

export default function HelpPage() {
  const [search, setSearch] = useState('')
  const [openItem, setOpenItem] = useState(null)

  const toggle = (key) => setOpenItem(openItem === key ? null : key)

  // Filter FAQs by search
  const filtered = FAQ_SECTIONS.map(section => ({
    ...section,
    faqs: section.faqs.filter(
      f =>
        f.q.toLowerCase().includes(search.toLowerCase()) ||
        f.a.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter(section => section.faqs.length > 0)

  return (
    <div className="page">
      <div className="page-header-simple">
        <h1 className="page-title">Help & FAQ</h1>
        <p className="page-sub">Everything you need to know about TrueTerms</p>
      </div>

      {/* Search */}
      <div className="search-bar help-search">
        <Search size={15} className="search-icon" />
        <input
          className="search-input"
          placeholder="Search questions..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && <span className="ref-count">{filtered.reduce((a, s) => a + s.faqs.length, 0)} results</span>}
      </div>

      {filtered.length === 0 && (
        <div className="empty-state">
          <HelpCircle size={40} className="empty-icon" strokeWidth={1} />
          <h2>No results found</h2>
          <p>Try a different search term</p>
        </div>
      )}

      {/* FAQ Sections */}
      <div className="help-sections">
        {filtered.map(section => (
          <div key={section.section} className="help-section">
            {/* Section header */}
            <div className="help-section-header" style={{ borderLeftColor: section.color }}>
              <span style={{ color: section.color }}>{section.icon}</span>
              <span className="help-section-title" style={{ color: section.color }}>{section.section}</span>
            </div>

            {/* FAQ items */}
            <div className="help-faq-list">
              {section.faqs.map((faq, i) => {
                const key = `${section.section}-${i}`
                const isOpen = openItem === key
                return (
                  <div key={key} className={`help-faq-item ${isOpen ? 'open' : ''}`}>
                    <button className="help-faq-question" onClick={() => toggle(key)}>
                      <span>{faq.q}</span>
                      {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    {isOpen && (
                      <div className="help-faq-answer">{faq.a}</div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
