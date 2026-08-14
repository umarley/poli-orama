import { ArrowLeftOutlined, FormOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Skeleton, Space, Switch, Typography } from 'antd';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  DEFAULT_REGISTRATION_FORM_PREFERENCES,
  getRegistrationFormPreferences,
  normalizeRegistrationFormPreferences,
} from '@/modules/tenants/registration-form-preferences';
import {
  getTenantConfiguration,
  updateTenantConfiguration,
} from '@/modules/tenants/tenant-service';
import type { RegistrationFormPreferences } from '@/modules/tenants/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './TenantPages.module.css';

interface FieldToggle {
  name: string[];
  label: string;
  locked?: boolean;
}

const FIELD_GROUPS: Array<{ title: string; description: string; fields: FieldToggle[] }> = [
  {
    title: 'Dados pessoais',
    description: 'O nome completo permanece sempre obrigatório neste formulário.',
    fields: [
      { name: ['nome_completo'], label: 'Nome completo', locked: true },
      { name: ['data_nascimento'], label: 'Data de nascimento' },
      { name: ['sexo'], label: 'Sexo' },
      { name: ['estado_civil'], label: 'Estado civil' },
    ],
  },
  {
    title: 'Documento',
    description: 'Exija o número de cada documento selecionado no cadastro manual.',
    fields: [
      { name: ['documento', 'CPF'], label: 'CPF' },
      { name: ['documento', 'RG'], label: 'RG' },
      { name: ['documento', 'CNH'], label: 'CNH' },
    ],
  },
  {
    title: 'Canal de contato',
    description: 'Exija o canal correspondente no cadastro manual de pessoas.',
    fields: [
      { name: ['canal', 'WhatsApp'], label: 'WhatsApp' },
      { name: ['canal', 'Celular'], label: 'Celular' },
      { name: ['canal', 'Telefone'], label: 'Telefone' },
      { name: ['canal', 'E-mail'], label: 'E-mail' },
    ],
  },
  {
    title: 'Dados eleitorais',
    description: 'Aplica-se somente ao título informado no cadastro interno.',
    fields: [{ name: ['titulo_eleitoral'], label: 'Título eleitoral' }],
  },
];

export function TenantCadastroSettingsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<RegistrationFormPreferences>();
  const configurationQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
  });
  const saveMutation = useMutation({
    mutationFn: (values: RegistrationFormPreferences) => {
      const currentPreferences = configurationQuery.data?.preferencias ?? {};
      return updateTenantConfiguration({
        preferencias: {
          ...currentPreferences,
          formulario_cadastro: normalizeRegistrationFormPreferences({
            ...values,
            nome_completo: true,
          }),
        },
      });
    },
    onSuccess: (configuration) => {
      queryClient.setQueryData(['tenant-configuration'], configuration);
      AppToast.success('Campos obrigatórios atualizados.');
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  useEffect(() => {
    if (!configurationQuery.data) return;
    form.setFieldsValue(getRegistrationFormPreferences(configurationQuery.data));
  }, [configurationQuery.data, form]);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Cadastros"
        description="Defina quais campos serão obrigatórios no cadastro manual de pessoas."
        breadcrumbs={[{ label: 'Configurações', to: '/configuracoes' }, { label: 'Cadastros' }]}
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
            <FormOutlined />
            Formulário de pessoas
          </Space>
        }
      >
        {configurationQuery.isPending ? (
          <Skeleton active />
        ) : (
          <Form<RegistrationFormPreferences>
            form={form}
            layout="vertical"
            initialValues={DEFAULT_REGISTRATION_FORM_PREFERENCES}
            onFinish={(values) => saveMutation.mutate(values)}
          >
            <Typography.Paragraph type="secondary">
              Essas regras valem apenas para o cadastro feito em Pessoas e eleitores. Aplicativo das
              lideranças, presença pública em eventos e integrações continuam exigindo somente o
              nome completo.
            </Typography.Paragraph>
            {FIELD_GROUPS.map((group) => (
              <section key={group.title} className={styles.fieldGroup}>
                <Typography.Title level={5}>{group.title}</Typography.Title>
                <Typography.Paragraph type="secondary">{group.description}</Typography.Paragraph>
                {group.fields.map((field) => (
                  <div key={field.name.join('.')} className={styles.switchRow}>
                    <Typography.Text>{field.label}</Typography.Text>
                    <Form.Item name={field.name} valuePropName="checked" style={{ margin: 0 }}>
                      <Switch
                        id={`campo-${field.name.join('-')}`}
                        aria-label={field.label}
                        checkedChildren="Obrigatório"
                        unCheckedChildren="Opcional"
                        disabled={field.locked}
                      />
                    </Form.Item>
                  </div>
                ))}
              </section>
            ))}
            <Button type="primary" htmlType="submit" loading={saveMutation.isPending}>
              Salvar campos obrigatórios
            </Button>
          </Form>
        )}
      </Card>
    </div>
  );
}
