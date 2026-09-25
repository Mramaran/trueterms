import { useState, useRef, useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer
} from "recharts";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_SECRET_KEY || "";
const headers = { "X-API-Key": API_KEY };

export default function XBRLImportPage() {
  // ── INPUT STATE ──
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);

  // ── ACTUS RUN STATE ──
  const [isRunning, setIsRunning] = useState(false);
  const [actusResult, setActusResult] = useState(null);

  // ── XBRL OUTPUT STATE ──
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [xbrlReport, setXbrlReport] = useState(null);
  const [activeTab, setActiveTab] = useState("table");
  const [activeTaxonomy, setActiveTaxonomy] = useState("both");

  const fileInputRef = useRef(null);

  // ── FILE HANDLING ──
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFileSelect(dropped);
  };

  const handleFileSelect = (f) => {
    if (!f) return;
    const ext = f.name.split(".").pop().toLowerCase();
    if (!["xml", "xbrl", "xsd", "htm", "html"].includes(ext)) {
      setError("Please upload an .xml, .xbrl, .xsd, .htm, or .html file");
      return;
    }
    setFile(f);
    setError(null);
    setExtractedData(null);
    setActusResult(null);
    setXbrlReport(null);
  };

  // ── STEP 1: EXTRACT FROM XBRL ──
  const handleExtract = async () => {
    if (!file) return;
    setIsExtracting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/parse-xbrl`, { method: "POST", headers, body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Extraction failed");
      setExtractedData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsExtracting(false);
    }
  };

  // ── STEP 2: RUN ON ACTUS SERVER ──
  const handleRunActus = async () => {
    if (!extractedData?.payload) return;
    setIsRunning(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/run-contract`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ contract: extractedData.payload }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "ACTUS run failed");
      setActusResult(data);
    } catch (e) {
      const msg = e.message || "";
      if (msg.includes("fetch") || msg.includes("network") || msg.includes("Failed to fetch")) {
        setError("Cannot reach backend (localhost:8000). Is uvicorn running?");
      } else if (msg.includes("ACTUS server") || msg.includes("timed out") || msg.includes("502") || msg.includes("504")) {
        setError("⚠️ ACTUS server at 34.203.247.32 is temporarily unreachable. Please try again in a moment.");
      } else {
        setError(msg);
      }
    } finally {
      setIsRunning(false);
    }
  };

  // ── STEP 3: GENERATE XBRL COMPLIANCE REPORT ──
  const handleGenerateReport = async () => {
    if (!actusResult) return;
    setIsGeneratingReport(true);
    setError(null);
    try {
      // ACTUS server returns: { success: true, results: [ [...events] ] }
      // results[0] is itself the events array
      const rawResults = actusResult?.results || [];
      const events =
        actusResult?.events ||
        actusResult?.cashFlows ||
        (Array.isArray(rawResults[0]) ? rawResults[0] : rawResults[0]?.events) ||
        rawResults.flat() ||
        [];
      const contracts = extractedData?.payload?.contracts || [];
      const contractInfo = contracts[0] || {};

      const res = await fetch(`${API_BASE}/generate-xbrl-report`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ actus_events: events, contract_info: contractInfo, taxonomy: activeTaxonomy }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Report generation failed");
      setXbrlReport(data);
      setActiveTab("table");
    } catch (e) {
      setError(e.message);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  // ── DOWNLOAD HELPER ──
  const downloadXML = (content, filename) => {
    const blob = new Blob([content], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const confidenceColor = (c) => (c >= 80 ? "#22c55e" : c >= 60 ? "#f59e0b" : "#ef4444");

  return (
    <div className="xbrl-page">
      {/* ── HEADER ── */}
      <div className="xbrl-header">
        <h1>📂 XBRL Import & Compliance Report</h1>
        <p className="xbrl-subtitle">
          Upload a bank XBRL filing → Extract contract fields → Run on ACTUS server → Generate XBRL compliance report
        </p>
        <div className="xbrl-pipeline">
          {[
            { label: "Upload XBRL", done: !!file, active: !file },
            { label: "Extract Fields", done: !!extractedData, active: !!file && !extractedData },
            { label: "Run ACTUS", done: !!actusResult, active: !!extractedData && !actusResult },
            { label: "XBRL Report", done: !!xbrlReport, active: !!actusResult && !xbrlReport },
          ].map((s, i) => (
            <>
              <div key={i} className={`pipeline-step ${s.done ? "done" : s.active ? "active" : ""}`}>
                <span className="step-num">{i + 1}</span>
                <span>{s.label}</span>
              </div>
              {i < 3 && <div className="pipeline-arrow">→</div>}
            </>
          ))}
        </div>
      </div>

      {/* ── UPLOAD ZONE ── */}
      <div
        className={`xbrl-dropzone ${isDragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input ref={fileInputRef} type="file" accept=".xml,.xbrl,.xsd,.htm,.html" style={{ display: "none" }}
          onChange={(e) => handleFileSelect(e.target.files[0])} />
        {file ? (
          <div className="file-selected">
            <span className="file-icon">📄</span>
            <span className="file-name">{file.name}</span>
            <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        ) : (
          <div className="dropzone-inner">
            <span className="upload-icon">📤</span>
            <p>Drag & drop your XBRL file here</p>
            <p className="dropzone-hint">or click to browse — supports .xml, .xbrl, .xsd, .htm (iXBRL)</p>
          </div>
        )}
      </div>

      {error && <div className="xbrl-error">⚠️ {error}</div>}

      {/* ── STEP 1 BUTTON ── */}
      {file && !extractedData && (
        <button className="xbrl-btn primary" onClick={handleExtract} disabled={isExtracting}>
          {isExtracting ? "⏳ Extracting Contract Fields..." : "🔍 Extract Contract Fields"}
        </button>
      )}

      {/* ── EXTRACTED FIELDS ── */}
      {extractedData && (
        <div className="xbrl-card">
          <div className="card-header">
            <h3>📋 Extracted Contract Fields</h3>
            <div className="badges">
              <span className="badge standard">{extractedData.standard_detected}</span>
              <span className="badge confidence" style={{ background: confidenceColor(extractedData.confidence) }}>
                {extractedData.confidence}% confidence
              </span>
              {extractedData.ready_to_run && <span className="badge ready">✅ Ready to Run</span>}
            </div>
          </div>
          {extractedData.suggested_contracts?.length > 0 && (
            <div className="fields-table-wrapper">
              <table className="fields-table">
                <thead><tr><th>Field</th><th>Value</th></tr></thead>
                <tbody>
                  {Object.entries(extractedData.suggested_contracts[0] || {}).map(([k, v]) => (
                    <tr key={k}>
                      <td className="field-key">{k}</td>
                      <td className="field-val">{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <button className="xbrl-btn primary" onClick={handleRunActus} disabled={isRunning}>
            {isRunning ? "⏳ Running on ACTUS Server..." : "🚀 Run on ACTUS Server"}
          </button>
        </div>
      )}

      {/* ── ACTUS RESULTS ── */}
      {actusResult && (
        <div className="xbrl-card">
          <div className="card-header">
            <h3>⚡ ACTUS Cash Flow Events</h3>
            <span className="badge ready">
              {(actusResult?.events || actusResult?.cashFlows ||
                (Array.isArray(actusResult?.results?.[0]) ? actusResult.results[0] : actusResult?.results?.[0]?.events) ||
                actusResult?.results?.flat() || []).length} events
            </span>
          </div>
          <div className="events-table-wrapper">
            <table className="fields-table">
              <thead>
                <tr><th>#</th><th>Event Type</th><th>Date</th><th>Amount</th><th>Currency</th></tr>
              </thead>
              <tbody>
                {(actusResult?.events || actusResult?.cashFlows || actusResult?.results?.[0]?.events || [])
                  .slice(0, 15).map((ev, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td><span className="event-badge">{ev.type || ev.eventType}</span></td>
                    <td>{String(ev.time || ev.eventDate || ev.date || "").slice(0, 10)}</td>
                    <td className={parseFloat(ev.payoff || ev.amount || 0) >= 0 ? "positive" : "negative"}>
                      {parseFloat(ev.payoff || ev.amount || 0).toFixed(2)}
                    </td>
                    <td>{ev.currency || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ── GENERATE REPORT SECTION ── */}
          <div className="generate-report-section">
            <h4>📊 Generate XBRL Compliance Report</h4>
            <p className="section-desc">
              Map ACTUS cash flow events to XBRL taxonomy concepts and generate a regulatory compliance report.
            </p>
            <div className="taxonomy-selector">
              <label>Select Taxonomy:</label>
              <div className="taxonomy-buttons">
                {[
                  { key: "both", label: "🌐 Both (IFRS + US-GAAP)", desc: "Complete report" },
                  { key: "ifrs", label: "🇮🇳 IFRS Only", desc: "India / EU / Asia" },
                  { key: "usgaap", label: "🇺🇸 US-GAAP Only", desc: "SEC / US" },
                ].map((t) => (
                  <button key={t.key}
                    className={`taxonomy-btn ${activeTaxonomy === t.key ? "selected" : ""}`}
                    onClick={() => setActiveTaxonomy(t.key)}>
                    <span>{t.label}</span>
                    <span className="tax-desc">{t.desc}</span>
                  </button>
                ))}
              </div>
            </div>
            <button className="xbrl-btn generate" onClick={handleGenerateReport} disabled={isGeneratingReport}>
              {isGeneratingReport ? "⏳ Generating XBRL Compliance Report..." : "📋 Generate XBRL Compliance Report"}
            </button>
          </div>
        </div>
      )}

      {/* ── XBRL COMPLIANCE REPORT OUTPUT ── */}
      {xbrlReport && (
        <div className="xbrl-card report-card">
          <div className="card-header">
            <h3>📊 XBRL Compliance Report</h3>
            <span className="badge ready">✅ Generated</span>
          </div>

          {/* Summary */}
          <div className="report-summary">
            {[
              { label: "Total Events", value: xbrlReport.summary.total_events },
              { label: "Event Types", value: xbrlReport.summary.event_types.join(", ") },
              { label: "Total Interest", value: `${xbrlReport.summary.currency} ${xbrlReport.summary.total_interest_payments.toLocaleString()}` },
              { label: "Principal Movements", value: `${xbrlReport.summary.currency} ${xbrlReport.summary.total_principal_movements.toLocaleString()}` },
              { label: "Taxonomies", value: xbrlReport.summary.taxonomies_mapped.join(" + ") },
              { label: "Reporting Date", value: xbrlReport.reporting_date },
            ].map((s) => (
              <div key={s.label} className="summary-item">
                <span className="summary-label">{s.label}</span>
                <span className="summary-value">{s.value}</span>
              </div>
            ))}
          </div>

          {/* Tabs */}
          <div className="report-tabs">
            {[
              { key: "table", label: "📋 Mapping Table" },
              { key: "ifrs", label: "🇮🇳 IFRS XML" },
              { key: "usgaap", label: "🇺🇸 US-GAAP XML" },
            ].map((t) => (
              <button key={t.key}
                className={`report-tab ${activeTab === t.key ? "active" : ""}`}
                onClick={() => setActiveTab(t.key)}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Mapping Table */}
          {activeTab === "table" && (
            <div className="tab-content">
              <p className="tab-desc">Each ACTUS event mapped to its IFRS and US-GAAP XBRL tag:</p>
              <div className="mapping-table-wrapper">
                <table className="mapping-table">
                  <thead>
                    <tr>
                      <th>ACTUS Event</th><th>Date</th><th>Amount</th>
                      <th>IFRS Tag</th><th>US-GAAP Tag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {xbrlReport.mapped_events.map((ev, i) => (
                      <tr key={i}>
                        <td><span className="event-badge">{ev.actus_event}</span></td>
                        <td>{String(ev.date || "").slice(0, 10)}</td>
                        <td className={ev.amount >= 0 ? "positive" : "negative"}>
                          {ev.currency} {ev.amount.toFixed(2)}
                        </td>
                        <td><span className="xbrl-tag ifrs-tag" title={ev.ifrs_description}>{ev.ifrs_tag}</span></td>
                        <td><span className="xbrl-tag usgaap-tag" title={ev.usgaap_description}>{ev.usgaap_tag}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* IFRS XML */}
          {activeTab === "ifrs" && (
            <div className="tab-content">
              <div className="xml-actions">
                <h4>🇮🇳 IFRS XBRL Instance Document</h4>
                <button className="xbrl-btn download"
                  onClick={() => downloadXML(xbrlReport.ifrs_xml, `actus_ifrs_report_${xbrlReport.reporting_date}.xml`)}>
                  ⬇️ Download IFRS XML
                </button>
              </div>
              <pre className="xml-preview">{xbrlReport.ifrs_xml}</pre>
            </div>
          )}

          {/* US-GAAP XML */}
          {activeTab === "usgaap" && (
            <div className="tab-content">
              <div className="xml-actions">
                <h4>🇺🇸 US-GAAP XBRL Instance Document</h4>
                <button className="xbrl-btn download"
                  onClick={() => downloadXML(xbrlReport.usgaap_xml, `actus_usgaap_report_${xbrlReport.reporting_date}.xml`)}>
                  ⬇️ Download US-GAAP XML
                </button>
              </div>
              <pre className="xml-preview">{xbrlReport.usgaap_xml}</pre>
            </div>
          )}

          {/* Download both */}
          <div className="download-both">
            <button className="xbrl-btn download-all" onClick={() => {
              downloadXML(xbrlReport.ifrs_xml, `actus_ifrs_report_${xbrlReport.reporting_date}.xml`);
              setTimeout(() => downloadXML(xbrlReport.usgaap_xml, `actus_usgaap_report_${xbrlReport.reporting_date}.xml`), 500);
            }}>
              ⬇️ Download Both Reports (IFRS + US-GAAP)
            </button>
          </div>
        </div>
      )}

      {/* ── CHARTS ── */}
      {xbrlReport && <XBRLCharts report={xbrlReport} />}
    </div>
  );
}

// ── COLORS ──
const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];

function XBRLCharts({ report }) {
  const events = report.mapped_events || [];

  // Chart 1: Cash flows grouped by month — exclude IED (too large, distorts scale)
  const barData = useMemo(() => {
    const grouped = {};
    events.forEach(ev => {
      if (ev.actus_event === 'IED') return; // skip initial disbursement
      const month = String(ev.date || "").slice(0, 7);
      if (!month) return;
      if (!grouped[month]) grouped[month] = { month, principal: 0, interest: 0 };
      const amt = Math.abs(parseFloat(ev.amount || 0));
      if (ev.actus_event === 'IP') grouped[month].interest  += amt;
      else                         grouped[month].principal += amt;
    });
    return Object.values(grouped); // show ALL months — no slice
  }, [events]);

  // Chart 2: Event type pie
  const pieData = useMemo(() => {
    const counts = {};
    events.forEach(ev => {
      const t = ev.actus_event || "OTHER";
      counts[t] = (counts[t] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [events]);

  // Chart 3: Interest payments over time
  const lineData = useMemo(() => {
    return events
      .filter(ev => ev.actus_event === "IP")
      .map(ev => ({ date: String(ev.date || "").slice(0, 7), interest: Math.abs(parseFloat(ev.amount || 0)) }))
      ; // show ALL interest events — no slice
  }, [events]);

  if (events.length === 0) return null;

  return (
    <div style={{ marginTop: 32 }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24, color: "var(--text-primary)" }}>
        📊 Cash Flow Visualizations
      </h2>

      {/* Chart 1: Bar — Cash Flows Over Time */}
      <div className="xbrl-card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 16, fontSize: 15, fontWeight: 600 }}>💰 Monthly Cash Flows (Principal + Interest)</h3>
        <p style={{ fontSize: 12, color: "#888", marginBottom: 12 }}>
          Monthly principal repayments vs interest payments (initial loan disbursement excluded for scale)
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={barData} margin={{ top: 5, right: 20, left: 20, bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d2d3d" />
            <XAxis dataKey="month" tick={{ fontSize: 10, fill: "#aaa" }}
              tickFormatter={(val) => val && val.slice(5,7) === '01' ? val.slice(0,4) : val.slice(5,7) === '07' ? 'Mid-'+val.slice(2,4) : ''}
              interval={0} />
            <YAxis tick={{ fontSize: 10, fill: "#aaa" }} />
            <Tooltip
              contentStyle={{ background: "#1e1e2e", border: "1px solid #3d3d4d", borderRadius: 8 }}
              labelStyle={{ color: "#ccc" }}
            />
            <Legend wrapperStyle={{ paddingTop: 16 }} />
            <Bar dataKey="principal" name="Principal Repaid" fill="#6366f1" radius={[3,3,0,0]} />
            <Bar dataKey="interest"  name="Interest Paid"   fill="#22c55e" radius={[3,3,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 2 + 3 side by side */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

        {/* Chart 2: Pie — Event Type Breakdown */}
        <div className="xbrl-card">
          <h3 style={{ marginBottom: 8, fontSize: 15, fontWeight: 600 }}>🥧 Event Type Breakdown</h3>
          <p style={{ fontSize: 12, color: "#888", marginBottom: 12 }}>
            Distribution of ACTUS event types
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" outerRadius={80}
                dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={true}
              >
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#1e1e2e", border: "1px solid #3d3d4d", borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Chart 3: Line — Interest Decreasing Over Time */}
        <div className="xbrl-card">
          <h3 style={{ marginBottom: 8, fontSize: 15, fontWeight: 600 }}>📉 Interest Payments Over Time</h3>
          <p style={{ fontSize: 12, color: "#888", marginBottom: 12 }}>
            Interest reduces as principal is repaid each month
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={lineData} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d2d3d" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#aaa" }}
                tickFormatter={(val) => val && val.slice(5,7) === '01' ? val.slice(0,4) : val.slice(5,7) === '07' ? 'Mid-'+val.slice(2,4) : ''}
                interval={0} />
              <YAxis tick={{ fontSize: 10, fill: "#aaa" }} />
              <Tooltip
                contentStyle={{ background: "#1e1e2e", border: "1px solid #3d3d4d", borderRadius: 8 }}
                labelStyle={{ color: "#ccc" }}
              />
              <Line type="monotone" dataKey="interest" stroke="#6366f1" strokeWidth={2}
                dot={false} name="Interest Payment" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
