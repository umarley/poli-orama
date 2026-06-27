import { render, screen } from '@testing-library/react';

import { App } from '@/app/App';
import { AppProviders } from '@/app/AppProviders';

describe('App', () => {
  it('renderiza a tela inicial de autenticação', async () => {
    window.history.pushState({}, '', '/login');

    render(
      <AppProviders>
        <App />
      </AppProviders>,
    );

    expect(await screen.findByRole('heading', { name: 'Acesse sua campanha' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled();
  });
});
