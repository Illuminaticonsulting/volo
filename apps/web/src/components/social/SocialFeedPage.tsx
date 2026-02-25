'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Heart, MessageCircle, Share2, RefreshCw,
  ExternalLink, Twitter, Instagram, Linkedin, Music, Globe,
  Bookmark, MoreHorizontal, Send, X, Plus, Link2, Unlink,
  Facebook as FacebookIcon, Sparkles, Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface SocialPost {
  platform: string;
  id: string;
  author: string;
  username: string;
  avatar: string;
  content: string;
  timestamp: string;
  likes: number;
  comments: number;
  shares: number;
  subreddit?: string;
  media: { url: string; type: string }[];
  url: string;
}

interface PlatformInfo {
  id: string;
  name: string;
  connected: boolean;
  color: string;
  username?: string;
  avatar?: string;
  configured?: boolean;
}

const platformIcons: Record<string, typeof Twitter> = {
  twitter: Twitter,
  instagram: Instagram,
  linkedin: Linkedin,
  reddit: MessageCircle,
  tiktok: Music,
  facebook: FacebookIcon,
};

const platformColors: Record<string, string> = {
  twitter: 'text-blue-400',
  instagram: 'text-pink-400',
  linkedin: 'text-blue-500',
  reddit: 'text-orange-500',
  tiktok: 'text-white',
  facebook: 'text-blue-500',
};

const platformBg: Record<string, string> = {
  twitter: 'bg-blue-500/10',
  instagram: 'bg-gradient-to-br from-purple-500/10 to-pink-500/10',
  linkedin: 'bg-blue-500/10',
  reddit: 'bg-orange-500/10',
  tiktok: 'bg-white/10',
  facebook: 'bg-blue-500/10',
};

export function SocialFeedPage() {
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [activePlatform, setActivePlatform] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [savedPosts, setSavedPosts] = useState<Set<string>>(new Set());
  const [likedPosts, setLikedPosts] = useState<Set<string>>(new Set());
  const [commentingOn, setCommentingOn] = useState<string | null>(null);
  const [commentText, setCommentText] = useState('');
  const [showCompose, setShowCompose] = useState(false);
  const [composeText, setComposeText] = useState('');
  const [composePlatform, setComposePlatform] = useState('twitter');
  const [showConnectPanel, setShowConnectPanel] = useState(false);
  const [summarizingPost, setSummarizingPost] = useState<string | null>(null);
  const [postSummaries, setPostSummaries] = useState<Record<string, string>>({});
  const commentRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchFeed();
    fetchConnectionStatus();
  }, []);

  useEffect(() => {
    // Check for ?connected= query param after OAuth callback
    const params = new URLSearchParams(window.location.search);
    const connected = params.get('connected');
    if (connected) {
      toast.success(`Connected to ${connected}!`);
      fetchConnectionStatus();
      window.history.replaceState({}, '', window.location.pathname);
    }
    const error = params.get('error');
    if (error) {
      toast.error(`Connection failed: ${error}`);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const fetchFeed = async (platform?: string) => {
    setLoading(true);
    try {
      const path = platform && platform !== 'all'
        ? `/api/social/feed/${platform}`
        : '/api/social/feed';
      const data = await api.get<{ posts: SocialPost[]; platforms: PlatformInfo[] }>(path);
      setPosts(data.posts || []);
      if (data.platforms) setPlatforms(data.platforms);
    } catch {
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchConnectionStatus = async () => {
    try {
      const data = await api.get<{ platforms: PlatformInfo[] }>('/api/social/connect/status');
      if (data.platforms) setPlatforms(data.platforms);
    } catch {}
  };

  const handleConnect = async (platformId: string) => {
    try {
      const data = await api.get<{ url: string }>(`/api/social/connect/${platformId}`);
      if (data.url) window.location.href = data.url;
    } catch {
      toast.error(`Failed to start ${platformId} connection`);
    }
  };

  const handleDisconnect = async (platformId: string) => {
    try {
      await api.delete(`/api/social/connect/${platformId}`);
      toast.success(`Disconnected from ${platformId}`);
      fetchConnectionStatus();
    } catch {
      toast.error('Failed to disconnect');
    }
  };

  const handleLike = async (post: SocialPost) => {
    const key = `${post.platform}:${post.id}`;
    if (likedPosts.has(key)) {
      // Unlike
      try {
        await api.delete(`/api/social/${post.platform}/like?post_id=${post.id}`);
        setLikedPosts(prev => { const n = new Set(prev); n.delete(key); return n; });
        toast.success('Unliked');
      } catch (e: any) {
        toast.error(e?.message || 'Failed to unlike');
      }
    } else {
      try {
        await api.post(`/api/social/${post.platform}/like`, { post_id: post.id });
        setLikedPosts(prev => new Set(prev).add(key));
        toast.success('Liked!');
      } catch (e: any) {
        if (e?.message?.includes('Not connected')) {
          toast.error(`Connect your ${post.platform} account first`);
        } else {
          toast.error(e?.message || 'Failed to like');
        }
      }
    }
  };

  const handleComment = async (post: SocialPost) => {
    if (!commentText.trim()) return;
    try {
      await api.post(`/api/social/${post.platform}/comment`, { post_id: post.id, text: commentText });
      toast.success('Comment posted!');
      setCommentText('');
      setCommentingOn(null);
    } catch (e: any) {
      if (e?.message?.includes('Not connected')) {
        toast.error(`Connect your ${post.platform} account first`);
      } else {
        toast.error(e?.message || 'Failed to comment');
      }
    }
  };

  const handleRepost = async (post: SocialPost) => {
    try {
      await api.post(`/api/social/${post.platform}/repost`, { post_id: post.id });
      toast.success('Reposted!');
    } catch (e: any) {
      // Fallback to share
      if (post.url) {
        if (navigator.share) {
          navigator.share({ title: post.author, url: post.url }).catch(() => {});
        } else {
          navigator.clipboard.writeText(post.url);
          toast.success('Link copied!');
        }
      } else {
        toast.error(e?.message || 'Failed to repost');
      }
    }
  };

  const handleCompose = async () => {
    if (!composeText.trim()) return;
    try {
      await api.post(`/api/social/${composePlatform}/post`, { text: composeText });
      toast.success(`Posted to ${composePlatform}!`);
      setComposeText('');
      setShowCompose(false);
      setTimeout(() => fetchFeed(), 2000);
    } catch (e: any) {
      if (e?.message?.includes('Not connected')) {
        toast.error(`Connect your ${composePlatform} account first`);
      } else {
        toast.error(e?.message || 'Failed to post');
      }
    }
  };

  const handleFilterPlatform = (platform: string) => {
    setActivePlatform(platform);
    fetchFeed(platform === 'all' ? undefined : platform);
  };

  const toggleSave = (postId: string) => {
    setSavedPosts(prev => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });
  };

  const formatCount = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  };

  const handleSummarizePost = async (post: SocialPost) => {
    const key = `${post.platform}:${post.id}`;
    if (postSummaries[key]) {
      // Toggle off
      setPostSummaries(prev => { const n = { ...prev }; delete n[key]; return n; });
      return;
    }
    setSummarizingPost(key);
    try {
      const data = await api.post<{ summary: string }>('/api/ai/summarize', {
        content: `${post.author} (@${post.username}): ${post.content}`,
        content_type: 'post',
        style: 'concise',
      });
      setPostSummaries(prev => ({ ...prev, [key]: data.summary }));
    } catch {
      toast.error('Could not summarize post');
    } finally {
      setSummarizingPost(null);
    }
  };

  const connectedPlatforms = platforms.filter(p => p.connected);

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-2">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-dark-1 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-bold text-white flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Globe className="w-5 h-5 text-white" />
              </div>
              Social Feed
            </h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowConnectPanel(!showConnectPanel)}
                className={cn(
                  'p-2 rounded-xl transition-colors',
                  showConnectPanel ? 'bg-brand-600 text-white' : 'bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white'
                )}
                title="Manage connections"
              >
                <Link2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowCompose(!showCompose)}
                className={cn(
                  'p-2 rounded-xl transition-colors',
                  showCompose ? 'bg-brand-600 text-white' : 'bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white'
                )}
                title="New post"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => fetchFeed(activePlatform === 'all' ? undefined : activePlatform)}
                className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Connect Panel */}
          <AnimatePresence>
            {showConnectPanel && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mb-3"
              >
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/5">
                  {platforms.map(p => {
                    const Icon = platformIcons[p.id] || Globe;
                    return (
                      <div key={p.id} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.03]">
                        <div className="flex items-center gap-2">
                          <Icon className={cn('w-4 h-4', platformColors[p.id])} />
                          <span className="text-xs text-white">{p.name}</span>
                        </div>
                        {p.connected ? (
                          <button
                            onClick={() => handleDisconnect(p.id)}
                            className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
                          >
                            <Unlink className="w-3 h-3" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleConnect(p.id)}
                            className="text-[10px] px-2 py-0.5 rounded bg-brand-500/20 text-brand-400 hover:bg-brand-500/30 transition-colors"
                          >
                            Connect
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Compose */}
          <AnimatePresence>
            {showCompose && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden mb-3"
              >
                <div className="p-4 rounded-xl bg-white/[0.03] border border-white/5 space-y-3">
                  <textarea
                    value={composeText}
                    onChange={e => setComposeText(e.target.value)}
                    placeholder="What's on your mind?"
                    className="w-full bg-transparent border-none outline-none text-white text-sm placeholder-zinc-500 resize-none min-h-[80px]"
                    autoFocus
                  />
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-500">Post to:</span>
                      {connectedPlatforms.map(p => {
                        const Icon = platformIcons[p.id] || Globe;
                        return (
                          <button
                            key={p.id}
                            onClick={() => setComposePlatform(p.id)}
                            className={cn(
                              'p-1.5 rounded-lg transition-colors',
                              composePlatform === p.id
                                ? 'bg-white/10 text-white'
                                : 'text-zinc-500 hover:text-white hover:bg-white/5'
                            )}
                          >
                            <Icon className="w-4 h-4" />
                          </button>
                        );
                      })}
                    </div>
                    <button
                      onClick={handleCompose}
                      disabled={!composeText.trim()}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-medium hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <Send className="w-3.5 h-3.5" />
                      Post
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Platform Filter Tabs */}
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hidden">
            <button
              onClick={() => handleFilterPlatform('all')}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                activePlatform === 'all'
                  ? 'bg-brand-600 text-white'
                  : 'bg-white/5 text-zinc-400 hover:bg-white/10'
              )}
            >
              All Platforms
            </button>
            {platforms.map(p => {
              const Icon = platformIcons[p.id] || Globe;
              return (
                <button
                  key={p.id}
                  onClick={() => handleFilterPlatform(p.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all',
                    activePlatform === p.id
                      ? 'bg-white/[0.15] text-white'
                      : 'bg-white/5 text-zinc-400 hover:bg-white/10'
                  )}
                >
                  <Icon className={cn('w-3.5 h-3.5', platformColors[p.id])} />
                  {p.name}
                  {!p.connected && (
                    <span className="w-1.5 h-1.5 ml-1 rounded-full bg-zinc-500" title="Not connected" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Feed */}
      <div className="max-w-3xl mx-auto px-6 py-4 space-y-3">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 rounded-2xl bg-white/5 animate-pulse" />
          ))
        ) : posts.length === 0 ? (
          <div className="text-center py-16 text-zinc-500">
            <Globe className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No posts to show. Connect your accounts to see your feed.</p>
            <button
              onClick={() => setShowConnectPanel(true)}
              className="mt-4 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm hover:bg-brand-500 transition-colors"
            >
              Connect Accounts
            </button>
          </div>
        ) : (
          posts.map((post, idx) => {
            const PlatformIcon = platformIcons[post.platform] || Globe;
            const postKey = `${post.platform}:${post.id}`;
            return (
              <motion.div
                key={post.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
                className="p-5 rounded-2xl bg-white/[0.03] border border-white/5 hover:border-white/10 transition-all"
              >
                {/* Post Header */}
                <div className="flex items-start gap-3">
                  <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', platformBg[post.platform])}>
                    {post.avatar ? (
                      <img src={post.avatar} alt="" className="w-10 h-10 rounded-full" />
                    ) : (
                      <PlatformIcon className={cn('w-5 h-5', platformColors[post.platform])} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold text-sm">{post.author}</span>
                      <span className="text-zinc-500 text-sm">{post.username}</span>
                      <span className="text-zinc-600 text-xs">{"\u00B7"} {timeAgo(post.timestamp)}</span>
                    </div>
                    {post.subreddit && (
                      <span className="text-orange-400 text-xs">r/{post.subreddit}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <PlatformIcon className={cn('w-4 h-4', platformColors[post.platform])} />
                    {post.url && (
                      <a href={post.url} target="_blank" rel="noopener noreferrer" className="p-1 rounded-lg hover:bg-white/10 text-zinc-500">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>

                {/* Content */}
                <p className="mt-3 text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {post.content}
                </p>

                {/* Media Grid */}
                {post.media && post.media.length > 0 && post.media[0].url && (
                  <div className={cn(
                    'mt-3 rounded-xl overflow-hidden',
                    post.media.length > 1 ? 'grid gap-1' : '',
                    post.media.length === 2 ? 'grid-cols-2' : '',
                    post.media.length === 3 ? 'grid-cols-2' : '',
                    post.media.length >= 4 ? 'grid-cols-2' : ''
                  )}>
                    {post.media.slice(0, 4).map((m, mi) => (
                      m.type?.startsWith('video') ? (
                        <video key={mi} src={m.url} controls className="w-full max-h-80 object-cover rounded-xl" />
                      ) : (
                        <img key={mi} src={m.url} alt="" className={cn(
                          'w-full object-cover',
                          post.media.length === 1 ? 'max-h-80 rounded-xl' : 'aspect-square rounded-lg',
                          post.media.length === 3 && mi === 0 ? 'row-span-2 h-full' : ''
                        )} />
                      )
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center gap-5">
                    <button
                      onClick={() => handleLike(post)}
                      className={cn(
                        'flex items-center gap-1.5 transition-colors text-xs',
                        likedPosts.has(postKey) ? 'text-red-400' : 'text-zinc-500 hover:text-red-400'
                      )}
                      title="Like"
                    >
                      <Heart className={cn('w-4 h-4', likedPosts.has(postKey) && 'fill-current')} />
                      {post.likes > 0 && formatCount(post.likes)}
                    </button>
                    <button
                      onClick={() => {
                        if (commentingOn === post.id) {
                          setCommentingOn(null);
                        } else {
                          setCommentingOn(post.id);
                          setTimeout(() => commentRef.current?.focus(), 100);
                        }
                      }}
                      className={cn(
                        'flex items-center gap-1.5 transition-colors text-xs',
                        commentingOn === post.id ? 'text-blue-400' : 'text-zinc-500 hover:text-blue-400'
                      )}
                      title="Comment"
                    >
                      <MessageCircle className="w-4 h-4" />
                      {post.comments > 0 && formatCount(post.comments)}
                    </button>
                    <button
                      onClick={() => handleRepost(post)}
                      className="flex items-center gap-1.5 text-zinc-500 hover:text-green-400 transition-colors text-xs"
                      title="Repost / Share"
                    >
                      <Share2 className="w-4 h-4" />
                      {post.shares > 0 && formatCount(post.shares)}
                    </button>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSummarizePost(post)}
                      disabled={summarizingPost === postKey}
                      className={cn(
                        'p-1.5 rounded-lg transition-colors',
                        postSummaries[postKey]
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-zinc-500 hover:text-brand-400 hover:bg-white/10'
                      )}
                      title="AI Summary"
                    >
                      {summarizingPost === postKey ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => toggleSave(post.id)}
                      className={cn(
                        'p-1.5 rounded-lg transition-colors',
                        savedPosts.has(post.id)
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-zinc-500 hover:text-white hover:bg-white/10'
                      )}
                    >
                      <Bookmark className={cn('w-4 h-4', savedPosts.has(post.id) && 'fill-current')} />
                    </button>
                  </div>
                </div>

                {/* AI Summary */}
                <AnimatePresence>
                  {postSummaries[postKey] && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 p-3 rounded-xl bg-brand-500/5 border border-brand-500/10">
                        <div className="flex items-start gap-2">
                          <Sparkles className="w-3.5 h-3.5 text-brand-400 mt-0.5 flex-shrink-0" />
                          <p className="text-sm text-zinc-300">{postSummaries[postKey]}</p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Comment Input */}
                <AnimatePresence>
                  {commentingOn === post.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 flex items-center gap-2">
                        <input
                          ref={commentRef}
                          value={commentText}
                          onChange={e => setCommentText(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter' && commentText.trim()) handleComment(post); }}
                          placeholder={`Reply on ${post.platform}...`}
                          className="flex-1 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder-zinc-500 outline-none focus:border-brand-500"
                        />
                        <button
                          onClick={() => handleComment(post)}
                          disabled={!commentText.trim()}
                          className="p-2 rounded-lg bg-brand-600 text-white hover:bg-brand-500 disabled:opacity-40 transition-colors"
                        >
                          <Send className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setCommentingOn(null); setCommentText(''); }}
                          className="p-2 rounded-lg text-zinc-500 hover:text-white hover:bg-white/10 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
