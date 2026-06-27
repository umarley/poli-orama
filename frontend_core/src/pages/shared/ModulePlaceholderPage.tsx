import { BuildOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { Card, Col, Row, Steps, Typography } from 'antd';

import { PageHeader } from '@/components/layout/PageHeader';

import styles from './ModulePlaceholderPage.module.css';

interface ModulePlaceholderPageProps {
  title: string;
  description: string;
}

export function ModulePlaceholderPage({ title, description }: ModulePlaceholderPageProps) {
  return (
    <div className={styles.page}>
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: title }]}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card>
            <div className={styles.emptyState}>
              <span className={styles.icon}>
                <BuildOutlined />
              </span>
              <Typography.Title level={4}>Módulo preparado para evolução</Typography.Title>
              <Typography.Paragraph type="secondary">
                A rota, a navegação e o shell autenticado já estão configurados. As regras deste
                domínio serão adicionadas nas próximas especificações.
              </Typography.Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Fundação disponível">
            <Steps
              direction="vertical"
              size="small"
              items={[
                {
                  title: 'Rota do módulo',
                  status: 'finish',
                  icon: <CheckCircleOutlined />,
                },
                {
                  title: 'Controle de sessão',
                  status: 'finish',
                  icon: <CheckCircleOutlined />,
                },
                {
                  title: 'Cliente HTTP e cache',
                  status: 'finish',
                  icon: <CheckCircleOutlined />,
                },
                { title: 'Regras de negócio', status: 'wait' },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
