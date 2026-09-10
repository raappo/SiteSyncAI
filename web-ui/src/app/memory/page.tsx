"use client";

import { useState, useEffect } from "react";

export default function Memory() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/memory/stats")
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(console.error);
  }, []);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/memory?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-8rem)]">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Institutional Memory</h2>
          <p className="text-slate-400">Query the vector database for historical context and similar events.</p>
        </div>
        {stats && (
          <div className="bg-slate-900 border border-slate-700 px-4 py-2 rounded-lg">
            <span className="text-slate-400 text-sm">Total Events Vectorized: </span>
            <span className="text-cyan-400 font-bold">{stats.total_events}</span>
          </div>
        )}
      </div>

      <div className="flex gap-4">
        <input 
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-cyan-500 transition-colors"
          placeholder="e.g., Show me all delays related to hydrotesting..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button 
          className="bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-3 px-8 rounded-lg transition-colors disabled:opacity-50"
          onClick={handleSearch}
          disabled={loading || !query}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      <div className="glass-card flex-1 p-6 overflow-y-auto">
        {results.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center mt-20 text-slate-500">
            <span className="text-4xl mb-4">🧠</span>
            <p className="text-lg">Ask the Institutional Memory</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {results.map((res, i) => (
              <div key={i} className="bg-slate-900 border border-slate-700 rounded-lg p-5">
                <div className="flex justify-between mb-2">
                  <span className="text-xs font-mono text-cyan-400 bg-cyan-900/30 px-2 py-1 rounded">
                    Score: {res.score.toFixed(3)}
                  </span>
                  <span className="text-xs text-slate-500">Event ID: {res.metadata?.event_id}</span>
                </div>
                <p className="text-white">
                  {res.document}
                </p>
                <div className="mt-4 text-sm text-slate-400">
                  <span className="mr-4"><strong>Discipline:</strong> {res.metadata?.discipline || 'N/A'}</span>
                  <span><strong>Component:</strong> {res.metadata?.component || 'N/A'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
