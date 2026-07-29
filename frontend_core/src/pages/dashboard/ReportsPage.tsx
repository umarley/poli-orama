import { DownloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Card, DatePicker, Form, Input, Modal, Radio, Segmented, Space, Table } from 'antd';
import type { TableColumnsType } from 'antd';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { exportReport, getReport } from '@/modules/dashboard/dashboard-service';
import type { DashboardFilters, ReportRow, ReportType } from '@/modules/dashboard/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatNumber, formatPercent } from '@/utils/number-format';

const labels: Record<ReportType, string> = {
  metas: 'Metas por líder',
  demandas: 'Demandas',
  agenda: 'Agenda',
  cadastros: 'Evolução de cadastros',
  lideres: 'Ranking de líderes',
};

const friendlyColumns: Record<string, string> = {
  lideranca_id: 'ID',
  lider: 'Líder',
  liderados: 'Liderados',
  meta: 'Meta',
  atual: 'Atual',
  percentual: 'Percentual',
  risco: 'Risco',
  status: 'Status',
  categoria: 'Categoria',
  responsavel: 'Responsável',
  prazo: 'Prazo',
  total: 'Total',
  vencidas: 'Vencidas',
  evento_id: 'ID',
  titulo: 'Evento',
  data_inicio: 'Início',
  data_fim: 'Fim',
  territorio: 'Território',
  convites: 'Convites',
  pautas: 'Pautas',
  data: 'Data',
  origem: 'Origem',
  posicao: 'Posição',
};

interface ExportForm {
  finalidade: string;
  formato: 'csv' | 'xlsx';
}

export function ReportsPage() {
  const [type, setType] = useState<ReportType>('metas');
  const [exportOpen, setExportOpen] = useState(false);
  const [form] = Form.useForm<ExportForm>();
  const [filters, setFilters] = useState<DashboardFilters>({
    data_inicio: dayjs().subtract(29, 'day').format('YYYY-MM-DD'),
    data_fim: dayjs().format('YYYY-MM-DD'),
  });
  const canExport = useSessionStore((state) =>
    state.user?.permissions.includes('dashboard.exportar'),
  );
  const report = useQuery({
    queryKey: ['dashboard', 'report', type, filters],
    queryFn: () => getReport(type, filters),
  });
  const columns = useMemo<TableColumnsType<ReportRow>>(
    () =>
      Object.keys(report.data?.[0] ?? {}).map((key) => ({
        title: friendlyColumns[key] ?? key,
        dataIndex: key,
        key,
        render: (value: unknown) => {
          if (value === null || value === undefined || value === '') return '—';
          if (key.includes('percentual')) return formatPercent(value as number | string);
          if (key.startsWith('data') || key === 'prazo') {
            const parsed = dayjs(String(value));
            return parsed.isValid()
              ? parsed.format(
                  key === 'data_inicio' || key === 'data_fim' ? 'DD/MM/YYYY HH:mm' : 'DD/MM/YYYY',
                )
              : String(value);
          }
          if (typeof value === 'number') return formatNumber(value);
          return String(value);
        },
      })),
    [report.data],
  );
  const exportMutation = useMutation({
    mutationFn: (values: ExportForm) =>
      exportReport(type, values.formato, values.finalidade, filters),
    onSuccess: () => {
      AppToast.success('Exportação gerada e registrada na auditoria.');
      setExportOpen(false);
      form.resetFields();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  return (
    <div style={{ display: 'grid', gap: 20 }}>
      <PageHeader
        title="Relatórios"
        description="Consulte os relatórios operacionais com o mesmo escopo territorial do dashboard."
        breadcrumbs={[{ label: 'Início' }, { label: 'Relatórios' }]}
        actions={
          canExport ? (
            <Button icon={<DownloadOutlined />} onClick={() => setExportOpen(true)}>
              Exportar
            </Button>
          ) : undefined
        }
      />
      <Card size="small">
        <Space wrap>
          <Segmented
            value={type}
            options={(Object.keys(labels) as ReportType[]).map((value) => ({
              value,
              label: labels[value],
            }))}
            onChange={(value) => setType(value as ReportType)}
          />
          <DatePicker.RangePicker
            allowClear={false}
            value={[dayjs(filters.data_inicio), dayjs(filters.data_fim)]}
            onChange={(range) => {
              if (range?.[0] && range[1]) {
                setFilters((current) => ({
                  ...current,
                  data_inicio: range[0]!.format('YYYY-MM-DD'),
                  data_fim: range[1]!.format('YYYY-MM-DD'),
                }));
              }
            }}
          />
        </Space>
      </Card>
      <Card title={labels[type]}>
        <Table
          rowKey={(_, index) => String(index)}
          loading={report.isPending}
          columns={columns}
          dataSource={report.data ?? []}
          scroll={{ x: 'max-content' }}
          pagination={{ pageSize: 20, showSizeChanger: true }}
        />
      </Card>
      <Modal
        title={`Exportar ${labels[type]}`}
        open={exportOpen}
        okText="Gerar exportação"
        confirmLoading={exportMutation.isPending}
        onCancel={() => setExportOpen(false)}
        onOk={() => form.submit()}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ formato: 'xlsx' }}
          onFinish={(values) => exportMutation.mutate(values)}
        >
          <Form.Item
            name="finalidade"
            label="Finalidade"
            rules={[
              { required: true, message: 'Informe a finalidade da exportação.' },
              { min: 3, message: 'A finalidade deve ter ao menos 3 caracteres.' },
            ]}
          >
            <Input.TextArea
              rows={3}
              maxLength={255}
              showCount
              placeholder="Ex.: reunião semanal de coordenação"
            />
          </Form.Item>
          <Form.Item name="formato" label="Formato">
            <Radio.Group>
              <Radio value="xlsx">Excel (XLSX)</Radio>
              <Radio value="csv">CSV</Radio>
            </Radio.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
