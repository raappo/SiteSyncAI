"use client";

import { useState } from "react";

export default function Home() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");

  const handleProcess = async () => {
    if (!input) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/api/v1/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_input: input, evidence_type: "text" }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.statusText}`);
      }
      
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to process");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-[calc(100vh-8rem)]">
      {/* Left Pane - Input */}
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Time Agent</h2>
          <p className="text-slate-400">Report progress updates from the field.</p>
        </div>
        
        <div className="glass-card flex-1 p-6 flex flex-col gap-4">
          <textarea 
            className="w-full flex-1 bg-slate-900 border border-slate-700 rounded-lg p-4 text-white focus:outline-none focus:border-cyan-500 resize-none transition-colors"
            placeholder="e.g., Spool erected on 6 inch hot oil line. 9 joints done out of 28 total. Date: 14-Feb-2024."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <button 
            className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-3 px-4 rounded-lg transition-colors disabled:opacity-50"
            onClick={handleProcess}
            disabled={loading || !input}
          >
            {loading ? "Processing..." : "Process & Link"}
          </button>
        </div>
      </div>

      {/* Right Pane - Output */}
      <div className="flex flex-col gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Live Extraction</h2>
          <p className="text-slate-400">Real-time schedule mapping output.</p>
        </div>
        
        <div className="glass-card flex-1 p-6 overflow-y-auto">
          {!result && !error && !loading && (
            <div className="h-full flex items-center justify-center text-slate-500">
              Submit an update to see extraction results.
            </div>
          )}
          
          {loading && (
            <div className="h-full flex items-center justify-center">
              <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
              <h3 className="font-bold mb-1">Error</h3>
              <p>{error}</p>
            </div>
          )}

          {result && (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
              <div className="flex items-center justify-between border-b border-slate-700 pb-4">
                <h3 className="text-lg font-semibold text-white">Extraction Complete</h3>
                <span className="text-xs font-mono bg-slate-800 px-2 py-1 rounded text-cyan-400">
                  {result.ms_elapsed}ms
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                  <div className="text-xs text-slate-400 mb-1">Status</div>
                  <div className={`text-lg font-bold ${result.status === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {result.status}
                  </div>
                </div>
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                  <div className="text-xs text-slate-400 mb-1">Updates Extracted</div>
                  <div className="text-lg font-bold text-white">{result.updates_extracted}</div>
                </div>
              </div>

              <div className="bg-slate-900 rounded-lg p-4 border border-slate-700">
                <div className="text-xs text-slate-400 mb-2">System Message</div>
                <div className="text-sm font-mono text-slate-300">{result.message}</div>
                {result.event_id && <div className="text-sm mt-2 text-slate-400">Event ID: {result.event_id}</div>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
