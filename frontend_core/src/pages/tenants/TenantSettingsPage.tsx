import {
  ApartmentOutlined,
  BankOutlined,
  CreditCardOutlined,
  FlagOutlined,
  FormOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  TeamOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  ColorPicker,
  Form,
  Image,
  Input,
  InputNumber,
  Select,
  Space,
  Skeleton,
  Typography,
  Upload,
} from 'antd';
import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  getCurrentTenant,
  getTenantConfiguration,
  getTenantLogoBlob,
  updateTenantConfiguration,
  uploadTenantLogo,
} from '@/modules/tenants/tenant-service';
import type { TenantConfiguration } from '@/modules/tenants/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import styles from './TenantPages.module.css';

type TenantSettingsForm = Pick<
  TenantConfiguration,
  'nome_publico' | 'cor_primaria' | 'fuso_horario' | 'percentual_alerta_meta'
>;

interface SettingsCard {
  title: string;
  description: string;
  icon: React.JSX.Element;
  path: string;
}

const TIME_ZONE_OPTIONS = Intl.supportedValuesOf('timeZone').map((timeZone) => ({
  value: timeZone,
  label: timeZone.replaceAll('_', ' '),
}));

export function TenantSettingsPage() {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [form] = Form.useForm<Partial<TenantSettingsForm>>();
  const setTenant = useSessionStore((state) => state.setTenant);
  const user = useSessionStore((state) => state.user);
  const canViewGeneralSettings = user?.permissions.includes('configuracoes.visualizar') ?? false;
  const tenantQuery = useQuery({ queryKey: ['current-tenant'], queryFn: getCurrentTenant });
  const configQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
    enabled: canViewGeneralSettings,
  });
  const storedLogoUrl = configQuery.data?.logo_url;
  const storedLogoQuery = useQuery({
    queryKey: ['tenant-configuration', 'logo', storedLogoUrl],
    queryFn: () => getTenantLogoBlob(storedLogoUrl!),
    enabled: Boolean(storedLogoUrl?.startsWith('/api/')),
  });
  const logoPreviewUrl = useMemo(() => {
    if (storedLogoQuery.data) return URL.createObjectURL(storedLogoQuery.data);
    if (storedLogoUrl && !storedLogoUrl.startsWith('/api/')) return storedLogoUrl;
    return null;
  }, [storedLogoQuery.data, storedLogoUrl]);
  const save = useMutation({
    mutationFn: updateTenantConfiguration,
    onSuccess: async (configuration) => {
      AppToast.success('Configurações atualizadas.');
      if (tenantQuery.data) {
        setTenant({
          id: tenantQuery.data.id,
          name: configuration.nome_publico || tenantQuery.data.nome,
          slug: tenantQuery.data.slug,
          status: tenantQuery.data.status,
        });
      }
      await client.invalidateQueries({ queryKey: ['tenant-configuration'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const uploadLogo = useMutation({
    mutationFn: uploadTenantLogo,
    onSuccess: (configuration) => {
      client.setQueryData(['tenant-configuration'], configuration);
      AppToast.success('Logotipo atualizado.');
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  useEffect(() => {
    if (configQuery.data) {
      const { nome_publico, cor_primaria, fuso_horario, percentual_alerta_meta } = configQuery.data;
      form.setFieldsValue({
        nome_publico,
        cor_primaria,
        fuso_horario,
        percentual_alerta_meta,
      });
    }
  }, [configQuery.data, form]);

  useEffect(
    () => () => {
      if (logoPreviewUrl?.startsWith('blob:')) URL.revokeObjectURL(logoPreviewUrl);
    },
    [logoPreviewUrl],
  );

  const campaignManager = ['gestor', 'gestor_saas', 'coordenador_territorial'].some((profile) =>
    user?.profiles.includes(profile),
  );
  const tenantManager = ['gestor', 'gestor_saas'].some((profile) =>
    user?.profiles.includes(profile),
  );
  const availableCards: Array<SettingsCard | null> = [
    tenantManager
      ? {
          title: 'Nomenclaturas',
          description: 'Escolha os termos exibidos na interface para este tenant.',
          icon: <ApartmentOutlined />,
          path: '/configuracoes/nomenclaturas',
        }
      : null,
    tenantManager
      ? {
          title: 'Cadastros',
          description: 'Campos obrigatórios no cadastro manual de pessoas.',
          icon: <FormOutlined />,
          path: '/configuracoes/cadastros',
        }
      : null,
    campaignManager
      ? {
          title: 'Campanhas eleitorais',
          description: 'Criação, edição, ativação e encerramento de campanhas.',
          icon: <FlagOutlined />,
          path: '/configuracoes/campanhas',
        }
      : null,
    user?.profiles.includes('gestor_saas')
      ? {
          title: 'Eleições oficiais',
          description: 'Calendário eleitoral global utilizado por todos os tenants.',
          icon: <BankOutlined />,
          path: '/admin/eleicoes',
        }
      : null,
    user?.permissions.includes('usuarios.visualizar')
      ? {
          title: 'Usuários e perfis',
          description: 'Acessos, perfis e responsabilidades dos usuários.',
          icon: <TeamOutlined />,
          path: '/usuarios',
        }
      : null,
    {
      title: 'Segurança e acessos',
      description: 'Histórico de sessões e segurança da conta.',
      icon: <SafetyCertificateOutlined />,
      path: '/minha-conta/acessos',
    },
    user?.permissions.includes('configuracoes.visualizar')
      ? {
          title: 'Assinatura',
          description: 'Plano contratado, limites e consumo do tenant.',
          icon: <CreditCardOutlined />,
          path: '/assinatura',
        }
      : null,
  ];
  const cards = availableCards.filter((item): item is SettingsCard => item !== null);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Configurações do sistema"
        description="Administre campanhas, acessos e parâmetros operacionais em um único lugar."
      />
      <section>
        <Typography.Title level={4}>Administração</Typography.Title>
        <div className={styles.settingsGrid}>
          {cards.map((item) => (
            <Card
              key={item.path}
              hoverable
              className={styles.settingsCard}
              onClick={() => navigate(item.path)}
            >
              <div className={styles.settingsIcon}>{item.icon}</div>
              <div className={styles.settingsContent}>
                <Typography.Title level={5}>{item.title}</Typography.Title>
                <Typography.Text type="secondary">{item.description}</Typography.Text>
              </div>
              <RightOutlined className={styles.settingsArrow} />
            </Card>
          ))}
        </div>
      </section>
      {canViewGeneralSettings && configQuery.error && (
        <Alert type="error" showIcon message={normalizeApiError(configQuery.error).message} />
      )}
      {canViewGeneralSettings && (
        <section>
          <Typography.Title level={4}>
            <SettingOutlined /> Configurações gerais
          </Typography.Title>
          <Card className={styles.card}>
            {configQuery.isPending ? (
              <Skeleton active />
            ) : (
              <Form
                form={form}
                layout="vertical"
                className={styles.form}
                onFinish={(values) => save.mutate(values)}
              >
                <Form.Item name="nome_publico" label="Nome público">
                  <Input maxLength={180} />
                </Form.Item>
                <Form.Item
                  name="cor_primaria"
                  label="Cor principal"
                  getValueFromEvent={(color) => color?.toHexString().toUpperCase()}
                  rules={[{ pattern: /^#[0-9A-F]{6}$/, message: 'Use #RRGGBB.' }]}
                >
                  <ColorPicker
                    allowClear
                    disabledAlpha
                    disabledFormat
                    format="hex"
                    showText={(color) => color.toHexString().toUpperCase()}
                  />
                </Form.Item>
                <Form.Item label="Logotipo" className={styles.full}>
                  <Space align="start" wrap>
                    {storedLogoQuery.isPending && storedLogoUrl?.startsWith('/api/') ? (
                      <Skeleton.Image active className={styles.logoPreview} />
                    ) : logoPreviewUrl ? (
                      <Image
                        src={logoPreviewUrl}
                        alt="Logotipo gravado"
                        width={180}
                        height={100}
                        className={styles.logoPreview}
                      />
                    ) : (
                      <div className={styles.logoPlaceholder}>Nenhum logotipo gravado</div>
                    )}
                    <Upload
                      accept="image/png,image/jpeg,image/webp"
                      beforeUpload={(file) => {
                        uploadLogo.mutate(file);
                        return Upload.LIST_IGNORE;
                      }}
                      disabled={uploadLogo.isPending}
                      showUploadList={false}
                    >
                      <Button icon={<UploadOutlined />} loading={uploadLogo.isPending}>
                        {logoPreviewUrl ? 'Substituir imagem' : 'Selecionar imagem'}
                      </Button>
                    </Upload>
                  </Space>
                </Form.Item>
                <Form.Item name="fuso_horario" label="Fuso horário">
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder="Selecione um fuso horário"
                    options={TIME_ZONE_OPTIONS}
                  />
                </Form.Item>
                <Form.Item name="percentual_alerta_meta" label="Alerta de meta (%)">
                  <InputNumber min={0} max={100} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item className={styles.full}>
                  <Button type="primary" htmlType="submit" loading={save.isPending}>
                    Salvar configurações
                  </Button>
                </Form.Item>
              </Form>
            )}
          </Card>
        </section>
      )}
    </div>
  );
}
