import { CheckOutlined, EditOutlined, PlusOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Input, Modal, Select, Space, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  activateCampaign,
  createCampaign,
  listCampaigns,
  listContestedOffices,
  listOfficialElections,
  updateCampaign,
} from '@/modules/eleicoes/eleicoes-service';
import type { Campaign, CampaignInput } from '@/modules/eleicoes/types';
import { normalizeApiError } from '@/services/api/api-error';

type CampaignForm = CampaignInput;

export function CampaignManagementPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<CampaignForm>();
  const [editing, setEditing] = useState<Campaign | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const selectedElectionId = Form.useWatch('eleicao_id', form);
  const campaigns = useQuery({ queryKey: ['campaigns'], queryFn: listCampaigns });
  const elections = useQuery({
    queryKey: ['official-elections', false],
    queryFn: () => listOfficialElections(false),
  });
  const selectedElection = elections.data?.find(
    (election) => election.id === selectedElectionId,
  );
  const selectedElectionType =
    selectedElection?.tipo === 'municipal' ? 'municipal' : 'federal';
  const contestedOffices = useQuery({
    queryKey: ['official-elections', 'contested-offices', selectedElectionType],
    queryFn: () => listContestedOffices(selectedElectionType),
    enabled: modalOpen && Boolean(selectedElection),
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['campaigns'] }),
      queryClient.invalidateQueries({ queryKey: ['current-campaign'] }),
    ]);
  };
  const save = useMutation({
    mutationFn: (values: CampaignForm) =>
      editing
        ? updateCampaign(editing.id, {
            nome: values.nome,
            cargo_pleiteado_id: values.cargo_pleiteado_id,
          })
        : createCampaign(values),
    onSuccess: async () => {
      AppToast.success(editing ? 'Campanha atualizada.' : 'Campanha criada.');
      setModalOpen(false);
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const activate = useMutation({
    mutationFn: activateCampaign,
    onSuccess: async () => {
      AppToast.success('Campanha definida como atual.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ ativa: false });
    setModalOpen(true);
  };
  const openEdit = (campaign: Campaign) => {
    setEditing(campaign);
    form.setFieldsValue({
      eleicao_id: campaign.eleicao_id,
      nome: campaign.nome,
      cargo_pleiteado_id: campaign.cargo_pleiteado_id ?? undefined,
      ativa: campaign.ativa,
    });
    setModalOpen(true);
  };
  const confirmActivation = (campaign: Campaign) =>
    Modal.confirm({
      title: `Tornar “${campaign.nome}” a campanha atual?`,
      content: 'A campanha atualmente ativa será desativada automaticamente.',
      okText: 'Ativar campanha',
      cancelText: 'Cancelar',
      onOk: () => activate.mutateAsync(campaign.id),
    });

  return (
    <div>
      <PageHeader
        title="Gestão de campanhas"
        description="Crie campanhas, defina a campanha atual e acompanhe o seu ciclo de vida."
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nova campanha
          </Button>
        }
      />
      <Card>
        <BaseTable<Campaign>
          rowKey="id"
          loading={campaigns.isPending}
          dataSource={campaigns.data ?? []}
          error={campaigns.error ? normalizeApiError(campaigns.error).message : null}
          onRetry={() => void campaigns.refetch()}
          columns={[
            {
              title: 'Campanha',
              dataIndex: 'nome',
              render: (value, record) => (
                <Space direction="vertical" size={0}>
                  <Typography.Text strong>{value}</Typography.Text>
                  <Typography.Text type="secondary">{record.cargo_pleiteado}</Typography.Text>
                </Space>
              ),
            },
            {
              title: 'Eleição',
              render: (_, record) =>
                `${record.eleicao_descricao || record.eleicao_tipo} · ${record.eleicao_ano} · ${record.eleicao_turno}º turno`,
            },
            {
              title: 'Status',
              render: (_, record) =>
                record.data_encerramento ? (
                  <Tag>Encerrada</Tag>
                ) : record.ativa ? (
                  <Tag color="success">Atual</Tag>
                ) : (
                  <Tag color="default">Inativa</Tag>
                ),
            },
            {
              title: 'Criada em',
              dataIndex: 'criado_em',
              render: (value) => dayjs(value).format('DD/MM/YYYY HH:mm:ss'),
            },
            {
              title: 'Ações',
              fixed: 'right',
              render: (_, record) => (
                <Space wrap>
                  {!record.data_encerramento && (
                    <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
                      Editar
                    </Button>
                  )}
                  {!record.ativa && !record.data_encerramento && (
                    <Button
                      size="small"
                      icon={<CheckOutlined />}
                      loading={activate.isPending}
                      onClick={() => confirmActivation(record)}
                    >
                      Tornar atual
                    </Button>
                  )}
                  {record.ativa && (
                    <Button
                      size="small"
                      danger
                      icon={<StopOutlined />}
                      onClick={() => navigate('/configuracoes/campanhas/encerramento')}
                    >
                      Encerrar
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <BaseModal
        isOpen={modalOpen}
        title={editing ? 'Editar campanha' : 'Nova campanha'}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={save.isPending}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={(values) => save.mutate(values)}>
          <Form.Item
            name="eleicao_id"
            label="Eleição oficial"
            rules={[{ required: true, message: 'Selecione a eleição.' }]}
          >
            <Select
              disabled={Boolean(editing)}
              placeholder="Selecione"
              onChange={() => form.setFieldValue('cargo_pleiteado_id', undefined)}
              options={(elections.data ?? []).map((election) => ({
                value: election.id,
                label: `${election.descricao || election.tipo} · ${election.ano} · ${election.turno}º turno`,
              }))}
            />
          </Form.Item>
          <Form.Item name="nome" label="Nome da campanha" rules={[{ required: true }]}>
            <Input maxLength={180} />
          </Form.Item>
          <Form.Item
            name="cargo_pleiteado_id"
            label="Cargo pleiteado"
            rules={[{ required: true, message: 'Selecione o cargo pleiteado.' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              disabled={!selectedElection}
              loading={contestedOffices.isPending}
              placeholder={
                selectedElection ? 'Selecione o cargo' : 'Selecione primeiro a eleição'
              }
              options={(contestedOffices.data ?? []).map((office) => ({
                value: office.id,
                label: office.nome,
              }))}
            />
          </Form.Item>
          {!editing && (
            <Form.Item name="ativa" label="Definir como campanha atual">
              <Select
                options={[
                  { value: true, label: 'Sim' },
                  { value: false, label: 'Não' },
                ]}
              />
            </Form.Item>
          )}
        </Form>
      </BaseModal>
    </div>
  );
}
