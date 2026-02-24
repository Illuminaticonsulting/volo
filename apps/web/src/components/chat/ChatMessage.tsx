'use client';

import { Brain, User, Copy, RotateCcw, ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useState } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

export interface ToolCall {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed';
  result?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'streaming' | 'error';
  toolCalls?: ToolCall[];
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegenerate = () => {
    // Find the last user message and resend it
    const messages = useChatStore.getState().messages;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      // Remove the current assistant message and all messages after
      const msgIndex = messages.findIndex((m) => m.id === message.id);
      if (msgIndex >= 0) {
        useChatStore.setState({
          messages: messages.slice(0, msgIndex),
        });
      }
      useChatStore.getState().sendMessage(lastUserMsg.content);
      toast.info('Regenerating response...');
    }
  };

  const handleFeedback = async (type: 'up' | 'down') => {
    setFeedback(type);
    try {
      await api.post('/api/chat/feedback', {
        message_id: message.id,
        conversation_id: useChatStore.getState().conversationId,
        feedback: type === 'up' ? 'positive' : 'negative',
      });
      toast.success(type === 'up' ? 'Thanks for the feedback!' : 'Feedback noted, we\'ll improve');
    } catch {
      // Feedback is best-effort, don't show error
    }
  };

  return (
    <div
      className={cn(
        'flex gap-2 sm:gap-3 tap-none group/msg',
        isUser ? 'flex-row-reverse' : 'flex-row',
        'animate-slide-up'
      )}
    >
      {/* Avatar — hidden on mobile for user, always show for assistant */}
      <div
        className={cn(
          'flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full sm:rounded-xl flex items-center justify-center mt-1',
          isUser
            ? 'bg-zinc-700 hidden sm:flex'
            : 'bg-gradient-to-br from-brand-500 to-brand-700'
        )}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-zinc-300" />
        ) : (
          <Brain className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn(
        'flex flex-col min-w-0',
        isUser ? 'items-end max-w-[85%] sm:max-w-[70%]' : 'items-start max-w-[90%] sm:max-w-[80%]'
      )}>
        {/* Name & time row */}
        <div className={cn('flex items-center gap-2 mb-0.5 px-1', isUser && 'flex-row-reverse')}>
          <span className="text-[11px] font-medium text-zinc-500">
            {isUser ? 'You' : 'Volo'}
          </span>
          <span className="text-[10px] text-zinc-600">
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>

        {/* Message bubble */}
        <div
          className={cn(
            'rounded-2xl px-3 sm:px-4 py-2 sm:py-3 text-sm leading-relaxed',
            isUser
              ? 'bg-brand-600 text-white rounded-tr-md'
              : 'bg-surface-dark-2 text-zinc-300 rounded-tl-md border border-white/5'
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
                  <span className="font-mono text-zinc-400">
                    {formatToolName(tool.name)}
                  </span>
                  <span className="text-zinc-600">
                    {tool.status === 'running' && 'Running...'}
                    {tool.status === 'completed' && 'Done'}
                    {tool.status === 'failed' && 'Failed'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Message content */}
          {isUser ? (
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none break-words">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const isInline = !className;
                    return isInline ? (
                      <code
                        className="bg-white/10 text-brand-300 px-1.5 py-0.5 rounded text-xs font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    ) : (
                      <code className={cn(className, 'text-xs')} {...props}>
                        {children}
                      </code>
                    );
                  },
                  pre({ children, ...props }) {
                    return (
                      <pre
                        className="bg-black/40 rounded-xl p-4 overflow-x-auto border border-white/5 my-3"
                        {...props}
                      >
                        {children}
                      </pre>
                    );
                  },
                  table({ children, ...props }) {
                    return (
                      <div className="overflow-x-auto my-3">
                        <table className="w-full text-xs border-collapse" {...props}>
                          {children}
                        </table>
                      </div>
                    );
                  },
                  th({ children, ...props }) {
                    return (
                      <th className="border border-white/10 px-3 py-2 bg-white/5 text-left text-zinc-300 font-medium" {...props}>
                        {children}
                      </th>
                    );
                  },
                  td({ children, ...props }) {
                    return (
                      <td className="border border-white/10 px-3 py-2 text-zinc-400" {...props}>
                        {children}
                      </td>
                    );
                  },
                  a({ href, children, ...props }) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-400 hover:text-brand-300 underline underline-offset-2"
                        {...props}
                      >
                        {children}
                      </a>
                    );
                  },
                  ul({ children, ...props }) {
                    return <ul className="list-disc list-inside space-y-1 my-2" {...props}>{children}</ul>;
                  },
                  ol({ children, ...props }) {
                    return <ol className="list-decimal list-inside space-y-1 my-2" {...props}>{children}</ol>;
                  },
                  h1({ children, ...props }) {
                    return <h1 className="text-lg font-bold text-white mt-4 mb-2" {...props}>{children}</h1>;
                  },
                  h2({ children, ...props }) {
                    return <h2 className="text-base font-bold text-white mt-3 mb-2" {...props}>{children}</h2>;
                  },
                  h3({ children, ...props }) {
                    return <h3 className="text-sm font-bold text-zinc-200 mt-3 mb-1" {...props}>{children}</h3>;
                  },
                  blockquote({ children, ...props }) {
                    return (
                      <blockquote className="border-l-2 border-brand-500 pl-3 my-2 text-zinc-400 italic" {...props}>
                        {children}
                      </blockquote>
                    );
                  },
                  p({ children, ...props }) {
                    return <p className="my-1.5 leading-relaxed" {...props}>{children}</p>;
                  },
                  strong({ children, ...props }) {
                    return <strong className="font-semibold text-zinc-200" {...props}>{children}</strong>;
                  },
                  hr(props) {
                    return <hr className="border-white/10 my-4" {...props} />;
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
              {message.status === 'streaming' && (
                <span className="cursor-blink" />
              )}
            </div>
          )}
        </div>

        {/* Assistant message actions */}
        {!isUser && message.status !== 'streaming' && message.content && (
          <div className="flex items-center gap-0.5 mt-1 opacity-0 group-hover/msg:opacity-100 sm:transition-opacity">
            <button
              onClick={handleCopy}
              className="p-1.5 sm:p-1.5 rounded-lg hover:bg-white/5 active:bg-white/10 transition-colors tap-none"
              title="Copy"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 sm:w-3 sm:h-3 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5 sm:w-3 sm:h-3 text-zinc-600 hover:text-zinc-400" />
              )}
            </button>
            <button
              onClick={handleRegenerate}
              className="p-1.5 sm:p-1.5 rounded-lg hover:bg-white/5 active:bg-white/10 transition-colors tap-none"
              title="Regenerate"
            >
              <RotateCcw className="w-3.5 h-3.5 sm:w-3 sm:h-3 text-zinc-600 hover:text-zinc-400" />
            </button>
            <button
              onClick={() => handleFeedback('up')}
              className="p-1.5 sm:p-1.5 rounded-lg hover:bg-white/5 active:bg-white/10 transition-colors tap-none"
              title="Good response"
            >
              <ThumbsUp className={cn('w-3.5 h-3.5 sm:w-3 sm:h-3', feedback === 'up' ? 'text-emerald-400' : 'text-zinc-600 hover:text-emerald-400')} />
            </button>
            <button
              onClick={() => handleFeedback('down')}
              className="p-1.5 sm:p-1.5 rounded-lg hover:bg-white/5 active:bg-white/10 transition-colors tap-none"
              title="Bad response"
            >
              <ThumbsDown className={cn('w-3.5 h-3.5 sm:w-3 sm:h-3', feedback === 'down' ? 'text-red-400' : 'text-zinc-600 hover:text-red-400')} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
