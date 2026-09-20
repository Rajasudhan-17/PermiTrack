import React from 'react';
import { AppShell, AppShellProps } from '../components/layout/AppShell';

export type AppLayoutProps = AppShellProps;

export const AppLayout: React.FC<AppLayoutProps> = (props) => {
  return <AppShell {...props} />;
};

export default AppLayout;
