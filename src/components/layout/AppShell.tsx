import React from 'react';
import { Navbar, NavbarProps } from './Navbar';
import { PageContainer } from './PageContainer';

export interface AppShellProps extends NavbarProps {
  children: React.ReactNode;
  containerMaxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  showFooter?: boolean;
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  userRole = 'student',
  userName = 'Rajasudhan R',
  userEmail = 'rajasudhan@college.edu',
  currentPath = '/',
  onLogout,
  onSwitchRole,
  onNavigate,
  containerMaxWidth = 'xl',
  showFooter = true,
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-bg text-text-primary antialiased relative selection:bg-primary/20 selection:text-primary">
      {/* Subtle Campus Dark Overlay Background */}
      <div 
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: `linear-gradient(180deg, rgba(7, 21, 31, 0.90) 0%, rgba(7, 21, 31, 0.96) 100%), url("/static/background.webp")`,
          backgroundPosition: 'center',
          backgroundSize: 'cover',
          backgroundAttachment: 'fixed',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* Sticky Frosted Header */}
      <div className="relative z-40">
        <Navbar
          userRole={userRole}
          userName={userName}
          userEmail={userEmail}
          currentPath={currentPath}
          onLogout={onLogout}
          onSwitchRole={onSwitchRole}
          onNavigate={onNavigate}
        />
      </div>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 flex flex-col">
        <PageContainer maxWidth={containerMaxWidth}>
          {children}
        </PageContainer>
      </main>
    </div>
  );
};
