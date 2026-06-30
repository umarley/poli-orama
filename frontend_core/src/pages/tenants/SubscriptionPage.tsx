import { useQuery } from '@tanstack/react-query';
import { Alert, Card, Progress, Skeleton, Statistic, Typography } from 'antd';

import { PageHeader } from '@/components/layout/PageHeader';
import { getPlanUsage } from '@/modules/tenants/tenant-service';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './TenantPages.module.css';

function percentage(value: number, limit?: number) {
  return limit ? Math.min(100, Math.round((value / limit) * 100)) : 0;
}

export function SubscriptionPage() {
  const usage = useQuery({ queryKey: ['plan-usage'], queryFn: getPlanUsage });
  const plan = usage.data?.plano;
  const storage = Number(usage.data?.armazenamento_mb ?? 0);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Assinatura e limites"
        description="Consulte o plano contratado e o consumo atual da operação."
      />
      {usage.error && (
        <Alert type="error" showIcon message={normalizeApiError(usage.error).message} />
      )}
      {usage.isPending ? (
        <Card>
          <Skeleton active />
        </Card>
      ) : (
        <>
          <Card className={styles.card}>
            <Typography.Title level={4}>{plan?.nome ?? 'Sem plano associado'}</Typography.Title>
            <Typography.Text type="secondary">{plan?.descricao}</Typography.Text>
          </Card>
          <div className={styles.usage}>
            <Card>
              <div className={styles.limit}>
                <Statistic title="Usuários" value={usage.data?.usuarios ?? 0} />
                <Progress
                  percent={percentage(usage.data?.usuarios ?? 0, plan?.limite_usuarios)}
                  format={() => `${usage.data?.usuarios ?? 0} / ${plan?.limite_usuarios ?? '∞'}`}
                />
              </div>
            </Card>
            <Card>
              <div className={styles.limit}>
                <Statistic title="Pessoas" value={usage.data?.pessoas ?? 0} />
                <Progress
                  percent={percentage(usage.data?.pessoas ?? 0, plan?.limite_pessoas)}
                  format={() => `${usage.data?.pessoas ?? 0} / ${plan?.limite_pessoas ?? '∞'}`}
                />
              </div>
            </Card>
            <Card>
              <div className={styles.limit}>
                <Statistic title="Armazenamento (MB)" value={storage} precision={1} />
                <Progress
                  percent={percentage(storage, plan?.limite_armazenamento_mb)}
                  format={() => `${storage.toFixed(1)} / ${plan?.limite_armazenamento_mb ?? '∞'}`}
                />
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
