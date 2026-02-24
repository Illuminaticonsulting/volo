'use client';

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { X, Mic, MicOff, Volume2, VolumeX, Phone } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chatStore';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface VoiceModeProps {
  isOpen: boolean;
  onClose: () => void;
}

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';

export function VoiceMode({ isOpen, onClose }: VoiceModeProps) {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [isTTSEnabled, setIsTTSEnabled] = useState(true);
  const [amplitude, setAmplitude] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);

  const recognitionRef = useRef<any>(null);
  const synthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number>(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isOpenRef = useRef(isOpen);

  // Keep ref in sync
  useEffect(() => {
    isOpenRef.current = isOpen;
  }, [isOpen]);

  // Timer for elapsed time
  useEffect(() => {
    if (isOpen && voiceState !== 'idle') {
      timerRef.current = setInterval(() => {
        setElapsedTime((t) => t + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isOpen, voiceState]);

  // Audio amplitude analysis for orb animation
  const startAudioAnalysis = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((sum, v) => sum + v, 0) / dataArray.length;
        setAmplitude(avg / 128); // normalize to 0-2 range
        animFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // Fallback: no amplitude visualization
    }
  }, []);

  const stopAudioAnalysis = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAmplitude(0);
  }, []);

  const stopEverything = useCallback(() => {
    // Stop recognition
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
    // Stop TTS
    if (typeof speechSynthesis !== 'undefined') {
      speechSynthesis.cancel();
    }
    // Stop audio analysis
    stopAudioAnalysis();
    // Abort any pending request
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, [stopAudioAnalysis]);

  // Cleanup on close
  useEffect(() => {
    if (!isOpen) {
      stopEverything();
      setTranscript('');
      setResponse('');
      setElapsedTime(0);
      setVoiceState('idle');
    }
  }, [isOpen, stopEverything]);

  // Start listening
  const startListening = useCallback(async () => {
    const w = window as any;
    const SpeechRecognition = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.error('Speech recognition not supported');
      return;
    }

    // Cancel any ongoing TTS
    if (typeof speechSynthesis !== 'undefined') speechSynthesis.cancel();

    // Don't listen if muted
    if (isMuted) {
      setVoiceState('idle');
      return;
    }

    setVoiceState('listening');
    setTranscript('');
    setResponse('');

    await startAudioAnalysis();

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    let finalTranscript = '';
    let silenceTimer: NodeJS.Timeout | null = null;

    recognition.onresult = (event: any) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += t + ' ';
        } else {
          interim = t;
        }
      }
      setTranscript(finalTranscript + interim);

      // Auto-send after 2s of silence following a final result
      if (silenceTimer) clearTimeout(silenceTimer);
      if (finalTranscript.trim()) {
        silenceTimer = setTimeout(() => {
          recognition.stop();
        }, 2000);
      }
    };

    recognition.onerror = (event: any) => {
      if (event.error !== 'aborted') {
        console.error('Voice error:', event.error);
      }
    };

    recognition.onend = () => {
      stopAudioAnalysis();
      const text = finalTranscript.trim();
      if (text) {
        processVoiceInput(text);
      } else {
        setVoiceState('idle');
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [startAudioAnalysis, stopAudioAnalysis, isMuted]);

  // Process voice input — send to AI and speak response
  const processVoiceInput = useCallback(async (text: string) => {
    setVoiceState('processing');
    setResponse('');

    // Add user message to chat store immediately
    const userMsg = {
      id: `voice-${Date.now()}-u`,
      role: 'user' as const,
      content: text,
      timestamp: new Date(),
      status: 'sent' as const,
    };
    useChatStore.setState((state) => ({
      messages: [...state.messages, userMsg],
    }));

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await api.stream('/api/chat', {
        message: text,
        conversation_id: useChatStore.getState().conversationId,
        messages: useChatStore.getState().messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
      }, controller.signal);

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      if (reader) {
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') continue;
              try {
                const parsed = JSON.parse(data);
                if (parsed.content) {
                  fullResponse += parsed.content;
                  setResponse(fullResponse);
                }
                if (parsed.conversation_id) {
                  useChatStore.setState({ conversationId: parsed.conversation_id });
                }
              } catch {}
            }
          }
        }
      }

      // Speak the response
      if (isTTSEnabled && fullResponse && typeof speechSynthesis !== 'undefined') {
        setVoiceState('speaking');
        // Simulate amplitude during speech
        const speakInterval = setInterval(() => {
          setAmplitude(0.3 + Math.random() * 0.8);
        }, 100);

        await speakText(fullResponse);
        clearInterval(speakInterval);
        setAmplitude(0);
      }

      // Add assistant message to chat store
      const assistantMsg = {
        id: `voice-${Date.now()}-a`,
        role: 'assistant' as const,
        content: fullResponse,
        timestamp: new Date(),
        status: 'sent' as const,
      };
      useChatStore.setState((state) => ({
        messages: [...state.messages, assistantMsg],
      }));

      // After speaking, auto-listen again (hands-free loop)
      if (isOpenRef.current) {
        setVoiceState('idle');
        setTimeout(() => {
          if (isOpenRef.current) startListening();
        }, 500);
      }
    } catch (err: any) {
      if (err?.name === 'AbortError') return;
      setResponse('Sorry, I had trouble processing that. Tap to try again.');
      setVoiceState('idle');
    }
  }, [isTTSEnabled, startListening]);

  // TTS helper
  const speakText = (text: string): Promise<void> => {
    return new Promise((resolve) => {
      if (typeof speechSynthesis === 'undefined') { resolve(); return; }

      // Clean markdown for TTS
      const clean = text
        .replace(/```[\s\S]*?```/g, 'code block omitted')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/#{1,6}\s/g, '')
        .replace(/\n{2,}/g, '. ')
        .replace(/\n/g, ' ');

      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      // Try to find a good voice
      const voices = speechSynthesis.getVoices();
      const preferred = voices.find((v) =>
        v.name.includes('Samantha') || v.name.includes('Karen') ||
        v.name.includes('Daniel') || v.name.includes('Google')
      ) || voices.find((v) => v.lang.startsWith('en'));
      if (preferred) utterance.voice = preferred;

      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      synthRef.current = utterance;
      speechSynthesis.speak(utterance);
    });
  };

  const handleMicToggle = () => {
    if (voiceState === 'listening') {
      if (recognitionRef.current) recognitionRef.current.stop();
      stopAudioAnalysis();
      setVoiceState('idle');
    } else if (voiceState === 'idle') {
      startListening();
    } else if (voiceState === 'speaking') {
      speechSynthesis.cancel();
      setVoiceState('idle');
      setTimeout(() => startListening(), 300);
    }
  };

  const handleClose = () => {
    stopEverything();
    onClose();
  };

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  const orbScale = 1 + amplitude * 0.3;
  const orbGlow = amplitude * 40;

  return (
    <div className="fixed inset-0 z-[100] bg-surface-dark-0 flex flex-col items-center justify-center animate-fade-in">
      {/* Background gradient pulse */}
      <div
        className="absolute inset-0 transition-opacity duration-500"
        style={{
          background: `radial-gradient(circle at 50% 40%, rgba(92,124,250,${0.05 + amplitude * 0.08}) 0%, transparent 70%)`,
        }}
      />

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-6 py-4 z-10">
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-2 h-2 rounded-full',
            voiceState === 'listening' ? 'bg-emerald-400 animate-pulse' :
            voiceState === 'processing' ? 'bg-amber-400 animate-pulse' :
            voiceState === 'speaking' ? 'bg-brand-400 animate-pulse' :
            'bg-zinc-600'
          )} />
          <span className="text-xs text-zinc-400 font-medium">
            {voiceState === 'listening' ? 'Listening...' :
             voiceState === 'processing' ? 'Processing...' :
             voiceState === 'speaking' ? 'Speaking...' :
             'Ready'}
          </span>
          {elapsedTime > 0 && (
            <span className="text-xs text-zinc-600">{formatTime(elapsedTime)}</span>
          )}
        </div>
        <button
          onClick={handleClose}
          className="p-2 rounded-full hover:bg-white/5 transition-colors"
          aria-label="Close voice mode"
        >
          <X className="w-5 h-5 text-zinc-400" />
        </button>
      </div>

      {/* Animated Orb */}
      <div className="relative mb-12">
        {/* Outer glow rings */}
        <div
          className="absolute inset-0 rounded-full transition-all duration-150"
          style={{
            transform: `scale(${orbScale * 1.4})`,
            boxShadow: `0 0 ${orbGlow * 2}px ${orbGlow}px rgba(92,124,250,0.1)`,
            width: 160,
            height: 160,
            marginLeft: -80 + 60,
            marginTop: -80 + 60,
          }}
        />
        <div
          className="absolute inset-0 rounded-full transition-all duration-150"
          style={{
            transform: `scale(${orbScale * 1.2})`,
            boxShadow: `0 0 ${orbGlow}px ${orbGlow / 2}px rgba(92,124,250,0.15)`,
            width: 140,
            height: 140,
            marginLeft: -70 + 60,
            marginTop: -70 + 60,
          }}
        />
        {/* Main orb */}
        <div
          className={cn(
            'w-[120px] h-[120px] rounded-full flex items-center justify-center transition-all duration-150 cursor-pointer',
            voiceState === 'listening' && 'shadow-[0_0_60px_20px_rgba(52,211,153,0.2)]',
            voiceState === 'processing' && 'shadow-[0_0_60px_20px_rgba(251,191,36,0.15)]',
            voiceState === 'speaking' && 'shadow-[0_0_60px_20px_rgba(92,124,250,0.25)]',
          )}
          style={{
            transform: `scale(${orbScale})`,
            background: voiceState === 'listening'
              ? 'linear-gradient(135deg, #34d399, #059669)'
              : voiceState === 'processing'
              ? 'linear-gradient(135deg, #fbbf24, #d97706)'
              : voiceState === 'speaking'
              ? 'linear-gradient(135deg, #818cf8, #5c7cfa)'
              : 'linear-gradient(135deg, #5c7cfa, #4338ca)',
          }}
          onClick={handleMicToggle}
        >
          {voiceState === 'processing' ? (
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-white/80 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2.5 h-2.5 rounded-full bg-white/80 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2.5 h-2.5 rounded-full bg-white/80 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          ) : voiceState === 'speaking' ? (
            <Volume2 className="w-10 h-10 text-white/90" />
          ) : (
            <Mic className={cn('w-10 h-10', voiceState === 'listening' ? 'text-white animate-pulse' : 'text-white/90')} />
          )}
        </div>
      </div>

      {/* Transcript / Response text */}
      <div className="max-w-lg mx-auto px-6 text-center space-y-4 min-h-[120px]">
        {transcript && (
          <div className="animate-fade-in">
            <p className="text-xs text-zinc-500 mb-1">You said</p>
            <p className="text-lg text-white font-medium leading-relaxed">{transcript}</p>
          </div>
        )}
        {response && (
          <div className="animate-fade-in">
            <p className="text-xs text-zinc-500 mb-1">Volo</p>
            <p className="text-sm text-zinc-300 leading-relaxed max-h-[200px] overflow-y-auto">
              {response}
            </p>
          </div>
        )}
        {voiceState === 'idle' && !transcript && !response && (
          <p className="text-zinc-500 text-sm">Tap the orb to start talking</p>
        )}
      </div>

      {/* Bottom controls */}
      <div className="absolute bottom-0 left-0 right-0 flex items-center justify-center gap-6 pb-12 safe-area-bottom">
        {/* Mute toggle */}
        <button
          onClick={() => setIsMuted(!isMuted)}
          className={cn(
            'w-14 h-14 rounded-full flex items-center justify-center transition-all',
            isMuted ? 'bg-red-500/20 text-red-400' : 'bg-white/5 text-zinc-400 hover:bg-white/10'
          )}
          aria-label={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
        </button>

        {/* End call */}
        <button
          onClick={handleClose}
          className="w-16 h-16 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-all shadow-lg shadow-red-500/30 active:scale-95"
          aria-label="End voice chat"
        >
          <Phone className="w-7 h-7 text-white rotate-[135deg]" />
        </button>

        {/* TTS toggle */}
        <button
          onClick={() => {
            setIsTTSEnabled(!isTTSEnabled);
            if (isTTSEnabled && typeof speechSynthesis !== 'undefined') {
              speechSynthesis.cancel();
            }
          }}
          className={cn(
            'w-14 h-14 rounded-full flex items-center justify-center transition-all',
            !isTTSEnabled ? 'bg-zinc-700 text-zinc-500' : 'bg-white/5 text-zinc-400 hover:bg-white/10'
          )}
          aria-label={isTTSEnabled ? 'Disable voice response' : 'Enable voice response'}
        >
          {isTTSEnabled ? <Volume2 className="w-6 h-6" /> : <VolumeX className="w-6 h-6" />}
        </button>
      </div>
    </div>
  );
}
