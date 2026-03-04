import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';
import { User, Mail, Shield, Bell, Settings, LogOut, Camera, ChevronRight } from 'lucide-react';

const Profile = () => {
    const { user, logout } = useAuth();
    const [activeTab, setActiveTab] = useState('profile');

    const menuItems = [
        { id: 'profile', label: 'Basic Info', icon: User },
        { id: 'security', label: 'Security', icon: Shield },
        { id: 'notifications', label: 'Notifications', icon: Bell },
        { id: 'settings', label: 'General Settings', icon: Settings },
    ];

    return (
        <div className="max-w-4xl mx-auto px-6 pt-12 pb-32">
            <header className="mb-16 relative">
                <div className="absolute -top-10 -left-10 w-40 h-40 bg-secondary/10 rounded-full blur-3xl"></div>
                <h1 className="text-5xl font-bold mb-4 tracking-tighter">My <span className="gradient-text">Profile</span></h1>
                <p className="text-slate-400 text-lg font-medium">Manage your personal settings and preferences.</p>
            </header>


            <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-8">
                {/* Sidebar */}
                <div className="space-y-2">
                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeTab === item.id;
                        return (
                            <button
                                key={item.id}
                                onClick={() => setActiveTab(item.id)}
                                className={`w-full flex items-center justify-between p-4 rounded-xl transition-all ${isActive ? 'bg-primary text-white shadow-glow' : 'hover:bg-surface-hover text-text-muted hover:text-text'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <Icon size={20} />
                                    <span className="font-semibold">{item.label}</span>
                                </div>
                                {isActive && <ChevronRight size={16} />}
                            </button>
                        );
                    })}

                    <div className="pt-4 mt-8 border-t border-white/5">
                        <button
                            onClick={logout}
                            className="w-full flex items-center gap-3 p-4 rounded-xl text-secondary hover:bg-secondary/10 transition-all font-semibold"
                        >
                            <LogOut size={20} />
                            Logout
                        </button>
                    </div>
                </div>

                {/* Content */}
                <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="card"
                >
                    {activeTab === 'profile' && (
                        <div className="space-y-8">
                            <div className="relative w-32 h-32 mx-auto md:mx-0">
                                <div className="w-full h-full rounded-3xl bg-gradient-to-br from-primary to-secondary p-1">
                                    <div className="w-full h-full rounded-[calc(1.5rem-2px)] bg-surface flex items-center justify-center text-4xl font-bold text-primary">
                                        {user?.username?.[0]?.toUpperCase() || 'U'}
                                    </div>
                                </div>
                                <button className="absolute -bottom-2 -right-2 p-2 bg-primary text-white rounded-xl shadow-lg hover:scale-110 transition-transform">
                                    <Camera size={16} />
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-text-muted uppercase tracking-widest ml-1">Full Name</label>
                                    <div className="flex items-center gap-3 p-4 bg-surface-hover/50 border border-border rounded-2xl">
                                        <User size={18} className="text-primary" />
                                        <span className="font-medium">{user?.firstName} {user?.lastName}</span>
                                    </div>
                                </div>
                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-text-muted uppercase tracking-widest ml-1">Email Address</label>
                                    <div className="flex items-center gap-3 p-4 bg-surface-hover/50 border border-border rounded-2xl">
                                        <Mail size={18} className="text-primary" />
                                        <span className="font-medium">{user?.email || 'user@example.com'}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-8 border-t border-white/5">
                                <h3 className="text-xl font-bold mb-4">Fitness Goals</h3>
                                <div className="flex flex-wrap gap-2">
                                    {['Weight Loss', 'Muscle Gain', 'Endurance'].map(goal => (
                                        <span key={goal} className="px-4 py-2 rounded-full glass border-white/5 text-sm font-medium">
                                            {goal}
                                        </span>
                                    ))}
                                    <button className="px-4 py-2 rounded-full border border-primary/30 text-primary text-sm font-bold hover:bg-primary/5 transition-all">
                                        + Add Goal
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab !== 'profile' && (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <Settings className="text-text-muted mb-4 opacity-20" size={64} />
                            <h3 className="text-2xl font-bold mb-2">{activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Settings</h3>
                            <p className="text-text-muted max-w-xs">These settings are currently under development and will be available soon.</p>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    );
};

export default Profile;
