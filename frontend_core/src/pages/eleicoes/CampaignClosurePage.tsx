import { CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Result,
  Space,
  Spin,
  Tag,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  getActiveCampaignClosure,
  requestActiveCampaignClosure,
  retryActiveCampaignClosure,
} from '@/modules/eleicoes/eleicoes-service';
import type { CampaignClosureInput } from '@/modules/eleicoes/types';
import { normalizeApiError } from '@/services/api/api-error';

interface ClosureForm extends Omit<CampaignClosureInput, 'resultado_oficial_em'> {
  resultado_oficial_em?: Dayjs;
}

const statusLabels = {
  enfileirado: { label: 'Na fila', color: 'processing' },
  processando: { label: 'Consolidando', color: 'processing' },
  concluido: { label: 'Concluído', color: 'success' },
  falha: { label: 'Falha', color: 'error' },
} as const;

function formatVoteCount(value: string | number | undefined): string {
  const digits = String(value ?? '').replace(/\D/g, '');
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function parseVoteCount(value: string | undefined): number {
  const digits = value?.replace(/\D/g, '') ?? '';
  return digits ? Number(digits) : Number.NaN;
}

export function CampaignClosurePage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<ClosureForm>();
  const closure = useQuery({
    queryKey: ['campaign-closure'],
    queryFn: getActiveCampaignClosure,
    refetchInterval: (query) =>
      ['enfileirado', 'processando'].includes(query.state.data?.status ?? '') ? 5000 : false,
  });

  const requestClosure = useMutation({
    mutationFn: (values: ClosureForm) =>
      requestActiveCampaignClosure({
        ...values,
        resultado_oficial_em: values.resultado_oficial_em?.toISOString(),
      }),
    onSuccess: async () => {
      AppToast.success('Encerramento enviado para processamento.');
      await queryClient.invalidateQueries({ queryKey: ['campaign-closure'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const retryClosure = useMutation({
    mutationFn: retryActiveCampaignClosure,
    onSuccess: async () => {
      AppToast.success('Reprocessamento enviado para a fila.');
      await queryClient.invalidateQueries({ queryKey: ['campaign-closure'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const confirm = async () => {
    const values = await form.validateFields();
    Modal.confirm({
      title: 'Encerrar definitivamente esta campanha?',
      icon: <ExclamationCircleOutlined />,
      content:
        'Os dados serão consolidados no DW e, após o processamento, a campanha deixará de ser a campanha ativa.',
      okText: 'Encerrar e consolidar',
      okButtonProps: { danger: true },
      cancelText: 'Cancelar',
      onOk: () => requestClosure.mutateAsync(values),
    });
  };

  const item = closure.data;
  const status = item ? statusLabels[item.status] : null;

  return (
    <div>
      <PageHeader
        title="Encerramento da campanha"
        description="Registre o resultado oficial e consolide o histórico para consultas analíticas."
      />

      {closure.isPending ? (
        <Card>
          <Spin />
        </Card>
      ) : item ? (
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Alert
              type={
                item.status === 'concluido' ? 'success' : item.status === 'falha' ? 'error' : 'info'
              }
              showIcon
              message={
                <Space>
                  Processamento
                  {status && <Tag color={status.color}>{status.label}</Tag>}
                </Space>
              }
              description={
                item.status === 'falha'
                  ? item.erro || 'O processamento falhou.'
                  : item.status === 'concluido'
                    ? 'A campanha foi encerrada e o snapshot analítico está disponível no DW.'
                    : 'O processamento acontece em background. Esta página pode ser fechada.'
              }
            />
            <Descriptions bordered column={{ xs: 1, md: 2 }}>
              <Descriptions.Item label="Campanha">{item.campanha_nome}</Descriptions.Item>
              <Descriptions.Item label="Cargo">{item.cargo_pleiteado}</Descriptions.Item>
              <Descriptions.Item label="Votos obtidos">
                {item.votos_obtidos.toLocaleString('pt-BR')}
              </Descriptions.Item>
              <Descriptions.Item label="Resultado">
                {item.eleito ? 'Eleito' : 'Não eleito'}
              </Descriptions.Item>
              <Descriptions.Item label="Colocação">
                {item.colocacao ? `${item.colocacao}º` : 'Não informada'}
              </Descriptions.Item>
              <Descriptions.Item label="Solicitado em">
                {dayjs(item.solicitado_em).format('DD/MM/YYYY HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>
            {item.status === 'falha' && (
              <Button
                type="primary"
                loading={retryClosure.isPending}
                onClick={() => retryClosure.mutate()}
              >
                Reprocessar consolidação
              </Button>
            )}
            {item.status === 'concluido' && (
              <Result
                icon={<CheckCircleOutlined />}
                status="success"
                title="Campanha consolidada"
                subTitle="Os dados históricos estão preservados para painéis e consultas futuras."
              />
            )}
          </Space>
        </Card>
      ) : (
        <Card>
          <Alert
            type="warning"
            showIcon
            message="Esta ação encerra a campanha ativa"
            description="Confira os dados com o resultado oficial antes de continuar."
            style={{ marginBottom: 20 }}
          />
          <Form form={form} layout="vertical">
            <Form.Item
              name="votos_obtidos"
              label="Votos obtidos pelo candidato"
              rules={[{ required: true }]}
            >
              <InputNumber
                min={0}
                precision={0}
                formatter={formatVoteCount}
                parser={parseVoteCount}
                style={{ width: '100%' }}
              />
            </Form.Item>
            <Form.Item name="total_votos_validos" label="Total de votos válidos">
              <InputNumber
                min={0}
                precision={0}
                formatter={formatVoteCount}
                parser={parseVoteCount}
                style={{ width: '100%' }}
              />
            </Form.Item>
            <Form.Item name="eleito" label="Resultado" rules={[{ required: true }]}>
              <Radio.Group
                options={[
                  { value: true, label: 'Eleito' },
                  { value: false, label: 'Não eleito' },
                ]}
              />
            </Form.Item>
            <Form.Item name="colocacao" label="Colocação">
              <InputNumber min={1} precision={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="resultado_oficial_em" label="Publicação do resultado oficial">
              <DatePicker showTime format="DD/MM/YYYY HH:mm:ss" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="fonte_resultado" label="Fonte oficial">
              <Input placeholder="URL ou identificação da publicação do TSE" maxLength={255} />
            </Form.Item>
            <Form.Item name="observacao" label="Observações">
              <Input.TextArea rows={4} maxLength={4000} />
            </Form.Item>
            <Button
              danger
              type="primary"
              loading={requestClosure.isPending}
              onClick={() => void confirm()}
            >
              Encerrar campanha
            </Button>
          </Form>
        </Card>
      )}
    </div>
  );
}
