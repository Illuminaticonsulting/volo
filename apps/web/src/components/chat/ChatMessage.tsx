'use client';

import { Brain, User, Copy, RotateCcw, ThumbsUp, ThumbsDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'streaming' | 'error';
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  result?: string;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-4 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center',
          isUser
            ? 'bg-zinc-700'
            : 'bg-gradient-to-br from-brand-500 to-brand-700'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-zinc-300" />
        ) : (
          <Brain className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn('flex-1 min-w-0', isUser ? 'text-right' : 'text-left')}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-zinc-400">
            {isUser ? 'You' : 'Volo'}
          </span>
          <span className="text-[10px] text-zinc-600">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div
          className={cn(
            'inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed max-w-full',
            isUser
              ? 'bg-brand-600/20 text-zinc-200 rounded-br-md'
              : 'bg-surface-dark-2 text-zinc-300 rounded-bl-md border border-white/5'
          )}
        >
          {/* Tool calls display */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mb-3 space-y-2">
              {message.toolCalls.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-xs"
                >
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full',
                      tool.status === 'running' && 'bg-amber-400 animate-pulse-soft',
                      tool.status === 'completed' && 'bg-emerald-400',
                      tool.status === 'failed' && 'bg-red-400'
                    )}
                  />
                  <span className="font-mono text-zinc-400">{tool.name}</span>
                  <span className="text-zinc-600">
                    {tool.status === 'running' && 'Running...'}
                    {tool.status === 'completed' && 'Done'}
                    {tool.status === 'failed' && 'Failed'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Message content with markdown-like rendering */}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
            {message.status === 'streaming' && (
              <span className="cursor-blink" />
            )}
          </div>
        </div>

        {/* Assistant message actions */}
        {!isUser && message.status !== 'streaming' && (
          <div className="flex items-center gap-1 mt-2">
            <button className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group">
              <Copy className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400" />
            </button>
            <button className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group">
              <RotateCcw className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400" />
            </button>
            <button className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group">
              <ThumbsUp className="w-3 h-3 text-zinc-600 group-hover:text-emerald-400" />
            </button>
            <button className="p-1.5 rounded-lg hover:bg-white/5 transition-colors group">
              <ThumbsDown className="w-3 h-3 text-zinc-600 group-hover:text-red-400" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
