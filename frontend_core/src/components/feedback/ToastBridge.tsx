import { App } from 'antd';
import { useEffect } from 'react';

import { AppToast } from '@/components/feedback/AppToast';

export function ToastBridge() {
  const { message } = App.useApp();

  useEffect(() => {
    AppToast.configure(message);
  }, [message]);

  return null;
}
