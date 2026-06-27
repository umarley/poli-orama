import type { ArgsProps } from 'antd/es/message/interface';

type MessageApi = {
  open: (config: ArgsProps) => void;
};

let messageApi: MessageApi | null = null;

export const AppToast = {
  configure(api: MessageApi) {
    messageApi = api;
  },
  success(content: string) {
    messageApi?.open({ type: 'success', content });
  },
  error(content: string) {
    messageApi?.open({ type: 'error', content });
  },
  info(content: string) {
    messageApi?.open({ type: 'info', content });
  },
};
