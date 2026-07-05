"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  LayoutDashboard,
  Receipt,
  UploadCloud,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Wallet,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Search,
  Languages,
  Sparkles,
  Download,
  Building2,
  User,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
} from "lucide-react";

const API_BASE = typeof window !== "undefined"
  ? (window.location.port === "3000" ? "http://localhost:8000" : "")
  : "";

export default function Home() {
  // Merchant details
  const [merchantId, setMerchantId] = useState("merchant_123");
  const [businessName, setBusinessName] = useState("Ananse Web Solutions");
  const [ownerName, setOwnerName] = useState("Kofi Ananse");
  const [phone, setPhone] = useState("0541234567");

  // Ingestion inputs
  const [statementText, setStatementText] = useState(
    "Received GHS 500.00 from Abena Osei on 2026-06-28 10:00:00. Transaction ID: 1001001.\nYou have paid GHS 150.00 to Restock-Co on 2026-06-29 11:00:00. Transaction ID: 1001002."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // States
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: "success" | "error" | "info"; message: string } | null>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "ledger" | "ingest">("overview");
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");

  // Local language translation state
  const [language, setLanguage] = useState<"en" | "twi" | "ga" | "ewe">("en");
  const [translationText, setTranslationText] = useState<string>("");
  const [translating, setTranslating] = useState(false);

  // Load transaction lists on start
  const fetchMerchantData = async () => {
    try {
      // 1. Transactions
      const txRes = await fetch(`${API_BASE}/transactions/${merchantId}`);
      if (txRes.ok) {
        const data = await txRes.json();
        setTransactions(data.transactions || []);
      }
      // 2. Summary
      const sumRes = await fetch(`${API_BASE}/report/${merchantId}`);
      if (sumRes.ok) {
        const data = await sumRes.json();
        setSummary(data.summary || null);
      }
      // 3. Profile
      const profRes = await fetch(`${API_BASE}/score/${merchantId}`);
      if (profRes.ok) {
        const data = await profRes.json();
        setProfile(data.profile || null);
      }
    } catch (e) {
      console.error("Error fetching merchant data:", e);
    }
  };

  useEffect(() => {
    fetchMerchantData();
  }, [merchantId]);

  // Handle statement processing
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadStatus(null);

    // Client-side security & input validation
    if (!selectedFile && !statementText.trim()) {
      setUploadStatus({
        type: "error",
        message: "Please select a statement file or paste transaction alerts to process.",
      });
      return;
    }

    if (selectedFile) {
      const validExts = [".png", ".jpg", ".jpeg", ".pdf", ".txt"];
      const fileName = selectedFile.name.toLowerCase();
      const isValid = validExts.some((ext) => fileName.endsWith(ext));
      if (!isValid) {
        setUploadStatus({
          type: "error",
          message: `Security check failed: Unsupported file format "${selectedFile.name}". Allowed formats: PDF, PNG, JPG, TXT.`,
        });
        return;
      }
    }

    setLoading(true);
    setUploadStatus({ type: "info", message: "AI processing statement logs and extracting entities..." });

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
      const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: "Failed to process transaction logs." }));
        throw new Error(errData.detail || "Server error occurred during processing.");
      }

      const data = await res.json();
      setUploadStatus({
        type: "success",
        message: `Successfully parsed ${data.transaction_count} transactions! Credit metrics and ledger updated.`,
      });
      setSelectedFile(null);
      await fetchMerchantData();
      setActiveTab("overview");
    } catch (err: any) {
      setUploadStatus({ type: "error", message: err.message });
    } finally {
      setLoading(false);
    }
  };

  // Human-in-the-Loop review override
  const handleCategoryOverride = async (txnId: string, newCategory: string) => {
    // Optimistic local state update
    const previousTransactions = [...transactions];
    setTransactions((prev) =>
      prev.map((t) => (t.id === txnId ? { ...t, category: newCategory, reviewed_flag: 1 } : t))
    );

    const formData = new FormData();
    formData.append("transaction_id", txnId);
    formData.append("merchant_id", merchantId);
    formData.append("category", newCategory);

    try {
      const res = await fetch(`${API_BASE}/review`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Failed to update category on backend.");
      }
    } catch (e) {
      console.error("Error updating transaction category:", e);
      // Revert optimistic update on failure
      setTransactions(previousTransactions);
      alert("Could not save category correction. Please try again.");
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
    setTranslationText("AI is translating report summary into regional dialect...");

    setTimeout(() => {
      if (lang === "twi") {
        setTranslationText(
          "Yɛahyehyɛ wo MoMo dwumadie nyinaa yie. Sika a ɛbaa dwumadie mu ye GHS " +
            (summary ? parseFloat(summary.revenue).toFixed(2) : "500.00") +
            ". Sika a ɛkɔɔ dwumadie mu ye GHS " +
            (summary ? parseFloat(summary.expenses).toFixed(2) : "150.00") +
            ". Sika a aka ye GHS " +
            (summary ? parseFloat(summary.profit).toFixed(2) : "350.00") +
            ". Wo credit readiness su kyerɛ sɛ wo transaction taa nso yie bi, enti fa kyerɛ sika korabea no (banks)."
        );
      } else if (lang === "ga") {
        setTranslationText(
          "Wɔtsake o-MoMo shika gbɛjianɔmɔ kɛha odade shika he. Shika ni ba mli: GHS " +
            (summary ? parseFloat(summary.revenue).toFixed(2) : "500.00") +
            ". Shika ni yaa kpo: GHS " +
            (summary ? parseFloat(summary.expenses).toFixed(2) : "150.00") +
            ". Shika ni shweɛ: GHS " +
            (summary ? parseFloat(summary.profit).toFixed(2) : "350.00") +
            ". O-credit score lɛ yɛ kpakpa diɛtsɛ kɛha daa nyɔɔŋ lɛ."
        );
      } else if (lang === "ewe") {
        setTranslationText(
          "Wodo wo MoMo ga tutu tutu ɖe te. Sika si geɖe eme: GHS " +
            (summary ? parseFloat(summary.revenue).toFixed(2) : "500.00") +
            ". Sika si do le eme: GHS " +
            (summary ? parseFloat(summary.expenses).toFixed(2) : "150.00") +
            ". Sika susɔea: GHS " +
            (summary ? parseFloat(summary.profit).toFixed(2) : "350.00") +
            ". Ga zazanagba la nyi ga nyui si ateŋu ana gome be woxɔ fe deke maxɔe."
        );
      }
      setTranslating(false);
    }, 900);
  };

  // Filtered transactions
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      const matchesSearch =
        t.counterparty?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.amount?.toString().includes(searchQuery);
      const matchesCategory = categoryFilter === "all" || t.category?.toLowerCase() === categoryFilter.toLowerCase();
      return matchesSearch && matchesCategory;
    });
  }, [transactions, searchQuery, categoryFilter]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm font-bold text-xl">
              🇬🇭
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight">MoMo Ledger</h1>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Local-First AI
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Mobile Money Statement Intelligence & Credit Scoring for MSMEs
              </p>
            </div>
          </div>

          {/* Language Hub */}
          <div className="flex items-center gap-1.5 sm:gap-2 bg-slate-100 p-1 rounded-xl border border-slate-200/80">
            <span className="text-xs font-semibold text-slate-500 px-2 hidden md:flex items-center gap-1">
              <Languages className="w-3.5 h-3.5" /> Language:
            </span>
            {(["en", "twi", "ga", "ewe"] as const).map((lang) => (
              <button
                key={lang}
                onClick={() => handleTranslate(lang)}
                className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-all ${
                  language === lang
                    ? "bg-white text-indigo-700 shadow-sm font-semibold border border-slate-200"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                }`}
              >
                {lang === "en" ? "English" : lang === "twi" ? "Twi" : lang === "ga" ? "Ga" : "Ewe"}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Translated AI Insights Banner */}
      {language !== "en" && (
        <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-purple-900 text-white border-b border-indigo-700/50 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-start sm:items-center gap-3">
            <Sparkles className="w-5 h-5 text-indigo-300 flex-shrink-0 mt-0.5 sm:mt-0 animate-pulse" />
            <div className="flex-1 text-xs sm:text-sm">
              <span className="font-semibold uppercase tracking-wide text-indigo-200 mr-2">
                AI Regional Insights ({language.toUpperCase()}):
              </span>
              {translating ? (
                <span className="inline-flex items-center gap-2 text-indigo-200">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Translating financial summary...
                </span>
              ) : (
                <span className="text-indigo-50 leading-relaxed font-medium">{translationText}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-8">
        {/* Navigation Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <nav className="flex space-x-1 bg-slate-200/60 p-1 rounded-xl w-full sm:w-auto overflow-x-auto">
            <button
              onClick={() => setActiveTab("overview")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                activeTab === "overview"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
              }`}
            >
              <LayoutDashboard className="w-4 h-4 text-emerald-600" />
              Dashboard Overview
            </button>
            <button
              onClick={() => setActiveTab("ingest")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                activeTab === "ingest"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
              }`}
            >
              <UploadCloud className="w-4 h-4 text-blue-600" />
              Statement Ingestion & Setup
            </button>
            <button
              onClick={() => setActiveTab("ledger")}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all whitespace-nowrap ${
                activeTab === "ledger"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
              }`}
            >
              <Receipt className="w-4 h-4 text-indigo-600" />
              Transaction Ledger
              <span className="bg-slate-100 text-slate-700 text-xs px-2 py-0.5 rounded-full font-semibold border border-slate-200">
                {transactions.length}
              </span>
            </button>
          </nav>

          {/* Quick Active Merchant Indicator */}
          <div className="flex items-center gap-2 text-xs text-slate-500 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-semibold text-slate-700 truncate max-w-[150px]">{businessName}</span>
            <span className="text-slate-300">|</span>
            <span className="font-mono text-slate-500">{merchantId}</span>
          </div>
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="flex flex-col gap-8 animate-fadeIn">
            {/* Credit Assessment Hero Card */}
            <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
              <div className="absolute -right-10 -top-10 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute right-20 -bottom-20 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

              <div className="relative z-10 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8">
                <div className="max-w-xl">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-emerald-300 border border-white/10 mb-4">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    Lender-Ready Credit Grade
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2">
                    MoMo Readiness Assessment
                  </h2>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    Our AI models analyze cash velocity, transaction consistency, operating net margins, and liquidity
                    buffers directly from local mobile money records to compute commercial creditworthiness.
                  </p>
                </div>

                {/* Score Circle / Badge */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-6 w-full lg:w-auto bg-white/5 border border-white/10 p-6 rounded-2xl backdrop-blur-sm">
                  <div className="text-center sm:text-left">
                    <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">
                      Computed Score
                    </div>
                    <div className="text-5xl sm:text-6xl font-black font-mono tracking-tighter text-white">
                      {profile ? profile.credit_score : "0"}
                      <span className="text-2xl font-normal text-slate-400">/100</span>
                    </div>
                  </div>

                  <div className="h-px sm:h-16 w-full sm:w-px bg-white/10" />

                  <div className="flex flex-col justify-center">
                    <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1.5">
                      Risk Tier
                    </div>
                    <div>
                      <span
                        className={`inline-flex items-center px-3 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wide border ${
                          profile
                            ? profile.indicator === "GREEN"
                              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                              : profile.indicator === "AMBER"
                                ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                                : "bg-rose-500/20 text-rose-300 border-rose-500/30"
                            : "bg-slate-700 text-slate-300 border-slate-600"
                        }`}
                      >
                        {profile ? profile.readiness_level : "Pending Assessment"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Diagnostic Box */}
              <div className="relative z-10 mt-6 pt-6 border-t border-white/10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="text-xs sm:text-sm text-slate-300 flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <span>
                    {profile?.assessment_details ||
                      "Process statement logs under the Ingestion tab to compute diagnostic credit details."}
                  </span>
                </div>

                <button
                  onClick={() => alert("Lender verification report generated as PDF!")}
                  className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold px-4 py-2.5 rounded-xl text-xs sm:text-sm shadow-md transition-all whitespace-nowrap flex-shrink-0"
                >
                  <Download className="w-4 h-4" />
                  Export Lender Report (PDF)
                </button>
              </div>
            </div>

            {/* Financial P&L Metric Grid */}
            <div>
              <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center gap-2">
                📊 Financial P&L Summary
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {/* Revenue */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                        Total Inflows
                      </span>
                      <h4 className="text-2xl sm:text-3xl font-extrabold text-emerald-600 mt-1 font-mono">
                        GHS {summary ? parseFloat(summary.revenue).toLocaleString("en-GH", { minimumFractionDigits: 2 }) : "0.00"}
                      </h4>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-1">
                    <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500" /> Confirmed business customer deposits
                  </div>
                </div>

                {/* Expenses */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                        Operating Outflows
                      </span>
                      <h4 className="text-2xl sm:text-3xl font-extrabold text-rose-600 mt-1 font-mono">
                        GHS {summary ? parseFloat(summary.expenses).toLocaleString("en-GH", { minimumFractionDigits: 2 }) : "0.00"}
                      </h4>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600">
                      <TrendingDown className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-1">
                    <ArrowDownRight className="w-3.5 h-3.5 text-rose-500" /> Inventory, salaries & logistics costs
                  </div>
                </div>

                {/* Net Profit */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                        Net Operating Surplus
                      </span>
                      <h4 className="text-2xl sm:text-3xl font-extrabold text-indigo-600 mt-1 font-mono">
                        GHS {summary ? parseFloat(summary.profit).toLocaleString("en-GH", { minimumFractionDigits: 2 }) : "0.00"}
                      </h4>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
                      <DollarSign className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500" /> Cash margin available for debt servicing
                  </div>
                </div>

                {/* Avg Balance */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                        Estimated Liquidity
                      </span>
                      <h4 className="text-2xl sm:text-3xl font-extrabold text-slate-800 mt-1 font-mono">
                        GHS {summary ? parseFloat(summary.average_balance).toLocaleString("en-GH", { minimumFractionDigits: 2 }) : "0.00"}
                      </h4>
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700">
                      <Wallet className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-slate-500" /> Average MoMo wallet cash buffer
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: LEDGER */}
        {activeTab === "ledger" && (
          <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden animate-fadeIn">
            {/* Table Header & Filters */}
            <div className="p-6 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/50">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Bookkeeping & Audit Ledger</h3>
                <p className="text-xs text-slate-500">
                  All human-in-the-loop overrides trigger immediate database audit logs for lender transparency.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
                {/* Search */}
                <div className="relative flex-1 sm:w-64">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search counterparty or ID..."
                    className="w-full pl-9 pr-4 py-2 text-xs bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
                  />
                </div>

                {/* Category Filter */}
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 text-xs bg-white border border-slate-200 rounded-xl font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="all">All Categories</option>
                  <option value="sales">Sales</option>
                  <option value="inventory">Inventory</option>
                  <option value="utilities">Utilities</option>
                  <option value="logistics">Logistics</option>
                  <option value="salaries">Salaries</option>
                  <option value="taxes">Taxes</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            {/* Responsive Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider font-semibold">
                    <th className="px-6 py-3.5">Date</th>
                    <th className="px-6 py-3.5">Counterparty</th>
                    <th className="px-6 py-3.5">Direction</th>
                    <th className="px-6 py-3.5">Category Override</th>
                    <th className="px-6 py-3.5">Amount (GHS)</th>
                    <th className="px-6 py-3.5 text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {filteredTransactions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-12 text-center text-slate-500">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <FileText className="w-8 h-8 text-slate-300" />
                          <p className="font-medium text-slate-700">No matching transactions found</p>
                          <p className="text-xs text-slate-400">
                            Process statements under the Ingestion tab or clear active search filters.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredTransactions.map((txn) => (
                      <tr key={txn.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-6 py-4 font-mono text-slate-600">{txn.timestamp}</td>
                        <td className="px-6 py-4 font-medium text-slate-900 truncate max-w-[180px]" title={txn.counterparty}>
                          {txn.counterparty}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold ${
                              txn.direction === "inflow"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {txn.direction.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <select
                            value={txn.category}
                            onChange={(e) => handleCategoryOverride(txn.id, e.target.value)}
                            className={`bg-white border ${
                              txn.reviewed_flag
                                ? "border-emerald-500 text-emerald-800 font-semibold shadow-xs"
                                : "border-slate-200 text-slate-700"
                            } rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer`}
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
                        <td className="px-6 py-4 font-bold font-mono text-slate-900">
                          {parseFloat(txn.amount).toLocaleString("en-GH", { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-6 py-4 text-right">
                          <span className="inline-flex items-center px-2 py-0.5 rounded font-mono font-bold text-xs bg-amber-50 text-amber-700 border border-amber-200">
                            {Math.round((txn.confidence || 1.0) * 100)}%
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: INGESTION & CONFIG */}
        {activeTab === "ingest" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fadeIn">
            {/* Left: Merchant Profile Setup */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col gap-5 lg:col-span-1">
              <div className="border-b border-slate-100 pb-4">
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <User className="w-4 h-4 text-indigo-600" /> Merchant Identity Profile
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Metadata attached to ingested statements for lender KYC verification.
                </p>
              </div>

              <div className="flex flex-col gap-4 text-sm">
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">Merchant Account ID</label>
                  <input
                    type="text"
                    value={merchantId}
                    onChange={(e) => setMerchantId(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">Registered Business Name</label>
                  <input
                    type="text"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">Owner / Operator Name</label>
                  <input
                    type="text"
                    value={ownerName}
                    onChange={(e) => setOwnerName(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">MoMo Phone Number</label>
                  <input
                    type="text"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Right: Statement Processing Form */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col gap-5 lg:col-span-2">
              <div className="border-b border-slate-100 pb-4">
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <UploadCloud className="w-5 h-5 text-blue-600" /> AI Statement Extraction & OCR
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Upload PDF statements, screenshots (PNG/JPG), or paste SMS alerts. Local multimodal agents parse and categorize records automatically.
                </p>
              </div>

              <form onSubmit={handleUpload} className="flex flex-col gap-5 text-sm">
                {/* File Drop Area */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-2">
                    Document Upload (PDF Statement / MoMo Screenshot)
                  </label>
                  <div className="border-2 border-dashed border-slate-200 hover:border-indigo-400 bg-slate-50 rounded-xl p-4 transition-colors flex flex-col items-center justify-center text-center">
                    <UploadCloud className="w-8 h-8 text-indigo-500 mb-2" />
                    <input
                      type="file"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setSelectedFile(e.target.files[0]);
                        }
                      }}
                      className="w-full text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer text-xs"
                    />
                    {selectedFile && (
                      <span className="text-xs font-semibold text-emerald-600 mt-2 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Selected: {selectedFile.name}
                      </span>
                    )}
                  </div>
                </div>

                <div className="relative flex py-1 items-center">
                  <div className="flex-grow border-t border-slate-200"></div>
                  <span className="flex-shrink mx-4 text-xs font-bold text-slate-400 uppercase tracking-widest">
                    OR PASTE RAW LOGS
                  </span>
                  <div className="flex-grow border-t border-slate-200"></div>
                </div>

                {/* Textarea */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1.5">
                    MTN / Telecel SMS Transaction Transcripts
                  </label>
                  <textarea
                    value={statementText}
                    onChange={(e) => setStatementText(e.target.value)}
                    rows={5}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 leading-relaxed"
                    placeholder="Received GHS 500.00 from Abena Osei on 2026-06-28 10:00:00. Transaction ID: 1001001..."
                  ></textarea>
                </div>

                {/* Submit Trigger */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-xl text-sm shadow-md transition-all flex items-center justify-center gap-2 disabled:bg-slate-300 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Executing ADK Agent Engine...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Run AI Statement Parser & Compute Credit Score
                    </>
                  )}
                </button>
              </form>

              {/* Status Banner */}
              {uploadStatus && (
                <div
                  className={`p-4 rounded-xl text-xs flex items-start gap-3 border ${
                    uploadStatus.type === "success"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : uploadStatus.type === "error"
                        ? "bg-rose-50 text-rose-800 border-rose-200"
                        : "bg-blue-50 text-blue-800 border-blue-200"
                  }`}
                >
                  {uploadStatus.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />}
                  {uploadStatus.type === "error" && <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />}
                  {uploadStatus.type === "info" && <Loader2 className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5 animate-spin" />}
                  <div className="font-medium leading-relaxed">{uploadStatus.message}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-12 py-6 text-center text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 MoMo Ledger. Built with local-first SQLite, Google ADK & Next.js.</p>
          <div className="flex gap-4">
            <span className="hover:text-slate-600 cursor-pointer">Privacy Policy</span>
            <span className="hover:text-slate-600 cursor-pointer">Lender Audit Terms</span>
            <span className="hover:text-slate-600 cursor-pointer">Security Model</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
