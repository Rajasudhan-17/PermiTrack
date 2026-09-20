import React, { useState, useRef, useEffect } from 'react';
import { User, LogOut, RefreshCw, Settings, ChevronDown } from 'lucide-react';
import { Badge } from '../ui/Badge';

export interface UserMenuProps {
  userName: string;
  userRole: 'student' | 'faculty' | 'mentor' | 'hod' | 'admin' | 'event_coordinator' | string;
  userEmail?: string;
  onSwitchRole?: () => void;
  onLogout?: () => void;
  onNavigate?: (path: string) => void;
  className?: string;
}

export const UserMenu: React.FC<UserMenuProps> = ({
  userName = 'Rajasudhan R',
  userRole = 'student',
  userEmail,
  onSwitchRole,
  onLogout = () => {},
  onNavigate,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNavigate = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    setIsOpen(false);
    if (onNavigate) {
      onNavigate(path);
    } else {
      window.history.pushState({}, '', path);
      window.dispatchEvent(new Event('popstate'));
    }
  };

  const getInitial = (name: string) => {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name[0].toUpperCase();
  };

  const initial = getInitial(userName);

  return (
    <div ref={menuRef} className={`relative inline-block ${className}`}>
      {/* Trigger Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 p-1.5 pl-2 pr-3 rounded-pill bg-surface-elevated hover:bg-[#1A384C] border border-border transition-all focus:outline-none focus:ring-2 focus:ring-primary/40 min-h-[44px]"
        aria-label="User profile menu"
        aria-expanded={isOpen}
      >
        {/* Avatar Circle */}
        <div className="w-7 h-7 rounded-full bg-primary text-[#07151F] font-bold text-xs flex items-center justify-center shrink-0">
          {initial}
        </div>

        {/* Name & Role Text */}
        <div className="hidden sm:flex flex-col text-left">
          <span className="text-xs font-semibold text-text-primary leading-tight max-w-[120px] truncate">
            {userName}
          </span>
          <span className="text-[10px] text-text-muted capitalize">
            {userRole}
          </span>
        </div>

        <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-60 bg-surface border border-border rounded-xl shadow-lg py-2 z-50 animate-fadeIn">
          {/* Menu User Header */}
          <div className="px-4 py-2.5 border-b border-border/60">
            <p className="text-sm font-semibold text-text-primary truncate">{userName}</p>
            {userEmail && <p className="text-xs text-text-muted truncate">{userEmail}</p>}
            <div className="mt-2">
              <Badge variant="primary" size="sm">
                {userRole.toUpperCase()}
              </Badge>
            </div>
          </div>

          {/* Actions */}
          <div className="py-1">
            <a
              href="/profile"
              onClick={(e) => handleNavigate('/profile', e)}
              className="flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-elevated transition-colors"
            >
              <User className="w-4 h-4 text-primary" />
              <span>My Profile</span>
            </a>

            {(userRole === 'faculty' || userRole === 'mentor') && (
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  if (onSwitchRole) onSwitchRole();
                }}
                className="w-full flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-primary hover:bg-primary-subtle transition-colors text-left"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Switch to {userRole === 'faculty' ? 'MENTOR' : 'FACULTY'}</span>
              </button>
            )}
          </div>

          {/* Logout */}
          <div className="pt-1 border-t border-border/60">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                if (onLogout) onLogout();
              }}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-xs font-medium text-danger hover:bg-danger-subtle transition-colors text-left"
            >
              <LogOut className="w-4 h-4" />
              <span>Log Out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
