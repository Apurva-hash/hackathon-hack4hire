/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        'surface-alt': 'var(--surface-alt)',
        border: 'var(--border)',
        text: 'var(--text)',
        'text-muted': 'var(--text-muted)',
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          tint: 'var(--primary-tint)',
        },
        accent: 'var(--accent)',
        status: {
          success: 'var(--status-success)',
          progress: 'var(--status-progress)',
          pending: 'var(--status-pending)',
          error: 'var(--status-error)',
          neutral: 'var(--status-neutral)',
        },
        sidebar: {
          bg: 'var(--admin-sidebar-bg)',
          text: 'var(--admin-sidebar-text)',
          muted: 'var(--admin-sidebar-muted)',
          hover: 'var(--admin-sidebar-hover)',
        },
        chart: {
          1: 'var(--chart-1)',
          2: 'var(--chart-2)',
          3: 'var(--chart-3)',
          4: 'var(--chart-4)',
          5: 'var(--chart-5)',
          6: 'var(--chart-6)',
        }
      },
      borderRadius: {
        card: '12px',
        input: '12px',
        modal: '16px',
        sheet: '16px',
      },
      boxShadow: {
        warmSm: 'var(--shadow-sm)',
        warmMd: 'var(--shadow-md)',
        warmLg: 'var(--shadow-lg)',
        warmXl: 'var(--shadow-xl)',
      },
      minHeight: {
        touch: '44px',
        touchLg: '48px',
      },
      minWidth: {
        touch: '44px',
        touchLg: '48px',
      }
    },
  },
  plugins: [],
}
