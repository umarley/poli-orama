import { ApartmentOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Radio, Skeleton, Space, Typography } from 'antd';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  getTenantConfiguration,
  updateTenantConfiguration,
} from '@/modules/tenants/tenant-service';
import {
  DEFAULT_COMMUNITY_TERMINOLOGY,
  getCommunityTerminology,
} from '@/modules/tenants/tenant-preferences';
import type { CommunityTerminology } from '@/modules/tenants/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './TenantPages.module.css';

interface TerminologyForm {
  nomenclatura_comunidades: CommunityTerminology;
}

export function TenantTerminologySettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<TerminologyForm>();
  const configurationQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
  });
  const saveMutation = useMutation({
    mutationFn: ({ nomenclatura_comunidades }: TerminologyForm) => {
      const currentPreferences = configurationQuery.data?.preferencias ?? {};
      return updateTenantConfiguration({
        preferencias: { ...currentPreferences, nomenclatura_comunidades },
      });
    },
    onSuccess: (configuration) => {
      queryClient.setQueryData(['tenant-configuration'], configuration);
      AppToast.success('Nomenclatura atualizada.');
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  useEffect(() => {
    if (!configurationQuery.data) return;
    form.setFieldValue(
      'nomenclatura_comunidades',
      getCommunityTerminology(configurationQuery.data),
    );
  }, [configurationQuery.data, form]);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Nomenclaturas do sistema"
        description="Adapte os termos exibidos na interface para a realidade operacional do tenant."
        breadcrumbs={[{ label: 'Configurações', to: '/configuracoes' }, { label: 'Nomenclaturas' }]}
        actions={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/configuracoes')}>
            Voltar
          </Button>
        }
      />

      {configurationQuery.isError ? (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar as configurações"
          description={normalizeApiError(configurationQuery.error).message}
          action={<Button onClick={() => configurationQuery.refetch()}>Tentar novamente</Button>}
        />
      ) : null}

      <Card
        className={styles.card}
        title={
          <Space>
            <ApartmentOutlined />
            Segmentação de pessoas
          </Space>
        }
      >
        {configurationQuery.isPending ? (
          <Skeleton active />
        ) : (
          <Form<TerminologyForm>
            form={form}
            layout="vertical"
            initialValues={{ nomenclatura_comunidades: DEFAULT_COMMUNITY_TERMINOLOGY }}
            onFinish={(values) => saveMutation.mutate(values)}
          >
            <Form.Item
              name="nomenclatura_comunidades"
              label="Como o sistema deve chamar Comunidades?"
              extra="Esta preferência altera somente os textos da interface. Dados, integrações e relatórios continuam usando internamente o conceito de comunidade."
              rules={[{ required: true, message: 'Escolha uma nomenclatura.' }]}
            >
              <Radio.Group optionType="button" buttonStyle="solid">
                <Radio.Button value="comunidades">Comunidades</Radio.Button>
                <Radio.Button value="frentes">Frentes</Radio.Button>
              </Radio.Group>
            </Form.Item>
            <Typography.Paragraph type="secondary">
              O padrão é “Comunidades”. Ao selecionar “Frentes”, a aba, os botões e os diálogos de
              segmentação passam a usar esse termo para os usuários deste tenant.
            </Typography.Paragraph>
            <Button type="primary" htmlType="submit" loading={saveMutation.isPending}>
              Salvar nomenclatura
            </Button>
          </Form>
        )}
      </Card>
    </div>
  );
}
