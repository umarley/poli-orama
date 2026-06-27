import { render, screen } from '@testing-library/react';
import { Form, Input } from 'antd';

import { BaseForm } from '@/components/form/BaseForm';

interface ExampleForm {
  name: string;
}

describe('BaseForm', () => {
  it('renderiza campos e o erro de submissao padronizado', () => {
    render(
      <BaseForm<ExampleForm> submitError="Falha de conexao">
        <Form.Item name="name" label="Nome">
          <Input />
        </Form.Item>
      </BaseForm>,
    );

    expect(screen.getByLabelText('Nome')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Falha de conexao');
  });
});
