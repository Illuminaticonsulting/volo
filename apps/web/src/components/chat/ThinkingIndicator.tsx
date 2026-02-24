'use client';

import { Brain, Wrench, Search, Globe, Code, Database, Mail, GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';
import { useState, useEffect } from 'react';

const toolIcons: Record<string, typeof Wrench> = {
  web_search: Search,
  browse: Globe,
  code: Code,
  database: Database,
  email: Mail,
  git: GitBranch,
};

const thinkingPhrases = [
  'Analyzing your request...',
  'Thinking about this...',
  'Working on it...',
  'Processing...',
  'Let me figure this out...',
];

export function ThinkingIndicator() {
  const messages = useChatStore((s) => s.messages);
  const [elapsed, setElapsed] = useState(0);
  const [phraseIndex, setPhraseIndex] = useState(0);

  // Get active tool calls from the latest assistant message
  const latestAssistant = [...messages].reverse().find((m) => m.role === 'assistant');
  const activeTools = latestAssistant?.toolCalls?.filter((t) => t.status === 'running') || [];
  const completedTools = latestAssistant?.toolCalls?.filter((t) => t.status === 'completed') || [];
  const hasTools = (latestAssistant?.toolCalls?.length || 0) > 0;

  useEffect(() => {
    const timer = setInterval(() => setElapsed((t) => t + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % thinkingPhrases.length);
    }, 3000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex gap-3 sm:gap-4 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full sm:rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
        <Brain className={cn('w-3.5 h-3.5 sm:w-4 sm:h-4 text-white', !hasTools && 'animate-pulse')} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="bg-surface-dark-2 border border-white/5 rounded-2xl rounded-tl-md px-3 sm:px-4 py-2.5 sm:py-3 max-w-[80%]">
          {/* Tool calls */}
          {hasTools && (
            <div className="space-y-1.5 mb-2">
              {activeTools.map((tool) => {
                const Icon = Object.entries(toolIcons).find(([key]) => tool.name.toLowerCase().includes(key))?.[1] || Wrench;
                return (
                  <div key={tool.id} className="flex items-center gap-2 text-xs">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    <Icon className="w-3 h-3 text-zinc-500" />
                    <span className="text-zinc-400 font-mono text-[11px]">
                      {formatToolName(tool.name)}
                    </span>
                    <span className="text-zinc-600 text-[10px]">running...</span>
                  </div>
                );
              })}
              {completedTools.map((tool) => {
                const Icon = Object.entries(toolIcons).find(([key]) => tool.name.toLowerCase().includes(key))?.[1] || Wrench;
                return (
                  <div key={tool.id} className="flex items-center gap-2 text-xs opacity-60">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    <Icon className="w-3 h-3 text-zinc-600" />
                    <span className="text-zinc-500 font-mono text-[11px]">
                      {formatToolName(tool.name)}
                    </span>
                    <span className="text-zinc-600 text-[10px]">done</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Thinking animation */}
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
            <span className="text-xs text-zinc-500">
              {hasTools ? 'Working...' : thinkingPhrases[phraseIndex]}
            </span>
            {elapsed > 2 && (
              <span className="text-[10px] text-zinc-600 ml-auto">{elapsed}s</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
