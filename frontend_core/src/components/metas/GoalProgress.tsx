import { Alert, Progress, Space, Typography } from 'antd';

interface GoalProgressProps {
  current: number;
  target: number;
  percentage: number;
  atRisk: boolean;
  compact?: boolean;
}

export function GoalProgress({
  current,
  target,
  percentage,
  atRisk,
  compact = false,
}: GoalProgressProps) {
  const shown = Math.min(100, Math.max(0, percentage));
  return (
    <Space direction="vertical" size={compact ? 2 : 8} style={{ width: '100%' }}>
      <Progress
        percent={shown}
        status={atRisk ? 'exception' : percentage >= 100 ? 'success' : 'active'}
        strokeColor={atRisk ? '#cf1322' : undefined}
      />
      <Typography.Text type="secondary">
        {current.toLocaleString('pt-BR')} de {target.toLocaleString('pt-BR')}
      </Typography.Text>
      {atRisk && !compact && (
        <Alert
          type="warning"
          showIcon
          message="Meta abaixo do limiar esperado"
          description="O risco é indicado por texto e ícone, não apenas pela cor."
        />
      )}
    </Space>
  );
}
