'use client';

import { create } from 'zustand';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface Conversation {
  id: string;
  title: string;
  preview: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationState {
  conversations: Conversation[];
  loading: boolean;
  searchQuery: string;

  // Actions
  fetchConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  loading: false,
  searchQuery: '',

  fetchConversations: async () => {
    set({ loading: true });
    try {
      const q = get().searchQuery;
      const endpoint = q
        ? `/api/conversations?search=${encodeURIComponent(q)}`
        : '/api/conversations';
      const data = await api.get<{ conversations: Conversation[] }>(endpoint);
      set({ conversations: data?.conversations || [] });
    } catch {
      // Keep existing conversations on error
    } finally {
      set({ loading: false });
    }
  },

  deleteConversation: async (id) => {
    const prev = get().conversations;
    set((s) => ({ conversations: s.conversations.filter((c) => c.id !== id) }));
    try {
      await api.delete(`/api/conversations/${id}`);
    } catch {
      set({ conversations: prev });
      toast.error('Failed to delete conversation');
    }
  },

  renameConversation: async (id, title) => {
    const prev = get().conversations;
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === id ? { ...c, title } : c,
      ),
    }));
    try {
      await api.patch(`/api/conversations/${id}`, { title });
    } catch {
      set({ conversations: prev });
      toast.error('Failed to rename conversation');
    }
  },

  setSearchQuery: (query) => set({ searchQuery: query }),
}));
