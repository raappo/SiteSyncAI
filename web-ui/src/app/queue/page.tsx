"use client";

import { useEffect, useState } from "react";

export default function Queue() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/queue")
      .then(res => res.json())
      .then(data => {
        setItems(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="flex flex-col gap-6 h-[calc(100vh-8rem)]">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Review Queue</h2>
        <p className="text-slate-400">Items requiring human planner approval due to low confidence or contradictions.</p>
      </div>

      <div className="glass-card flex-1 p-6 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center mt-20">
            <div className="w-8 h-8 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center mt-20 text-slate-500">
            <span className="text-4xl mb-4">🎉</span>
            <p className="text-lg">Inbox Zero!</p>
            <p className="text-sm">No items require review.</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {items.map((item) => (
              <div key={item.id} className="bg-slate-900 border border-slate-700 rounded-lg p-5 hover:border-cyan-500 transition-colors">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-400 text-xs font-bold tracking-wider">
                      {item.status}
                    </span>
                    <span className="text-sm text-slate-400">ID: {item.id}</span>
                  </div>
                  <span className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
                </div>
                
                <p className="text-white mb-4">
                  {item.planner_notes}
                </p>
                
                <div className="flex gap-3">
                  <button className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded text-sm font-medium transition-colors">
                    Approve
                  </button>
                  <button className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded text-sm font-medium transition-colors">
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
