'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { motion } from 'framer-motion';
import { Eye, Shield, Users, Zap, Search } from 'lucide-react';

interface IntelligenceLead {
  id: number;
  email_hash: string;
  created_at: string;
  provider: string;
  role: string;
  meta: any;
  last_action: string;
  activity_score: number;
}

export default function OverseerDashboard() {
  const [feed, setFeed] = useState<IntelligenceLead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState('');

  const fetchFeed = async () => {
    try {
      const { data } = await api.get('/leads/feed');
      setFeed(data?.data ?? []);
    } catch (error) {
      console.error("Overseer System Fault:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 10000); // Live poll every 10s
    return () => clearInterval(interval);
  }, []);

  const filteredFeed = feed.filter(f => 
    f.email_hash.includes(filter) || f.last_action?.includes(filter)
  );

  return (
    <div className="overseer-root min-h-screen bg-[#050505] text-white p-8 font-mono">
      {/* Header */}
      <header className="flex justify-between items-center mb-12 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tighter flex items-center gap-3">
            <Shield className="text-purple-500" /> AETHERA OVERSEER
          </h1>
          <p className="text-white/40 text-xs mt-1 uppercase tracking-widest">Neural Pulse Monitoring // Real-Time Lead Capture</p>
        </div>
        <div className="flex gap-8 text-xs">
          <div className="flex flex-col items-end">
            <span className="text-white/40">TOTAL CAPTURED</span>
            <span className="text-xl text-purple-400">{feed.length}</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-white/40">LIVE SESSIONS</span>
            <span className="text-xl text-green-400">{feed.filter(f => f.activity_score > 5).length}</span>
          </div>
        </div>
      </header>

      {/* Toolbar */}
      <div className="flex gap-4 mb-8">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" size={16} />
          <input 
            type="text" 
            placeholder="FILTER BY HASH, EVENT, OR ORIGIN..." 
            className="w-full bg-white/5 border border-white/10 rounded-none py-3 pl-10 pr-4 text-xs focus:ring-1 focus:ring-purple-500 outline-none"
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <button 
          onClick={fetchFeed} 
          className="bg-purple-600 hover:bg-purple-500 px-6 py-3 text-xs font-bold transition-all"
        >
          FORCE SYNC
        </button>
      </div>

      {/* Main Feed */}
      <div className="grid grid-cols-1 gap-1">
        <div className="flex text-[10px] text-white/20 uppercase tracking-tighter mb-2 px-4 italic">
          <div className="w-12">ID</div>
          <div className="flex-1">Intelligence Target (Email Hash)</div>
          <div className="w-32">Origin</div>
          <div className="w-32">Last Action</div>
          <div className="w-24 text-right">Intensity</div>
          <div className="w-48 text-right">Captured At</div>
        </div>

        {isLoading ? (
          <div className="py-20 text-center text-white/20 italic text-sm animate-pulse">Establishing secure neural link...</div>
        ) : (
          filteredFeed.map((lead, idx) => (
            <motion.div 
              key={lead.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
              className={`flex items-center px-4 py-4 border border-white/5 hover:border-purple-500/50 hover:bg-purple-500/5 transition-all group ${lead.role === 'guest' ? 'border-l-4 border-l-purple-500/30' : ''}`}
            >
              <div className="w-12 text-white/20 text-xs">{lead.id}</div>
              <div className="flex-1">
                <div className="text-xs font-bold text-white/80 flex items-center gap-2">
                  {lead.role === 'guest' ? <Zap size={10} className="text-yellow-500" /> : <Users size={10} className="text-blue-500" />}
                  {lead.email_hash.substring(0, 16)}...
                </div>
                <div className="text-[10px] text-white/30 truncate max-w-sm mt-1">
                  {lead.meta?.session_id || 'UNKNOWN_SESSION'} {' // '} {lead.meta?.browser || 'DIRECT'}
                </div>
              </div>
              <div className="w-32 text-xs uppercase text-white/40">{lead.provider}</div>
              <div className="w-32 text-xs">
                <span className="bg-white/10 px-2 py-0.5 rounded text-[10px] font-bold text-white/60">
                  {lead.last_action || 'IDLE'}
                </span>
              </div>
              <div className="w-24 text-right">
                <div className="flex justify-end gap-0.5">
                  {[...Array(5)].map((_, i) => (
                    <div 
                      key={i} 
                      className={`w-1 h-3 ${i < (lead.activity_score / 2) ? 'bg-purple-500' : 'bg-white/10'}`}
                    />
                  ))}
                </div>
              </div>
              <div className="w-48 text-right text-[10px] text-white/20">
                {new Date(lead.created_at).toLocaleString()}
              </div>
            </motion.div>
          ))
        )}
      </div>

      <style jsx>{`
        .overseer-root {
          scrollbar-width: thin;
          scrollbar-color: rgba(255,255,255,0.1) transparent;
        }
      `}</style>
    </div>
  );
}
