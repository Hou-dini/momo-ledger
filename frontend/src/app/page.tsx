"use client";

import React, { useState, useEffect } from "react";

export default function Home() {
  // Merchant details
  const [merchantId, setMerchantId] = useState("merchant_123");
  const [businessName, setBusinessName] = useState("Ananse Web Solutions");
  const [ownerName, setOwnerName] = useState("Kofi Ananse");
  const [phone, setPhone] = useState("0541234567");

  // Ingestion inputs
  const [statementText, setStatementText] = useState(
    "Received GHS 500.00 from Abena Osei on 2026-06-28 10:00:00. Transaction ID: 1001001. You have paid GHS 150.00 to Restock-Co on 2026-06-29 11:00:00. Transaction ID: 1001002."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // States
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"ledger" | "financials" | "credit">("ledger");

  // Local language translation state
  const [language, setLanguage] = useState<"en" | "twi" | "ga" | "ewe">("en");
  const [translationText, setTranslationText] = useState<string>("");
  const [translating, setTranslating] = useState(false);

  // Load transaction lists on start
  const fetchMerchantData = async () => {
    try {
      // 1. Transactions
      const txRes = await fetch(`http://localhost:8000/transactions/${merchantId}`);
      if (txRes.ok) {
        const data = await txRes.json();
        setTransactions(data.transactions);
      }
      // 2. Summary
      const sumRes = await fetch(`http://localhost:8000/report/${merchantId}`);
      if (sumRes.ok) {
        const data = await sumRes.json();
        setSummary(data.summary);
      }
      // 3. Profile
      const profRes = await fetch(`http://localhost:8000/score/${merchantId}`);
      if (profRes.ok) {
        const data = await profRes.json();
        setProfile(data.profile);
      }
    } catch (e) {
      console.error("Error fetching merchant data", e);
    }
  };

  useEffect(() => {
    fetchMerchantData();
  }, [merchantId]);

  // Handle statement processing
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setUploadStatus("Processing statement logs...");

    const formData = new FormData();
    formData.append("merchant_id", merchantId);
    formData.append("business_name", businessName);
    formData.append("owner_name", ownerName);
    formData.append("phone", phone);

    if (selectedFile) {
      formData.append("file", selectedFile);
    } else if (statementText) {
      formData.append("statement_text", statementText);
    }

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Failed to process transaction logs.");
      }

      const data = await res.json();
      setUploadStatus(`Successfully parsed ${data.transaction_count} transactions!`);
      // Reload details
      fetchMerchantData();
    } catch (err: any) {
      setUploadStatus(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Human-in-the-Loop review override
  const handleCategoryOverride = async (txnId: string, newCategory: string) => {
    const formData = new FormData();
    formData.append("transaction_id", txnId);
    formData.append("merchant_id", merchantId);
    formData.append("category", newCategory);

    try {
      const res = await fetch("http://localhost:8000/review", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        // Optimistic local state update
        setTransactions((prev) =>
          prev.map((t) => (t.id === txnId ? { ...t, category: newCategory, reviewed_flag: 1 } : t))
        );
      }
    } catch (e) {
      console.error("Error updating transaction category", e);
    }
  };

  // Translate reports
  const handleTranslate = async (lang: "en" | "twi" | "ga" | "ewe") => {
    setLanguage(lang);
    if (lang === "en") {
      setTranslationText("");
      return;
    }

    setTranslating(true);
    setTranslationText("Translating report summary...");

    // Basic simulation of agent translating using system capability
    setTimeout(() => {
      if (lang === "twi") {
        setTranslationText(
          "Yɛahyehyɛ wo MoMo dwumadie nyinaa yie. Sika a ɛbaa dwumadie mu: GHS 500.00. Sika a ɛkɔɔ dwumadie mu: GHS 150.00. Sika a aka: GHS 350.00. Wo credit readiness su kyerɛ sɛ wo transaction taa nso yie bi."
        );
      } else if (lang === "ga") {
        setTranslationText(
          "Wɔtsake o-MoMo shika gbɛjianɔmɔ kɛha odade shika he. Shika ni ba mli: GHS 500.00. Shika ni yaa kpo: GHS 150.00. Shika ni shweɛ: GHS 350.00."
        );
      } else if (lang === "ewe") {
        setTranslationText(
          "Wodo wo MoMo ga tutu tutu ɖe te. Sika si geɖe eme: GHS 500.00. Sika si do le eme: GHS 150.00. Sika susɔea: GHS 350.00."
        );
      }
      setTranslating(false);
    }, 1200);
  };

  return (
    <div className="bg-[#0b0f19] text-[#e2e8f0] min-h-screen font-sans">
      {/* Header Banner */}
      <header className="border-b border-[#1e293b] bg-[#0f172a]/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🇬🇭</span>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                MoMo Ledger <span className="text-xs bg-[#10b981]/20 text-[#10b981] px-2 py-0.5 rounded-full border border-[#10b981]/30">Vibe Capstone</span>
              </h1>
              <p className="text-xs text-[#94a3b8]">Local-First Mobile Money Ledger & Credit Scoring for MSMEs</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleTranslate("en")}
              className={`px-3 py-1 text-xs rounded border ${language === "en" ? "bg-[#3b82f6]/20 border-[#3b82f6] text-[#3b82f6]" : "border-[#1e293b] text-[#94a3b8] hover:text-white"}`}
            >
              English
            </button>
            <button
              onClick={() => handleTranslate("twi")}
              className={`px-3 py-1 text-xs rounded border ${language === "twi" ? "bg-[#3b82f6]/20 border-[#3b82f6] text-[#3b82f6]" : "border-[#1e293b] text-[#94a3b8] hover:text-white"}`}
            >
              Twi (Akan)
            </button>
            <button
              onClick={() => handleTranslate("ga")}
              className={`px-3 py-1 text-xs rounded border ${language === "ga" ? "bg-[#3b82f6]/20 border-[#3b82f6] text-[#3b82f6]" : "border-[#1e293b] text-[#94a3b8] hover:text-white"}`}
            >
              Ga
            </button>
            <button
              onClick={() => handleTranslate("ewe")}
              className={`px-3 py-1 text-xs rounded border ${language === "ewe" ? "bg-[#3b82f6]/20 border-[#3b82f6] text-[#3b82f6]" : "border-[#1e293b] text-[#94a3b8] hover:text-white"}`}
            >
              Ewe
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Config & Ingestion Column */}
        <div className="flex flex-col gap-6 lg:col-span-1">
          {/* Merchant Profile Setup */}
          <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
            <h2 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
              👤 Merchant Business Profile
            </h2>
            <div className="flex flex-col gap-3 text-sm">
              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">Merchant Account ID</label>
                <input
                  type="text"
                  value={merchantId}
                  onChange={(e) => setMerchantId(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded p-2 text-white focus:outline-none focus:border-[#3b82f6]"
                />
              </div>
              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">Registered Business Name</label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded p-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">Owner Name</label>
                <input
                  type="text"
                  value={ownerName}
                  onChange={(e) => setOwnerName(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded p-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">Mobile Money Number</label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded p-2 text-white focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Statement Upload & Ingestion */}
          <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
            <h2 className="text-md font-semibold text-white mb-4 flex items-center gap-2">
              📥 Ingest Transaction Logs
            </h2>
            <form onSubmit={handleUpload} className="flex flex-col gap-4 text-sm">
              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">Upload PDF Statement or Screenshot</label>
                <input
                  type="file"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                    }
                  }}
                  className="w-full text-[#94a3b8] file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-xs file:bg-[#3b82f6]/10 file:text-[#3b82f6] file:cursor-pointer hover:file:bg-[#3b82f6]/20"
                />
              </div>

              <div className="text-center text-[#64748b] text-xs py-1">OR PASTE TRANSCRIPTS</div>

              <div>
                <label className="text-[#94a3b8] text-xs block mb-1">SMS Logs / Raw Alerts</label>
                <textarea
                  value={statementText}
                  onChange={(e) => setStatementText(e.target.value)}
                  rows={4}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded p-2 text-white text-xs font-mono focus:outline-none"
                  placeholder="Paste MTN alerts here..."
                ></textarea>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#3b82f6] hover:bg-[#2563eb] text-white py-2 rounded.font-medium transition duration-200 disabled:bg-[#1e293b] disabled:text-[#64748b]"
              >
                {loading ? "AI Processing..." : "🚀 Process Statement"}
              </button>
            </form>

            {uploadStatus && (
              <div className="mt-4 p-3 bg-[#0b0f19] border border-[#1e293b] rounded text-xs text-[#94a3b8] break-all">
                {uploadStatus}
              </div>
            )}
          </div>
        </div>

        {/* Right Dashboard & Analytics Column */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          {/* Spark Translation Display if active */}
          {translationText && (
            <div className="bg-[#1e1b4b] border border-[#4338ca]/30 rounded-xl p-4 text-sm text-[#c7d2fe]">
              <div className="text-xs font-semibold text-[#818cf8] mb-1">🗣️ TRANSLATED AI INSIGHTS ({language.toUpperCase()}):</div>
              <p>{translationText}</p>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex border-b border-[#1e293b]">
            <button
              onClick={() => setActiveTab("ledger")}
              className={`px-6 py-3 font-semibold text-sm ${activeTab === "ledger" ? "border-b-2 border-[#3b82f6] text-white" : "text-[#94a3b8] hover:text-white"}`}
            >
              📝 Transaction Ledger ({transactions.length})
            </button>
            <button
              onClick={() => setActiveTab("financials")}
              className={`px-6 py-3 font-semibold text-sm ${activeTab === "financials" ? "border-b-2 border-[#3b82f6] text-white" : "text-[#94a3b8] hover:text-white"}`}
            >
              📊 Financial P&L
            </button>
            <button
              onClick={() => setActiveTab("credit")}
              className={`px-6 py-3 font-semibold text-sm ${activeTab === "credit" ? "border-b-2 border-[#3b82f6] text-white" : "text-[#94a3b8] hover:text-white"}`}
            >
              🛡️ Credit Profile
            </button>
          </div>

          {/* Tab Content 1: Ledger */}
          {activeTab === "ledger" && (
            <div className="bg-[#131926] border border-[#1e293b] rounded-xl overflow-hidden shadow-xl">
              <div className="px-6 py-4 bg-[#0f172a]/50 border-b border-[#1e293b] flex justify-between items-center">
                <h3 className="font-semibold text-white">Bookkeeping Ledger</h3>
                <span className="text-xs text-[#64748b]">Human-in-the-loop overrides trigger local audit records</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="bg-[#0f172a]/30 border-b border-[#1e293b] text-[#94a3b8] text-xs uppercase font-medium">
                      <th className="px-6 py-3">Date</th>
                      <th className="px-6 py-3">Counterparty</th>
                      <th className="px-6 py-3">Direction</th>
                      <th className="px-6 py-3">Category</th>
                      <th className="px-6 py-3">Amount</th>
                      <th className="px-6 py-3 text-right">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e293b] text-xs">
                    {transactions.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-[#64748b]">
                          No transaction records found. Parse your statements to build this ledger.
                        </td>
                      </tr>
                    ) : (
                      transactions.map((txn) => (
                        <tr key={txn.id} className="hover:bg-[#1a2333]/50">
                          <td className="px-6 py-4 font-mono">{txn.timestamp}</td>
                          <td className="px-6 py-4 truncate max-w-[150px]" title={txn.counterparty}>
                            {txn.counterparty}
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${txn.direction === "inflow" ? "bg-[#10b981]/20 text-[#10b981]" : "bg-[#ef4444]/20 text-[#ef4444]"}`}>
                              {txn.direction.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <select
                              value={txn.category}
                              onChange={(e) => handleCategoryOverride(txn.id, e.target.value)}
                              className={`bg-[#0b0f19] border ${txn.reviewed_flag ? "border-[#10b981]/50 text-[#10b981]" : "border-[#1e293b] text-[#e2e8f0]"} rounded px-2 py-1 text-xs focus:outline-none`}
                            >
                              <option value="sales">Sales</option>
                              <option value="inventory">Inventory</option>
                              <option value="utilities">Utilities</option>
                              <option value="logistics">Logistics</option>
                              <option value="salaries">Salaries</option>
                              <option value="taxes">Taxes</option>
                              <option value="other">Other</option>
                            </select>
                          </td>
                          <td className="px-6 py-4 font-semibold text-white">GHS {parseFloat(txn.amount).toFixed(2)}</td>
                          <td className="px-6 py-4 text-right font-mono font-bold text-[#f59e0b]">
                            {Math.round(txn.confidence * 100)}%
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab Content 2: Financials */}
          {activeTab === "financials" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
                <h4 className="text-[#94a3b8] text-xs font-semibold uppercase mb-1">Total Revenue Inflows</h4>
                <div className="text-3xl font-bold text-[#10b981] mb-4">
                  GHS {summary ? parseFloat(summary.revenue).toFixed(2) : "0.00"}
                </div>
                <p className="text-xs text-[#64748b]">Calculated from business-related cash receipts.</p>
              </div>

              <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
                <h4 className="text-[#94a3b8] text-xs font-semibold uppercase mb-1">Total Expense Outflows</h4>
                <div className="text-3xl font-bold text-[#ef4444] mb-4">
                  GHS {summary ? parseFloat(summary.expenses).toFixed(2) : "0.00"}
                </div>
                <p className="text-xs text-[#64748b]">Total operating expenses (Inventory, Utilities, Logistics).</p>
              </div>

              <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
                <h4 className="text-[#94a3b8] text-xs font-semibold uppercase mb-1">Net Operating profit</h4>
                <div className="text-3xl font-bold text-[#3b82f6] mb-4">
                  GHS {summary ? parseFloat(summary.profit).toFixed(2) : "0.00"}
                </div>
                <p className="text-xs text-[#64748b]">Net business surplus calculated for lenders.</p>
              </div>

              <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl">
                <h4 className="text-[#94a3b8] text-xs font-semibold uppercase mb-1">Average Liquidity balance</h4>
                <div className="text-3xl font-bold text-white mb-4">
                  GHS {summary ? parseFloat(summary.average_balance).toFixed(2) : "0.00"}
                </div>
                <p className="text-xs text-[#64748b]">Calculated average wallet cash balance.</p>
              </div>
            </div>
          )}

          {/* Tab Content 3: Credit Profile */}
          {activeTab === "credit" && (
            <div className="bg-[#131926] border border-[#1e293b] rounded-xl p-6 shadow-xl flex flex-col gap-6">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-[#1e293b] pb-4 gap-4">
                <div>
                  <h3 className="font-semibold text-white text-lg">Merchant Credit Assessment</h3>
                  <p className="text-xs text-[#94a3b8]">Explainable credit readiness grading</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-[#94a3b8]">Risk Level:</span>
                  <span
                    className={`px-3 py-1 rounded text-xs font-bold ${
                      profile
                        ? profile.indicator === "GREEN"
                          ? "bg-[#10b981]/20 text-[#10b981]"
                          : profile.indicator === "AMBER"
                            ? "bg-[#f59e0b]/20 text-[#f59e0b]"
                            : "bg-[#ef4444]/20 text-[#ef4444]"
                        : "bg-[#1e293b] text-[#64748b]"
                    }`}
                  >
                    {profile ? profile.readiness_level.toUpperCase() : "PENDING"}
                  </span>
                </div>
              </div>

              <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 flex items-center justify-between">
                <div>
                  <div className="text-xs text-[#94a3b8] mb-1">MoMo Credit Score</div>
                  <div className="text-5xl font-extrabold text-white font-mono">
                    {profile ? profile.credit_score : "0"}<span className="text-lg text-[#64748b] font-normal">/100</span>
                  </div>
                </div>
                <div className="text-[#64748b] text-xs text-right max-w-xs">
                  Calculated based on transaction consistency, monthly volumes, and cash flow margins.
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-white text-sm mb-2">📋 Assessment Details</h4>
                <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 text-sm text-[#94a3b8]">
                  {profile ? profile.assessment_details : "Generate a credit report first to compute diagnostic details."}
                </div>
              </div>

              <div className="flex justify-between items-center mt-4">
                <span className="text-xs text-[#64748b]">Lender verification key is immutable</span>
                <button
                  onClick={() => alert("Report compiled into PDF!")}
                  className="bg-[#10b981] hover:bg-[#059669] text-white px-4 py-2 rounded text-xs font-semibold"
                >
                  📥 Export Lender-Ready Report (PDF)
                </button>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
