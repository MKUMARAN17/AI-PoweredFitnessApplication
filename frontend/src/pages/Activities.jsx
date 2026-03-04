import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Plus, Search, Filter, Calendar, Zap, HardHat, TrendingUp, Activity } from 'lucide-react';
import { activityService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Activities = () => {
    const { user } = useAuth();
    const [activities, setActivities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [newActivity, setNewActivity] = useState({
        type: 'Running',
        value: '',
        unit: 'km',
        timestamp: new Date().toISOString().split('T')[0]
    });

    useEffect(() => {
        if (user?.id) {
            fetchActivities();
        }
    }, [user]);

    const fetchActivities = async () => {
        try {
            const res = await activityService.getActivities(user.id);
            setActivities(res.data);
        } catch (err) {
            console.error('Error fetching activities:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (e) => {
        e.preventDefault();
        try {
            await activityService.addActivity({ ...newActivity, userId: user.id });
            setShowAddModal(false);
            fetchActivities();
        } catch (err) {
            alert('Failed to log activity');
        }
    };

    return (
        <div className="max-w-5xl mx-auto px-6 pt-12 pb-32">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-8 mb-16 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-accent/10 rounded-full blur-3xl"></div>
                <div>
                    <h1 className="text-5xl font-bold mb-4 tracking-tighter">Activity <span className="gradient-text">History</span></h1>
                    <p className="text-slate-400 text-lg font-medium">Keep track of every step, rep, and breath.</p>
                </div>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="btn-primary group"
                >
                    <Plus size={20} className="group-hover:rotate-90 transition-transform" /> Log Activity
                </button>
            </header>


            {/* Stats Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
                <div className="glass p-6 rounded-2xl border-white/5">
                    <p className="text-text-muted text-sm uppercase font-bold tracking-tighter mb-1">Total Distance</p>
                    <p className="text-2xl font-bold">128.4 km</p>
                    <div className="mt-2 text-xs text-accent flex items-center gap-1">
                        <TrendingUp size={12} /> +12% from last week
                    </div>
                </div>
                <div className="glass p-6 rounded-2xl border-white/5">
                    <p className="text-text-muted text-sm uppercase font-bold tracking-tighter mb-1">Active Minutes</p>
                    <p className="text-2xl font-bold">420m</p>
                    <div className="mt-2 text-xs text-primary flex items-center gap-1">
                        On track for weekly goal
                    </div>
                </div>
            </div>

            {/* Activity List */}
            <div className="space-y-4">
                {loading ? (
                    [1, 2, 3].map(i => <div key={i} className="h-24 glass rounded-2xl animate-pulse"></div>)
                ) : activities.length > 0 ? (
                    activities.map((act, i) => (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            key={i}
                            className="glass p-6 rounded-2xl border-white/5 flex items-center justify-between group hover:border-primary/30 transition-all"
                        >
                            <div className="flex items-center gap-6">
                                <div className="p-4 bg-surface-hover rounded-2xl text-primary group-hover:bg-primary group-hover:text-white transition-all">
                                    {act.type === 'Running' ? <Zap size={24} /> : <HardHat size={24} />}
                                </div>
                                <div>
                                    <div className="flex items-center gap-3">
                                        <h3 className="text-xl font-bold">{act.type}</h3>
                                        <span className="px-2 py-0.5 rounded-full bg-surface-hover text-[10px] font-bold uppercase text-text-muted border border-border">
                                            {act.unit}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 mt-1 text-sm text-text-muted">
                                        <span className="flex items-center gap-1"><Calendar size={14} /> {new Date(act.timestamp).toLocaleDateString()}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-3xl font-bold">{act.value}</p>
                                <p className="text-xs text-text-muted font-medium">{act.unit} achieved</p>
                            </div>
                        </motion.div>
                    ))
                ) : (
                    <div className="glass p-12 rounded-3xl text-center border-dashed border-2 border-border/50">
                        <Activity className="mx-auto text-text-muted mb-4 opacity-20" size={64} />
                        <p className="text-xl font-bold text-text-muted mb-4">No activities found</p>
                        <button onClick={() => setShowAddModal(true)} className="btn-outline">Log your first activity</button>
                    </div>
                )}
            </div>

            {/* Add Activity Modal (Simplified) */}
            {showAddModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="glass p-8 rounded-3xl w-full max-w-md shadow-2xl relative"
                    >
                        <h2 className="text-2xl font-bold mb-6">Log New Activity</h2>
                        <form onSubmit={handleAdd} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-text-muted mb-1">Activity Type</label>
                                <select
                                    className="w-full bg-surface/50 border border-border rounded-xl p-3 outline-none"
                                    value={newActivity.type}
                                    onChange={e => setNewActivity({ ...newActivity, type: e.target.value })}
                                >
                                    <option className="bg-surface text-text">Running</option>
                                    <option className="bg-surface text-text">Swimming</option>
                                    <option className="bg-surface text-text">Cycling</option>
                                    <option className="bg-surface text-text">Weightlifting</option>
                                    <option className="bg-surface text-text">Yoga</option>
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-text-muted mb-1">Value</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        required
                                        className="w-full bg-surface/50 border border-border rounded-xl p-3 outline-none"
                                        value={newActivity.value}
                                        onChange={e => setNewActivity({ ...newActivity, value: e.target.value })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-text-muted mb-1">Unit</label>
                                    <input
                                        type="text"
                                        className="w-full bg-surface/50 border border-border rounded-xl p-3 outline-none"
                                        value={newActivity.unit}
                                        onChange={e => setNewActivity({ ...newActivity, unit: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="flex gap-4 mt-8">
                                <button type="button" onClick={() => setShowAddModal(false)} className="flex-1 btn-outline">Cancel</button>
                                <button type="submit" className="flex-1 btn-primary">Log Activity</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default Activities;
