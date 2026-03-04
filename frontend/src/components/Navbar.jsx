import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LogOut, Activity, LayoutDashboard, BrainCircuit, User } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
    const { user, logout } = useAuth();
    const location = useLocation();

    const navItems = [
        { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
        { path: '/activities', label: 'Activities', icon: Activity },
        { path: '/ai-coach', label: 'AI Coach', icon: BrainCircuit },
        { path: '/profile', label: 'Profile', icon: User },
    ];

    if (!user) return null;

    return (
        <nav className="glass fixed bottom-8 left-1/2 -translate-x-1/2 px-8 py-4 rounded-3xl flex items-center gap-10 z-50 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-white/10 transition-all duration-500 hover:bottom-10">
            {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`flex flex-col items-center gap-1.5 transition-all duration-300 group ${isActive ? 'text-primary scale-110' : 'text-slate-400 hover:text-white'
                            }`}
                    >
                        <div className={`p-2 rounded-xl transition-all duration-300 ${isActive ? 'bg-primary/10 shadow-[0_0_20px_rgba(139,92,246,0.2)]' : 'group-hover:bg-white/5'}`}>
                            <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                        </div>
                        <span className={`text-[10px] font-bold uppercase tracking-widest transition-all ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>{item.label}</span>
                    </Link>
                );
            })}
            <div className="w-[1px] h-8 bg-white/10 mx-2" />
            <button
                onClick={logout}
                className="flex flex-col items-center gap-1.5 text-slate-400 hover:text-rose-400 transition-all duration-300 group"
            >
                <div className="p-2 rounded-xl group-hover:bg-rose-400/10 transition-all">
                    <LogOut size={22} />
                </div>
                <span className="text-[10px] font-bold uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">Logout</span>
            </button>
        </nav>
    );

};

export default Navbar;
