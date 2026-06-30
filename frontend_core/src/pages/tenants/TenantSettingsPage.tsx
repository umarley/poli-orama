import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Input, InputNumber, Skeleton } from 'antd';
import { useEffect } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  getCurrentTenant,
  getTenantConfiguration,
  updateTenantConfiguration,
} from '@/modules/tenants/tenant-service';
import type { TenantConfiguration } from '@/modules/tenants/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import styles from './TenantPages.module.css';

type TenantSettingsForm = Pick<
  TenantConfiguration,
  'nome_publico' | 'cor_primaria' | 'logo_url' | 'fuso_horario' | 'percentual_alerta_meta'
>;

export function TenantSettingsPage() {
  const client = useQueryClient();
  const [form] = Form.useForm<Partial<TenantSettingsForm>>();
  const setTenant = useSessionStore((state) => state.setTenant);
  const tenantQuery = useQuery({ queryKey: ['current-tenant'], queryFn: getCurrentTenant });
  const configQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
  });
  const save = useMutation({
    mutationFn: updateTenantConfiguration,
    onSuccess: async (configuration) => {
      AppToast.success('Configurações atualizadas.');
      if (tenantQuery.data) {
        setTenant({
          id: String(tenantQuery.data.id),
          name: configuration.nome_publico || tenantQuery.data.nome,
          slug: tenantQuery.data.slug,
          status: tenantQuery.data.status,
        });
      }
      await client.invalidateQueries({ queryKey: ['tenant-configuration'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  useEffect(() => {
    if (configQuery.data) {
      const { nome_publico, cor_primaria, logo_url, fuso_horario, percentual_alerta_meta } =
        configQuery.data;
      form.setFieldsValue({
        nome_publico,
        cor_primaria,
        logo_url,
        fuso_horario,
        percentual_alerta_meta,
      });
    }
  }, [configQuery.data, form]);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Configurações do tenant"
        description="Identidade pública e parâmetros operacionais da campanha."
      />
      {configQuery.error && (
        <Alert type="error" showIcon message={normalizeApiError(configQuery.error).message} />
      )}
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
              rules={[{ pattern: /^#[0-9a-f]{6}([0-9a-f]{2})?$/i, message: 'Use #RRGGBB.' }]}
            >
              <Input placeholder="#1677ff" />
            </Form.Item>
            <Form.Item name="logo_url" label="URL do logotipo" className={styles.full}>
              <Input type="url" />
            </Form.Item>
            <Form.Item name="fuso_horario" label="Fuso horário">
              <Input />
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
    </div>
  );
}
