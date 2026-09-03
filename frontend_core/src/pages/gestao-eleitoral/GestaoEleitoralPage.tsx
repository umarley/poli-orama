import { BarChartOutlined, GlobalOutlined, RightOutlined, TrophyOutlined } from '@ant-design/icons';
import { Card, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';

import styles from './GestaoEleitoralPage.module.css';

const cards = [
  {
    title: 'Análise de resultados',
    description: 'Indicadores, comparativos e distribuição de votos por município, zona, local e seção.',
    icon: <BarChartOutlined />,
    path: '/gestao-eleitoral/analise',
  },
  {
    title: 'Mapa de votação',
    description: 'Mapa de calor da votação do candidato selecionado, com cores distintas quando houver comparação.',
    icon: <GlobalOutlined />,
    path: '/gestao-eleitoral/analise?aba=mapa',
  },
  {
    title: 'Ranking por cargo',
    description: 'Compare os candidatos mais votados no recorte selecionado, com percentual e diferença de votos.',
    icon: <TrophyOutlined />,
    path: '/gestao-eleitoral/analise?aba=ranking',
  },
];

export function GestaoEleitoralPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <PageHeader
        title="Gestão eleitoral"
        description="Analise o desempenho em eleições anteriores por território e use os dados para orientar a estratégia da campanha."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Gestão eleitoral' }]}
      />
      <div className={styles.grid}>
        {cards.map((item) => (
          <Card
            key={item.path}
            hoverable
            className={styles.card}
            onClick={() => navigate(item.path)}
          >
            <div className={styles.icon}>{item.icon}</div>
            <div className={styles.content}>
              <Typography.Title level={5}>{item.title}</Typography.Title>
              <Typography.Text type="secondary">{item.description}</Typography.Text>
            </div>
            <RightOutlined className={styles.arrow} />
          </Card>
        ))}
      </div>
    </div>
  );
}
