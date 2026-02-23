'use client';

import { useEffect, useRef, useState } from 'react';
import {
  Search,
  MessageSquare,
  Code,
  TrendingUp,
  Mail,
  Settings,
  Terminal,
  Calendar,
  LayoutDashboard,
  Moon,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

const commands = [
  { id: 'chat', icon: MessageSquare, label: 'New conversation', category: 'General' },
  { id: 'dashboard', icon: LayoutDashboard, label: 'Open dashboard', category: 'General' },
  { id: 'settings', icon: Settings, label: 'Settings', category: 'General' },
  { id: 'briefing', icon: Calendar, label: 'Morning briefing', category: 'Actions' },
  { id: 'deploy', icon: Code, label: 'Deploy a project', category: 'Actions' },
  { id: 'portfolio', icon: TrendingUp, label: 'Portfolio overview', category: 'Actions' },
  { id: 'email', icon: Mail, label: 'Check email', category: 'Actions' },
  { id: 'terminal', icon: Terminal, label: 'Run terminal command', category: 'Actions' },
  { id: 'social', icon: Globe, label: 'Social media overview', category: 'Actions' },
  { id: 'theme', icon: Moon, label: 'Toggle dark mode', category: 'Appearance' },
];

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Will need to lift this state up or use a store
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filtered = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  );

  const grouped = filtered.reduce(
    (acc, cmd) => {
      if (!acc[cmd.category]) acc[cmd.category] = [];
      acc[cmd.category].push(cmd);
      return acc;
    },
    {} as Record<string, typeof commands>
  );

  return (
    <div className="fixed inset-0 z-50 cmd-overlay" onClick={onClose}>
      <div
        className="mx-auto mt-[20vh] w-full max-w-lg animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-2xl bg-surface-dark-1 border border-white/10 shadow-2xl overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
            <Search className="w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands, actions, anything..."
              className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 outline-none"
            />
            <kbd className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto py-2">
            {Object.entries(grouped).map(([category, cmds]) => (
              <div key={category}>
                <p className="px-4 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                  {category}
                </p>
                {cmds.map((cmd) => (
                  <button
                    key={cmd.id}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 transition-colors group"
                    onClick={onClose}
                  >
                    <cmd.icon className="w-4 h-4 text-zinc-500 group-hover:text-brand-400" />
                    <span className="text-sm text-zinc-300">{cmd.label}</span>
                  </button>
                ))}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="px-4 py-8 text-sm text-zinc-600 text-center">
                No commands found. Try&nbsp;
                <span className="text-brand-400">asking Volo</span> directly.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
