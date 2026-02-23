'use client';

import { Search, Command, PanelLeftClose, PanelLeft, Bell, User } from 'lucide-react';

interface TopBarProps {
  onToggleSidebar: () => void;
  onOpenCommandPalette: () => void;
}

export function TopBar({ onToggleSidebar, onOpenCommandPalette }: TopBarProps) {
  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-white/5 bg-surface-dark-1/50 backdrop-blur-xl">
      {/* Left */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-lg hover:bg-white/5 transition-colors"
          aria-label="Toggle sidebar"
        >
          <PanelLeft className="w-4 h-4 text-zinc-400" />
        </button>
        <div className="text-sm text-zinc-500">
          <span className="text-zinc-300 font-medium">Volo</span>
          <span className="mx-2 text-zinc-700">/</span>
          <span>New Conversation</span>
        </div>
      </div>

      {/* Center — Command Palette Trigger */}
      <button
        onClick={onOpenCommandPalette}
        className="flex items-center gap-3 px-4 py-1.5 rounded-xl bg-white/5 hover:bg-white/8 border border-white/5 transition-colors group"
      >
        <Search className="w-3.5 h-3.5 text-zinc-500" />
        <span className="text-sm text-zinc-500">Search or ask anything...</span>
        <kbd className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono">
          <Command className="w-2.5 h-2.5" />K
        </kbd>
      </button>

      {/* Right */}
      <div className="flex items-center gap-2">
        <button className="relative p-2 rounded-lg hover:bg-white/5 transition-colors">
          <Bell className="w-4 h-4 text-zinc-400" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand-500" />
        </button>
        <button className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
          <User className="w-4 h-4 text-white" />
        </button>
      </div>
    </header>
  );
}
