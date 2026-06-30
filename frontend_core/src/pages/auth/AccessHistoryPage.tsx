import { DeleteOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Input, Modal, Space, Table, Tag, Typography } from 'antd';
import type { TableProps } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  confirmMfa,
  disableMfa,
  getCurrentUser,
  listSessions,
  revokeSession,
  setupMfa,
} from '@/modules/auth/auth-service';
import type { MfaSetup, UserSession } from '@/modules/auth/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import styles from '../tenants/TenantPages.module.css';

interface MfaFormValues {
  senha: string;
  codigo?: string;
}

export function AccessHistoryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useSessionStore((state) => state.user);
  const clearSession = useSessionStore((state) => state.clearSession);
  const updateUser = useSessionStore((state) => state.updateUser);
  const [mfaModalOpen, setMfaModalOpen] = useState(false);
  const [mfaSetup, setMfaSetup] = useState<MfaSetup | null>(null);
  const [submittingMfa, setSubmittingMfa] = useState(false);
  const [mfaForm] = Form.useForm<MfaFormValues>();
  const sessions = useQuery({ queryKey: ['auth-sessions'], queryFn: listSessions });
  const isManager = user?.profiles.some((profile) => ['gestor', 'gestor_saas'].includes(profile));

  const refreshIdentity = async () => {
    updateUser(await getCurrentUser());
  };

  const handleMfa = async () => {
    const values = await mfaForm.validateFields();
    setSubmittingMfa(true);
    try {
      if (user?.mfaEnabled) {
        await disableMfa(values.senha, values.codigo ?? '');
        AppToast.success('Autenticação em dois fatores desabilitada.');
        setMfaModalOpen(false);
        mfaForm.resetFields();
        await refreshIdentity();
        return;
      }
      if (!mfaSetup) {
        setMfaSetup(await setupMfa(values.senha));
        mfaForm.setFieldValue('codigo', undefined);
        return;
      }
      await confirmMfa(values.codigo ?? '');
      AppToast.success('Autenticação em dois fatores habilitada.');
      setMfaModalOpen(false);
      setMfaSetup(null);
      mfaForm.resetFields();
      await refreshIdentity();
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    } finally {
      setSubmittingMfa(false);
    }
  };

  const handleRevoke = async (session: UserSession) => {
    try {
      const revokedCurrent = await revokeSession(session.id);
      if (revokedCurrent) {
        clearSession();
        navigate('/login', { replace: true });
        return;
      }
      AppToast.success('Sessão revogada.');
      await queryClient.invalidateQueries({ queryKey: ['auth-sessions'] });
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };

  const columns: TableProps<UserSession>['columns'] = [
    {
      title: 'Dispositivo',
      key: 'device',
      render: (_, session) => (
        <Space direction="vertical" size={0}>
          <strong>{session.dispositivo || 'Dispositivo não identificado'}</strong>
          <Typography.Text type="secondary" ellipsis style={{ maxWidth: 360 }}>
            {session.user_agent || 'Navegador não identificado'}
          </Typography.Text>
        </Space>
      ),
    },
    { title: 'IP', dataIndex: 'ip_origem', render: (value) => value || '—' },
    {
      title: 'Última atividade',
      dataIndex: 'ultimo_uso_em',
      render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm'),
    },
    {
      title: 'Validade máxima',
      dataIndex: 'expira_em',
      render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm'),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, session) =>
        session.status !== 'ativa' ? (
          <Tag>{session.status.replace('_', ' ')}</Tag>
        ) : session.atual ? (
          <Tag color="success">Sessão atual</Tag>
        ) : (
          <Tag color="processing">Ativa</Tag>
        ),
    },
    {
      title: 'Ações',
      key: 'actions',
      render: (_, session) =>
        session.status === 'ativa' && (
          <Button danger icon={<DeleteOutlined />} onClick={() => void handleRevoke(session)}>
            {session.atual ? 'Encerrar' : 'Revogar'}
          </Button>
        ),
    },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title="Segurança e acessos"
        description="Gerencie a autenticação em dois fatores e os dispositivos conectados."
      />
      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            Autenticação em dois fatores
          </Space>
        }
        extra={
          isManager ? (
            <Button
              type={user?.mfaEnabled ? 'default' : 'primary'}
              onClick={() => setMfaModalOpen(true)}
            >
              {user?.mfaEnabled ? 'Desabilitar MFA' : 'Configurar MFA'}
            </Button>
          ) : undefined
        }
      >
        {isManager ? (
          <Tag color={user?.mfaEnabled ? 'success' : 'warning'}>
            {user?.mfaEnabled ? 'Habilitada' : 'Não configurada'}
          </Tag>
        ) : (
          <Typography.Text type="secondary">
            A configuração opcional de MFA está disponível para perfis gestores.
          </Typography.Text>
        )}
      </Card>

      <Card title="Histórico de acessos">
        <Table
          rowKey="id"
          columns={columns}
          dataSource={sessions.data ?? []}
          loading={sessions.isPending}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
        />
      </Card>

      <Modal
        open={mfaModalOpen}
        title={user?.mfaEnabled ? 'Desabilitar MFA' : 'Configurar MFA'}
        okText={user?.mfaEnabled ? 'Desabilitar' : mfaSetup ? 'Confirmar código' : 'Continuar'}
        confirmLoading={submittingMfa}
        onOk={() => void handleMfa()}
        onCancel={() => {
          setMfaModalOpen(false);
          setMfaSetup(null);
          mfaForm.resetFields();
        }}
      >
        <Form form={mfaForm} layout="vertical">
          {!mfaSetup && (
            <Form.Item name="senha" label="Senha atual" rules={[{ required: true }]}>
              <Input.Password autoComplete="current-password" />
            </Form.Item>
          )}
          {mfaSetup && (
            <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
              <Typography.Text>
                Cadastre a chave no aplicativo autenticador e informe o código gerado.
              </Typography.Text>
              <Typography.Text code copyable>
                {mfaSetup.segredo}
              </Typography.Text>
            </Space>
          )}
          {(mfaSetup || user?.mfaEnabled) && (
            <Form.Item
              name="codigo"
              label="Código do autenticador"
              rules={[
                { required: true },
                { pattern: /^\d{6}$/, message: 'Informe os seis números.' },
              ]}
            >
              <Input inputMode="numeric" maxLength={6} autoComplete="one-time-code" />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
}
