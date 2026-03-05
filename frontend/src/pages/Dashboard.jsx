import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Flame, Clock, TrendingUp, Plus, BrainCircuit } from 'lucide-react';
import { activityService, aiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Dashboard = () => {
    const { user } = useAuth();
    const [activities, setActivities] = useState([]);
    const [suggestions, setSuggestions] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [actRes, aiRes] = await Promise.all([
                    activityService.getActivities(user.id),
                    aiService.getSuggestions({ userId: user.id })
                ]);
                setActivities(actRes.data.slice(0, 5));
                setSuggestions(aiRes.data);
            } catch (err) {
                console.error('Error fetching dashboard data:', err);
            } finally {
                setLoading(false);
            }
        };

        if (user?.id) fetchData();
    }, [user]);

    const stats = [
        { label: 'Steps Today', value: '8,432', icon: Activity, color: 'text-sky-400' },
        { label: 'Calories', value: '450 kcal', icon: Flame, color: 'text-orange-400' },
        { label: 'Workout', value: '45 min', icon: Clock, color: 'text-cyan-400' },
    ];

    return (
        <div className="max-w-5xl mx-auto px-6 pt-12 pb-32">
            <header className="mb-16 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-primary/10 rounded-full blur-3xl animate-pulse"></div>
                <h1 className="text-6xl font-bold mb-4 tracking-tighter">
                    Hello, <span className="gradient-text">{user?.username || 'Athlete'}</span>
                </h1>
                <p className="text-slate-400 text-xl font-medium">Ready to crush your goals today?</p>
            </header>


            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                {stats.map((stat, i) => (
                    <motion.div
                        key={stat.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="card group overflow-hidden relative"
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-text-muted text-sm font-medium uppercase tracking-wider mb-2">{stat.label}</p>
                                <p className="text-3xl font-bold">{stat.value}</p>
                            </div>
                            <div className={`p-4 rounded-2xl bg-surface-hover ${stat.color} group-hover:scale-110 transition-transform`}>
                                <stat.icon size={28} />
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* AI Suggestions */}
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="card border-primary/20 bg-primary/5"
                >
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-primary rounded-lg text-white">
                            <BrainCircuit size={20} />
                        </div>
                        <h2 className="text-2xl font-bold">AI Recommendations</h2>
                    </div>
                    {loading ? (
                        <div className="animate-pulse space-y-4">
                            <div className="h-4 bg-surface rounded w-3/4"></div>
                            <div className="h-4 bg-surface rounded w-1/2"></div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <p className="text-text-muted leading-relaxed">
                                {suggestions?.message || "Great progress! Based on your recent activities, you're on track to hit your weekly goal. Consider a 30-minute HIIT session tomorrow."}
                            </p>
                            <button className="btn-primary w-full mt-4">Generate New Plan</button>
                        </div>
                    )}
                </motion.div>

                {/* Recent Activities */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="card"
                >
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold">Recent History</h2>
                        <button className="text-primary hover:underline font-medium">View All</button>
                    </div>
                    <div className="space-y-4">
                        {activities.length > 0 ? (
                            activities.map((act, i) => (
                                <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-surface-hover/50 hover:bg-surface-hover transition-colors">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2 bg-green-500/10 text-green-400 rounded-lg">
                                            <TrendingUp size={20} />
                                        </div>
                                        <div>
                                            <p className="font-bold">{act.type}</p>
                                            <p className="text-xs text-text-muted">{new Date(act.timestamp).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                    <p className="font-bold text-lg">{act.value} {act.unit}</p>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-8 text-text-muted">
                                No activities logged yet.
                                <button className="block mx-auto mt-4 btn-outline flex items-center gap-2">
                                    <Plus size={18} /> Log First Activity
                                </button>
                            </div>
                        )}
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

export default Dashboard;
