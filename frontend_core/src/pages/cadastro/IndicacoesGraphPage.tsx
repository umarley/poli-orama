import { ApartmentOutlined, FilterOutlined, SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  Input,
  Select,
  Space,
  Spin,
  Statistic,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { buscarPessoas, obterGrafoIndicacoes } from '@/modules/cadastro/pessoas-service';
import type {
  IndicacaoGraphEdge,
  IndicacaoGraphFilters,
  IndicacaoGraphNode,
} from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './IndicacoesGraphPage.module.css';

interface FilterForm {
  pessoa_id?: number;
  origem?: string;
  periodo?: [Dayjs, Dayjs];
  profundidade?: number;
}

interface Position {
  x: number;
  y: number;
}

function layoutGraph(nodes: IndicacaoGraphNode[], edges: IndicacaoGraphEdge[]) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const incoming = new Map(nodes.map((node) => [node.id, 0]));
  const outgoing = new Map<number, number[]>();
  edges.forEach((edge) => {
    if (!nodeIds.has(edge.origem_id) || !nodeIds.has(edge.destino_id)) return;
    incoming.set(edge.destino_id, (incoming.get(edge.destino_id) ?? 0) + 1);
    outgoing.set(edge.origem_id, [...(outgoing.get(edge.origem_id) ?? []), edge.destino_id]);
  });
  const roots = nodes.filter((node) => (incoming.get(node.id) ?? 0) === 0);
  const queue = (roots.length ? roots : nodes.slice(0, 1)).map((node) => node.id);
  const levels = new Map(queue.map((id) => [id, 0]));
  while (queue.length) {
    const current = queue.shift()!;
    const currentLevel = levels.get(current) ?? 0;
    for (const target of outgoing.get(current) ?? []) {
      if (!levels.has(target)) {
        levels.set(target, Math.min(currentLevel + 1, 6));
        queue.push(target);
      }
    }
  }
  nodes.forEach((node) => {
    if (!levels.has(node.id)) levels.set(node.id, 0);
  });
  const groups = new Map<number, IndicacaoGraphNode[]>();
  nodes.forEach((node) => {
    const level = levels.get(node.id) ?? 0;
    groups.set(level, [...(groups.get(level) ?? []), node]);
  });
  const positions = new Map<number, Position>();
  groups.forEach((items, level) => {
    items
      .sort((left, right) => left.nome.localeCompare(right.nome, 'pt-BR'))
      .forEach((node, index) => {
        positions.set(node.id, { x: 50 + level * 270, y: 44 + index * 108 });
      });
  });
  const maxLevel = Math.max(0, ...levels.values());
  const maxRows = Math.max(1, ...[...groups.values()].map((items) => items.length));
  return {
    positions,
    width: Math.max(920, 300 + maxLevel * 270),
    height: Math.max(480, 100 + maxRows * 108),
  };
}

export function IndicacoesGraphPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm<FilterForm>();
  const [filters, setFilters] = useState<IndicacaoGraphFilters>({ profundidade: 3 });
  const [personSearch, setPersonSearch] = useState('');
  const peopleQuery = useQuery({
    queryKey: ['cadastro', 'busca-grafo', personSearch],
    queryFn: () => buscarPessoas(personSearch),
    enabled: personSearch.trim().length >= 2,
  });
  const graphQuery = useQuery({
    queryKey: ['cadastro', 'grafo-indicacoes', filters],
    queryFn: () => obterGrafoIndicacoes(filters),
  });
  const graph = graphQuery.data;
  const layout = useMemo(() => layoutGraph(graph?.nodes ?? [], graph?.edges ?? []), [graph]);

  const applyFilters = (values: FilterForm) => {
    setFilters({
      pessoa_id: values.pessoa_id,
      origem: values.origem?.trim() || undefined,
      data_inicial: values.periodo?.[0].format('YYYY-MM-DD'),
      data_final: values.periodo?.[1].format('YYYY-MM-DD'),
      profundidade: values.profundidade ?? 3,
    });
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title="Rede de indicações"
        description="Visualize quem indicou quem e explore a propagação da rede de relacionamento."
        breadcrumbs={[{ label: 'Cadastro', to: '/cadastro' }, { label: 'Rede de indicações' }]}
      />
      <Card size="small">
        <Form form={form} layout="inline" onFinish={applyFilters} className={styles.filters}>
          <Form.Item name="pessoa_id" className={styles.personFilter}>
            <Select
              allowClear
              showSearch
              filterOption={false}
              suffixIcon={<SearchOutlined />}
              placeholder="Buscar pessoa para centralizar"
              onSearch={setPersonSearch}
              options={(peopleQuery.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome_completo,
              }))}
              notFoundContent={peopleQuery.isFetching ? <Spin size="small" /> : null}
            />
          </Form.Item>
          <Form.Item name="origem">
            <Input allowClear placeholder="Origem da indicação" />
          </Form.Item>
          <Form.Item name="periodo">
            <DatePicker.RangePicker format="DD/MM/YYYY" />
          </Form.Item>
          <Form.Item name="profundidade" initialValue={3}>
            <Select
              style={{ width: 130 }}
              options={[1, 2, 3, 4, 5, 6].map((value) => ({
                value,
                label: `${value} ${value === 1 ? 'nível' : 'níveis'}`,
              }))}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" icon={<FilterOutlined />}>
                Aplicar
              </Button>
              <Button
                onClick={() => {
                  form.resetFields();
                  setFilters({ profundidade: 3 });
                }}
              >
                Limpar
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
      <Space size={16} wrap>
        <Card size="small">
          <Statistic title="Pessoas na rede" value={graph?.nodes.length ?? 0} />
        </Card>
        <Card size="small">
          <Statistic
            title="Indicações"
            value={graph?.total_edges ?? 0}
            prefix={<ApartmentOutlined />}
          />
        </Card>
      </Space>
      {graphQuery.error ? (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar o grafo"
          description={normalizeApiError(graphQuery.error).message}
        />
      ) : null}
      {graph?.truncated ? (
        <Alert
          type="warning"
          showIcon
          message="A rede foi limitada a 300 relações. Use os filtros para reduzir o resultado."
        />
      ) : null}
      <Card className={styles.graphCard} title="Grafo de indicações" loading={graphQuery.isPending}>
        {!graphQuery.isPending && !graph?.nodes.length ? (
          <Empty description="Nenhuma indicação encontrada para os filtros selecionados." />
        ) : (
          <div className={styles.graphViewport}>
            <div className={styles.canvas} style={{ width: layout.width, height: layout.height }}>
              <svg
                className={styles.edges}
                width={layout.width}
                height={layout.height}
                aria-hidden="true"
              >
                <defs>
                  <marker
                    id="arrow"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#69b1ff" />
                  </marker>
                </defs>
                {(graph?.edges ?? []).map((edge) => {
                  const source = layout.positions.get(edge.origem_id);
                  const target = layout.positions.get(edge.destino_id);
                  if (!source || !target) return null;
                  return (
                    <line
                      key={edge.id}
                      className={styles.edge}
                      x1={source.x + 190}
                      y1={source.y + 37}
                      x2={target.x}
                      y2={target.y + 37}
                      markerEnd="url(#arrow)"
                    >
                      <title>{edge.origem || 'Indicação direta'}</title>
                    </line>
                  );
                })}
              </svg>
              {(graph?.nodes ?? []).map((node) => {
                const position = layout.positions.get(node.id);
                if (!position) return null;
                return (
                  <button
                    key={node.id}
                    type="button"
                    className={`${styles.node} ${node.ativo ? '' : styles.inactive}`}
                    style={{ left: position.x, top: position.y }}
                    onClick={() => navigate(`/cadastro/pessoas/${node.id}`)}
                    aria-label={`Abrir cadastro de ${node.nome}`}
                  >
                    <strong>{node.nome}</strong>
                    <span>Pessoa #{node.id}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div className={styles.legend}>
          <span>
            <i className={styles.legendMark} />
            sentido da indicação
          </span>
          <span>Selecione uma pessoa para abrir o cadastro</span>
        </div>
      </Card>
    </div>
  );
}
