import { App as AntApp } from 'antd';
import { RouterProvider } from 'react-router-dom';

import { router } from '@/app/router';

export function App() {
  return (
    <AntApp>
      <RouterProvider router={router} />
    </AntApp>
  );
}
