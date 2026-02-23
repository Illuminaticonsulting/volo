'use client';

import { Brain } from 'lucide-react';

export function ThinkingIndicator() {
  return (
    <div className="flex gap-4 animate-fade-in">
      <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center animate-thinking">
        <Brain className="w-4 h-4 text-white" />
      </div>
      <div className="flex items-center gap-2 py-3">
        <div className="flex gap-1">
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-xs text-zinc-500">Volo is thinking...</span>
      </div>
    </div>
  );
}
