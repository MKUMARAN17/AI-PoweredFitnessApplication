import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Sparkles, Send, Loader2, Bot, User, CheckCircle2, ChevronRight } from 'lucide-react';
import { aiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const AICoach = () => {
    const { user } = useAuth();
    const [messages, setMessages] = useState([
        { role: 'ai', content: `Hello ${user?.username}! I'm your FitAI Coach. How can I help you reach your fitness goals today?` }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setInput('');
        setLoading(true);

        try {
            const res = await aiService.getSuggestions({
                userId: user.id,
                prompt: userMsg
            });
            setMessages(prev => [...prev, { role: 'ai', content: res.data.message || res.data.suggestion || "Here's your plan!" }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'ai', content: "I'm having trouble connecting to my brain right now. Please try again in a moment!" }]);
        } finally {
            setLoading(false);
        }
    };

    const quickPrompts = [
        "What's my workout for today?",
        "Give me a 5-minute warm-up routine.",
        "Show my progress from last week.",
        "Suggest a high-protein meal."
    ];

    return (
        <div className="max-w-4xl mx-auto px-6 pt-12 pb-40 h-[calc(100vh-80px)] flex flex-col">
            <header className="flex items-center gap-6 mb-12 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-primary/10 rounded-full blur-3xl animate-pulse"></div>
                <div className="p-4 bg-primary rounded-3xl shadow-glow relative">
                    <BrainCircuit size={32} className="text-white" />
                    <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-4 border-slate-900"></div>
                </div>
                <div>
                    <h1 className="text-4xl font-bold tracking-tighter">FitAI <span className="gradient-text">Coach</span></h1>
                    <p className="text-slate-400 text-sm font-medium flex items-center gap-2">
                        <Sparkles size={14} className="text-[#10B981]" /> Online & ready to help
                    </p>
                </div>
            </header>


            {/* Chat Area */}
            <div className="flex-1 glass rounded-3xl p-6 overflow-y-auto space-y-6 mb-6 scrollbar-hide border-white/5 relative">
                <AnimatePresence>
                    {messages.map((msg, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            className={`flex ${msg.role === 'ai' ? 'justify-start' : 'justify-end'}`}
                        >
                            <div className={`flex gap-4 max-w-[85%] ${msg.role === 'ai' ? 'flex-row' : 'flex-row-reverse'}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'ai' ? 'bg-primary text-white' : 'bg-surface-hover text-primary border border-primary/20'
                                    }`}>
                                    {msg.role === 'ai' ? <Bot size={18} /> : <User size={18} />}
                                </div>
                                <div className={`p-4 rounded-2xl ${msg.role === 'ai'
                                    ? 'bg-surface/50 border border-white/5 text-text'
                                    : 'bg-primary text-white shadow-lg'
                                    }`}>
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                    {loading && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                            <div className="flex gap-4 bg-surface/30 p-4 rounded-2xl">
                                <Loader2 className="animate-spin text-primary" size={20} />
                                <span className="text-sm text-text-muted">Analyzing your data...</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Quick Prompts */}
            <div className="flex gap-2 overflow-x-auto pb-4 scrollbar-hide">
                {quickPrompts.map((p, i) => (
                    <button
                        key={i}
                        onClick={() => setInput(p)}
                        className="whitespace-nowrap px-4 py-2 rounded-full glass border-white/10 text-xs font-semibold hover:border-primary transition-all text-text-muted hover:text-text"
                    >
                        {p}
                    </button>
                ))}
            </div>

            {/* Input Area */}
            <form onSubmit={handleSend} className="relative">
                <input
                    type="text"
                    placeholder="Ask your coach anything..."
                    className="w-full glass bg-surface/50 border border-white/10 rounded-2xl py-4 pl-6 pr-16 outline-none focus:border-primary/50 transition-all text-lg"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
                <button
                    type="submit"
                    className="absolute right-3 top-1/2 -translate-y-1/2 btn-primary p-3 rounded-xl disabled:opacity-50"
                    disabled={!input.trim() || loading}
                >
                    <Send size={20} />
                </button>
            </form>
        </div>
    );
};

export default AICoach;
