'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Brain,
  Code,
  TrendingUp,
  Mail,
  Calendar,
  Terminal,
  Sparkles,
  ArrowRight,
  Sun,
  Moon,
  Sunrise,
  Sunset,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void;
}

const suggestions = [
  {
    icon: Sparkles,
    title: 'Get started',
    description: 'Set up my integrations and configure Volo',
    prompt: "Let's get started — help me set up Volo with all my tools and accounts.",
  },
  {
    icon: Code,
    title: 'My projects',
    description: 'Connect GitHub and index all my repositories',
    prompt: 'Connect to my GitHub and show me an overview of all my projects.',
  },
  {
    icon: TrendingUp,
    title: 'Trading',
    description: 'Set up portfolio tracking and market alerts',
    prompt: 'Help me set up my trading integrations — brokerage, crypto, and market data.',
  },
  {
    icon: Mail,
    title: 'Communications',
    description: 'Connect email, calendar, and messaging',
    prompt: 'Connect my email and calendar so you can help me manage communications.',
  },
  {
    icon: Terminal,
    title: 'Machine access',
    description: 'Let Volo run tasks on your computers',
    prompt: 'Set up remote machine access so you can execute tasks on my laptop.',
  },
  {
    icon: Calendar,
    title: 'Morning briefing',
    description: 'Get a daily summary of everything that matters',
    prompt: 'Give me my morning briefing — calendar, tasks, markets, messages.',
  },
];

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  const [status, setStatus] = useState({ apiOnline: false, integrations: 0, memories: 0 });
  const user = useAuthStore((s) => s.user);

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    const firstName = user?.name?.split(' ')[0] || '';
    const name = firstName ? `, ${firstName}` : '';
    if (hour < 6) return { text: `Still up${name}?`, icon: Moon, sub: 'The night is yours — let\'s get things done.' };
    if (hour < 12) return { text: `Good morning${name}`, icon: Sunrise, sub: 'Ready to make today count.' };
    if (hour < 17) return { text: `Good afternoon${name}`, icon: Sun, sub: 'What are we working on?' };
    if (hour < 21) return { text: `Good evening${name}`, icon: Sunset, sub: 'Let\'s wrap up the day strong.' };
    return { text: `Good night${name}`, icon: Moon, sub: 'One more thing before bed?' };
  }, [user?.name]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [healthRes, systemRes] = await Promise.allSettled([
          api.get('/health'),
          api.get<{ integrations_count?: number; memories_count?: number }>('/api/system/status'),
        ]);
        setStatus({
          apiOnline: healthRes.status === 'fulfilled',
          integrations: systemRes.status === 'fulfilled' ? (systemRes.value as { integrations_count?: number }).integrations_count || 0 : 0,
          memories: systemRes.status === 'fulfilled' ? (systemRes.value as { memories_count?: number }).memories_count || 0 : 0,
        });
      } catch {
        setStatus({ apiOnline: false, integrations: 0, memories: 0 });
      }
    };
    fetchStatus();
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-3 sm:px-4 py-6 sm:py-12">
      {/* Logo & Welcome */}
      <div className="mb-6 sm:mb-10 text-center">
        <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center mx-auto mb-4 sm:mb-6 shadow-lg shadow-brand-500/20">
          <Brain className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 sm:mb-3 flex items-center justify-center gap-2">
          {<greeting.icon className="w-6 h-6 sm:w-7 sm:h-7 text-brand-400" />}
          {greeting.text}
        </h1>
        <p className="text-zinc-500 text-xs sm:text-sm max-w-md px-2">
          {greeting.sub}
        </p>
      </div>

      {/* Suggestion Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3 max-w-3xl w-full">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.title}
            onClick={() => onSuggestionClick(suggestion.prompt)}
            className="group flex flex-col items-start gap-2 sm:gap-3 p-3 sm:p-4 rounded-2xl bg-surface-dark-2 border border-white/5 hover:border-brand-500/30 active:border-brand-500/50 hover:bg-surface-dark-3 transition-all text-left tap-none active:scale-[0.98]"
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-brand-600/10 flex items-center justify-center group-hover:bg-brand-600/20 transition-colors">
              <suggestion.icon className="w-4 h-4 sm:w-5 sm:h-5 text-brand-400" />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-medium text-zinc-200 mb-0.5 sm:mb-1 flex items-center gap-1 sm:gap-2">
                {suggestion.title}
                <ArrowRight className="w-3 h-3 text-zinc-600 group-hover:text-brand-400 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-[10px] sm:text-xs text-zinc-500 leading-relaxed line-clamp-2">
                {suggestion.description}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* Status indicators */}
      <div className="flex items-center gap-4 sm:gap-6 mt-6 sm:mt-10 text-[10px] text-zinc-600">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.apiOnline ? 'bg-emerald-500' : 'bg-red-500'}`} />
          {status.apiOnline ? 'Online' : 'Offline'}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.integrations > 0 ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
          {status.integrations} Integration{status.integrations !== 1 ? 's' : ''}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.memories > 0 ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
          {status.memories > 0 ? `${status.memories} Memories` : 'Memory Empty'}
        </div>
      </div>
    </div>
  );
}
