import { CheckOutlined, CloseOutlined, DownloadOutlined, SaveOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, Col, Descriptions, Row, Select, Space, Statistic, Table, Tabs, Tag } from 'antd';
import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  approveImport,
  cancelImport,
  downloadErrorReport,
  getImport,
  getImportDuplicates,
  getImportErrors,
  getImportSummary,
  updateMapping,
} from '@/modules/etl/etl-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

const targetFields = [
  'nome_completo', 'cpf', 'rg', 'titulo_eleitor', 'data_nascimento',
  'telefone', 'email', 'endereco', 'logradouro', 'numero', 'complemento',
  'bairro', 'municipio', 'uf', 'cep',
].map((value) => ({ value, label: value }));

export function ImportDetailPage() {
  const { id } = useParams();
  const importId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const item = useQuery({
    queryKey: ['etl', 'importacao', importId],
    queryFn: () => getImport(importId),
    enabled: importId > 0,
    refetchInterval: (query) =>
      ['pendente', 'processando'].includes(query.state.data?.status ?? '') ? 2500 : false,
  });
  const isProcessing = ['pendente', 'processando'].includes(item.data?.status ?? '');
  const pollingInterval = isProcessing ? 2500 : false;
  const summary = useQuery({ queryKey: ['etl', importId, 'resumo'], queryFn: () => getImportSummary(importId), enabled: importId > 0, refetchInterval: pollingInterval });
  const errors = useQuery({ queryKey: ['etl', importId, 'erros'], queryFn: () => getImportErrors(importId), enabled: importId > 0, refetchInterval: pollingInterval });
  const duplicates = useQuery({ queryKey: ['etl', importId, 'duplicidades'], queryFn: () => getImportDuplicates(importId), enabled: importId > 0, refetchInterval: pollingInterval });
  const columns = useMemo(
    () => (item.data?.parametros.colunas_detectadas as string[] | undefined) ?? [],
    [item.data],
  );
  const refresh = async () => queryClient.invalidateQueries({ queryKey: ['etl'] });
  const mappingMutation = useMutation({
    mutationFn: () => updateMapping(importId, { ...item.data?.mapeamento_colunas, ...mapping }),
    onSuccess: async () => { AppToast.success('Mapeamento salvo e reprocessamento iniciado.'); await refresh(); },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const approval = useMutation({
    mutationFn: () => approveImport(importId),
    onSuccess: async () => { AppToast.success('Carga aprovada e enfileirada.'); await refresh(); },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const cancellation = useMutation({
    mutationFn: () => cancelImport(importId),
    onSuccess: async () => { AppToast.success('Importação cancelada.'); await refresh(); navigate('/importacoes'); },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const report = useMutation({
    mutationFn: () => downloadErrorReport(importId),
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  if (item.error) return <Alert type="error" showIcon message={normalizeApiError(item.error).message} />;
  const current = item.data;
  const totals = summary.data;
  return (
    <div>
      <PageHeader
        title={current?.arquivo?.nome_arquivo || `Importação #${importId}`}
        description="Mapeamento, validação, duplicidades e carga controlada."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Importações', to: '/importacoes' }, { label: `#${importId}` }]}
        actions={<Space>
          {permissions.includes('etl.exportar') && <Button icon={<DownloadOutlined />} loading={report.isPending} onClick={() => report.mutate()}>Relatório CSV</Button>}
          {permissions.includes('etl.aprovar') && current?.status === 'parcial' && <Button type="primary" icon={<CheckOutlined />} loading={approval.isPending} onClick={() => approval.mutate()}>Aprovar carga</Button>}
          {permissions.includes('etl.editar') && ['pendente', 'parcial', 'falha'].includes(current?.status ?? '') && <Button danger icon={<CloseOutlined />} onClick={() => cancellation.mutate()}>Cancelar</Button>}
        </Space>}
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={4}><Card><Statistic title="Total" value={totals?.total ?? 0} /></Card></Col>
        <Col xs={12} lg={4}><Card><Statistic title="Válidas" value={totals?.validas ?? 0} /></Card></Col>
        <Col xs={12} lg={4}><Card><Statistic title="Inválidas" value={totals?.invalidas ?? 0} /></Card></Col>
        <Col xs={12} lg={4}><Card><Statistic title="Duplicadas" value={totals?.duplicadas ?? 0} /></Card></Col>
        <Col xs={12} lg={4}><Card><Statistic title="Pendentes" value={totals?.pendentes ?? 0} /></Card></Col>
        <Col xs={12} lg={4}><Card><Statistic title="Carregadas" value={totals?.carregadas ?? 0} /></Card></Col>
      </Row>
      <Card style={{ marginBottom: 16 }}>
        <Descriptions>
          <Descriptions.Item label="Fonte">{current?.fonte_nome}</Descriptions.Item>
          <Descriptions.Item label="Status"><Tag>{current?.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="Descrição">{current?.descricao || '—'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Tabs items={[
        {
          key: 'mapping', label: 'Mapeamento', children: <Card
            extra={permissions.includes('etl.editar') && <Button icon={<SaveOutlined />} loading={mappingMutation.isPending} onClick={() => mappingMutation.mutate()}>Salvar e validar</Button>}
          >
            <Table rowKey={(value) => value} pagination={false} dataSource={columns} columns={[
              { title: 'Coluna do arquivo', render: (_, value) => value },
              { title: 'Campo do cadastro', render: (_, value) => <Select allowClear style={{ width: 260 }} defaultValue={current?.mapeamento_colunas[value]} options={targetFields} onChange={(selected) => setMapping((old) => ({ ...old, [value]: selected }))} /> },
            ]} />
          </Card>,
        },
        {
          key: 'errors', label: `Erros e avisos (${errors.data?.length ?? 0})`, children: <Table rowKey="id" dataSource={errors.data ?? []} columns={[
            { title: 'Linha', dataIndex: 'numero_linha' }, { title: 'Severidade', dataIndex: 'severidade' },
            { title: 'Campo', dataIndex: 'campo' }, { title: 'Valor', dataIndex: 'valor' }, { title: 'Motivo', dataIndex: 'mensagem' },
          ]} />,
        },
        {
          key: 'duplicates', label: `Duplicidades (${duplicates.data?.length ?? 0})`, children: <Table rowKey="id" dataSource={duplicates.data ?? []} columns={[
            { title: 'Staging', dataIndex: 'staging_pessoa_id' }, { title: 'Pessoa candidata', dataIndex: 'pessoa_candidata_id' },
            { title: 'Regra', dataIndex: 'criterio' }, { title: 'Score', dataIndex: 'score' }, { title: 'Decisão', dataIndex: 'decisao' },
          ]} />,
        },
      ]} />
    </div>
  );
}
