export const tokens = {
  colors: {
    bg: {
      DEFAULT: '#07151F',
      secondary: '#0B1C27',
    },
    surface: {
      DEFAULT: '#0F2432',
      elevated: '#132B3A',
    },
    primary: {
      DEFAULT: '#22B8CF',
      hover: '#35C7DD',
      subtle: 'rgba(34, 184, 207, 0.12)',
    },
    success: {
      DEFAULT: '#32D583',
      subtle: 'rgba(50, 213, 131, 0.12)',
    },
    warning: {
      DEFAULT: '#F5B942',
      subtle: 'rgba(245, 185, 66, 0.12)',
    },
    danger: {
      DEFAULT: '#F04438',
      subtle: 'rgba(240, 68, 56, 0.12)',
    },
    info: {
      DEFAULT: '#4EA5FF',
      subtle: 'rgba(78, 165, 255, 0.12)',
    },
    text: {
      primary: '#F4F8FB',
      secondary: '#A7BAC7',
      muted: '#718796',
    },
    border: {
      DEFAULT: 'rgba(255, 255, 255, 0.08)',
      subtle: 'rgba(255, 255, 255, 0.04)',
      hover: 'rgba(34, 184, 207, 0.35)',
    },
  },
  typography: {
    fontFamily: {
      base: "'Inter', system-ui, -apple-system, sans-serif",
      display: "'Space Grotesk', 'Inter', system-ui, sans-serif",
    },
    fontSize: {
      pageTitle: { desktop: '32px', tablet: '28px', mobile: '24px', weight: '700' },
      sectionTitle: { size: '18-20px', weight: '600' },
      statNumber: { size: '28-40px', weight: '700' },
      body: '14-16px',
      label: '12-14px',
      muted: '12-13px',
    },
  },
  spacing: {
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    5: '20px',
    6: '24px',
    7: '32px',
    8: '40px',
    9: '48px',
    10: '64px',
  },
  radius: {
    sm: '8px',     // small controls
    md: '10px',    // inputs
    lg: '16px',    // cards
    xl: '20px',    // large containers
    pill: '9999px',// badges, status, tags
  },
  shadows: {
    sm: '0 4px 12px rgba(0, 0, 0, 0.15)',
    md: '0 8px 24px rgba(0, 0, 0, 0.25)',
    lg: '0 16px 40px rgba(0, 0, 0, 0.35)',
  }
} as const;
