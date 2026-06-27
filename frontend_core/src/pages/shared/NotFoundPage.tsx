import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <Result
      status="404"
      title="Página não encontrada"
      subTitle="A página solicitada não existe ou foi movida."
      extra={
        <Button type="primary" onClick={() => navigate('/dashboard')}>
          Voltar ao painel
        </Button>
      }
    />
  );
}
