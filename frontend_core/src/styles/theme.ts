import type { ThemeConfig } from 'antd';

export const palette = {
  primary: '#1677ff',
  primaryHover: '#4096ff',
  primaryActive: '#0958d9',
  navy: '#001d66',
  navySoft: '#102c7a',
  success: '#52c41a',
  warning: '#faad14',
  error: '#ff4d4f',
  text: '#141414',
  textSecondary: '#595959',
  textTertiary: '#8c8c8c',
  border: '#d9d9d9',
  split: '#eeeeF1',
  surface: '#ffffff',
  background: '#f5f5f5',
} as const;

export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: palette.primary,
    colorSuccess: palette.success,
    colorWarning: palette.warning,
    colorError: palette.error,
    colorInfo: palette.primary,
    colorText: palette.text,
    colorTextSecondary: palette.textSecondary,
    colorTextTertiary: palette.textTertiary,
    colorBorder: palette.border,
    colorSplit: palette.split,
    colorBgLayout: palette.background,
    colorBgContainer: palette.surface,
    borderRadius: 6,
    controlHeight: 32,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    fontSize: 14,
    lineWidth: 1,
  },
  components: {
    Layout: {
      headerBg: palette.navy,
      siderBg: palette.navy,
      bodyBg: palette.background,
      headerHeight: 44,
      headerPadding: '0 16px',
    },
    Menu: {
      darkItemBg: palette.navy,
      darkSubMenuItemBg: '#001452',
      darkItemSelectedBg: palette.navySoft,
      darkItemHoverBg: '#0b2875',
      itemBorderRadius: 0,
    },
    Card: {
      bodyPadding: 20,
      headerHeight: 48,
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: palette.text,
      rowHoverBg: '#fafafa',
    },
    Button: {
      fontWeight: 600,
    },
  },
};
