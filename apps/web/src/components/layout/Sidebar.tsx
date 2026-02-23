'use client';

import { useState } from 'react';
import {
  MessageSquare,
  Plus,
  Settings,
  Zap,
  Code,
  TrendingUp,
  Mail,
  Terminal,
  Globe,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Brain,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const conversations = [
  { id: '1', title: 'Morning Briefing', time: 'Today', icon: Zap },
  { id: '2', title: 'Deploy Project Alpha', time: 'Today', icon: Code },
  { id: '3', title: 'Portfolio Review', time: 'Yesterday', icon: TrendingUp },
  { id: '4', title: 'Email Triage', time: 'Yesterday', icon: Mail },
];

const integrations = [
  { id: 'github', name: 'GitHub', icon: Code, connected: false },
  { id: 'email', name: 'Email', icon: Mail, connected: false },
  { id: 'trading', name: 'Trading', icon: TrendingUp, connected: false },
  { id: 'terminal', name: 'Machine', icon: Terminal, connected: false },
  { id: 'social', name: 'Social', icon: Globe, connected: false },
];

export function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'chats' | 'integrations'>('chats');

  return (
    <aside
      className={cn(
        'relative flex flex-col border-r border-white/5 bg-surface-dark-1 transition-all duration-300',
        isOpen ? 'w-72' : 'w-0 overflow-hidden'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <span className="text-lg font-bold tracking-tight gradient-text">VOLO</span>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-3">
        <button className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" />
          New Conversation
        </button>
      </div>

      {/* Tabs */}
      <div className="flex px-3 gap-1">
        <button
          onClick={() => setActiveTab('chats')}
          className={cn(
            'flex-1 py-2 text-xs font-medium rounded-lg transition-colors',
            activeTab === 'chats'
              ? 'bg-white/10 text-white'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Conversations
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={cn(
            'flex-1 py-2 text-xs font-medium rounded-lg transition-colors',
            activeTab === 'integrations'
              ? 'bg-white/10 text-white'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Integrations
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
        {activeTab === 'chats' ? (
          <>
            <p className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Recent
            </p>
            {conversations.map((conv) => (
              <button
                key={conv.id}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 text-left transition-colors group"
              >
                <conv.icon className="w-4 h-4 text-zinc-500 group-hover:text-brand-400 transition-colors" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-300 truncate">{conv.title}</p>
                  <p className="text-[10px] text-zinc-600">{conv.time}</p>
                </div>
              </button>
            ))}
          </>
        ) : (
          <>
            <p className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Connected Services
            </p>
            {integrations.map((integration) => (
              <button
                key={integration.id}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 text-left transition-colors group"
              >
                <integration.icon className="w-4 h-4 text-zinc-500 group-hover:text-brand-400 transition-colors" />
                <div className="flex-1">
                  <p className="text-sm text-zinc-300">{integration.name}</p>
                </div>
                <span
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded-full',
                    integration.connected
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-zinc-800 text-zinc-500'
                  )}
                >
                  {integration.connected ? 'Active' : 'Setup'}
                </span>
              </button>
            ))}
          </>
        )}
      </div>

      {/* Bottom — Dashboard & Settings */}
      <div className="border-t border-white/5 p-3 space-y-1">
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 text-left transition-colors">
          <LayoutDashboard className="w-4 h-4 text-zinc-500" />
          <span className="text-sm text-zinc-400">Dashboard</span>
        </button>
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 text-left transition-colors">
          <Settings className="w-4 h-4 text-zinc-500" />
          <span className="text-sm text-zinc-400">Settings</span>
        </button>
      </div>

      {/* Toggle button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-surface-dark-2 border border-white/10 flex items-center justify-center hover:bg-surface-dark-3 transition-colors z-10"
      >
        {isOpen ? (
          <ChevronLeft className="w-3 h-3 text-zinc-400" />
        ) : (
          <ChevronRight className="w-3 h-3 text-zinc-400" />
        )}
      </button>
    </aside>
  );
}
