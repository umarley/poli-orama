import { render, screen } from '@testing-library/react';

import { GoalProgress } from '@/components/metas/GoalProgress';

describe('GoalProgress', () => {
  it('informa o risco por texto e nao apenas por cor', () => {
    render(<GoalProgress current={35} target={100} percentage={35} atRisk={true} />);

    expect(screen.getByText('35 de 100')).toBeInTheDocument();
    expect(screen.getByText('Meta abaixo do limiar esperado')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '35');
  });

  it('oculta o alerta detalhado no modo compacto', () => {
    render(
      <GoalProgress current={80} target={100} percentage={80} atRisk={false} compact={true} />,
    );

    expect(screen.queryByText('Meta abaixo do limiar esperado')).not.toBeInTheDocument();
  });
});
