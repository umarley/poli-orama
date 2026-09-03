import { BarChartOutlined, CommentOutlined, PhoneOutlined, RightOutlined } from '@ant-design/icons';
import { Card, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { useSessionStore } from '@/stores/session-store';

import styles from './ComunicacaoPage.module.css';

function openAttendanceWindow() {
  const url = '/comunicacao/atendimento?janela=1';
  const popup = window.open(url, 'comunicacao-atendimento', 'popup=yes,width=1440,height=900');
  if (popup == null) {
    window.location.assign(url);
  } else {
    popup.focus();
  }
}

export function ComunicacaoPage() {
  const navigate = useNavigate();
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canAttend = profiles.includes('telefonista');
  const canViewIndicators = profiles.includes('gestor');

  return (
    <div className={styles.page}>
      <PageHeader
        title="Comunicação"
        description="Atendimento ao eleitor, registro de contatos e indicadores da operação."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Comunicação' }]}
      />
      <div className={styles.grid}>
        <Card
          hoverable={canAttend}
          className={`${styles.card} ${canAttend ? '' : styles.cardDisabled}`}
          onClick={canAttend ? openAttendanceWindow : undefined}
        >
          <div className={styles.icon}>
            <PhoneOutlined />
          </div>
          <div className={styles.content}>
            <Typography.Title level={5}>Atendimento</Typography.Title>
            <Typography.Text type="secondary">
              {canAttend
                ? 'Abre a janela operacional para selecionar um eleitor e registrar o contato.'
                : 'Exclusivo do perfil telefonista. Você pode acessar o módulo, mas não iniciar o atendimento.'}
            </Typography.Text>
          </div>
          {canAttend ? (
            <RightOutlined className={styles.arrow} />
          ) : (
            <CommentOutlined className={styles.arrow} />
          )}
        </Card>
        {canViewIndicators ? (
          <Card hoverable className={styles.card} onClick={() => navigate('/comunicacao/indicadores')}>
            <div className={styles.icon}>
              <BarChartOutlined />
            </div>
            <div className={styles.content}>
              <Typography.Title level={5}>Indicadores e relatórios</Typography.Title>
              <Typography.Text type="secondary">
                Acompanhe volume, canais, intenção de voto, motivos de rejeição e conversão.
              </Typography.Text>
            </div>
            <RightOutlined className={styles.arrow} />
          </Card>
        ) : null}
      </div>
    </div>
  );
}
