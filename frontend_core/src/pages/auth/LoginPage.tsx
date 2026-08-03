import {
  BankOutlined,
  LockOutlined,
  MailOutlined,
  PieChartOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Alert, Button, Form, Input, Space, Typography } from 'antd';
import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { Brand } from '@/components/brand/Brand';
import { getDefaultRoute } from '@/app/navigation';
import { login } from '@/modules/auth/auth-service';
import { passwordMinLengthRule } from '@/modules/auth/password-policy';
import { normalizeApiError } from '@/services/api/api-error';
import { mapAuthUser, useSessionStore } from '@/stores/session-store';

import styles from './LoginPage.module.css';

interface LoginFormValues {
  tenantSlug: string;
  email: string;
  password: string;
  mfaCode?: string;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mfaRequired, setMfaRequired] = useState(false);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const mustChangePassword = useSessionStore((state) => state.user?.mustChangePassword);
  const setSession = useSessionStore((state) => state.setSession);

  if (isAuthenticated) {
    return (
      <Navigate to={mustChangePassword ? '/minha-conta/alterar-senha' : '/dashboard'} replace />
    );
  }

  const handleSubmit = async (values: LoginFormValues) => {
    setSubmitting(true);
    setError(null);

    try {
      const authentication = await login({
        tenant_slug: values.tenantSlug,
        email: values.email,
        senha: values.password,
        dispositivo: window.navigator.userAgent.slice(0, 180),
        codigo_mfa: values.mfaCode,
      });
      useSessionStore
        .getState()
        .updateAuthentication(
          authentication.usuario,
          authentication.access_token,
          authentication.refresh_token,
          authentication.expires_in,
        );
      const tenant = authentication.usuario.tenant;
      setSession(
        mapAuthUser(authentication.usuario),
        {
          id: tenant.id,
          name: tenant.nome,
          slug: tenant.slug,
          status: tenant.status,
        },
        null,
        authentication.access_token,
        authentication.refresh_token,
        authentication.expires_in,
      );
      const destination = authentication.usuario.deve_alterar_senha
        ? '/minha-conta/alterar-senha'
        : ((location.state as { from?: string } | null)?.from ??
            getDefaultRoute(
              authentication.usuario.permissoes,
              authentication.usuario.perfis.map((profile) => profile.codigo),
            ));
      navigate(destination, { replace: true });
    } catch (requestError) {
      useSessionStore.getState().clearSession();
      const apiError = normalizeApiError(requestError);
      if (apiError.code === 'mfa_required') {
        setMfaRequired(true);
      }
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.formPanel}>
        <div className={styles.formWrapper}>
          <Brand />
          <div className={styles.intro}>
            <Typography.Title level={2}>Acesse sua campanha</Typography.Title>
            <Typography.Text type="secondary">
              Entre para acompanhar pessoas, territórios, metas e demandas.
            </Typography.Text>
          </div>

          {error && <Alert type="error" showIcon message={error} />}

          <Form<LoginFormValues>
            layout="vertical"
            requiredMark={false}
            onFinish={handleSubmit}
            size="large"
          >
            <Form.Item
              label="Campanha"
              name="tenantSlug"
              rules={[
                { required: true, message: 'Informe o identificador da campanha.' },
                {
                  pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
                  message: 'Use letras minúsculas, números e hífens.',
                },
              ]}
            >
              <Input
                prefix={<BankOutlined />}
                placeholder="nome-da-campanha"
                autoComplete="organization"
              />
            </Form.Item>
            {mfaRequired && (
              <Form.Item
                label="Código de autenticação"
                name="mfaCode"
                rules={[
                  { required: true, message: 'Informe o código do aplicativo autenticador.' },
                  { pattern: /^\d{6}$/, message: 'O código deve possuir seis números.' },
                ]}
              >
                <Input
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  autoComplete="one-time-code"
                />
              </Form.Item>
            )}
            <Form.Item
              label="E-mail"
              name="email"
              rules={[
                { required: true, message: 'Informe seu e-mail.' },
                { type: 'email', message: 'Informe um e-mail válido.' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="nome@campanha.com.br"
                autoComplete="email"
              />
            </Form.Item>
            <Form.Item
              label="Senha"
              name="password"
              rules={[
                { required: true, message: 'Informe sua senha.' },
                passwordMinLengthRule,
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Digite sua senha"
                autoComplete="current-password"
              />
            </Form.Item>

            <div className={styles.formOptions}>
              <span />
              <Button type="link" size="small">
                Esqueci minha senha
              </Button>
            </div>

            <Button
              type="primary"
              htmlType="submit"
              block
              loading={submitting}
              className={styles.submit}
            >
              Entrar
            </Button>
          </Form>
        </div>
      </section>

      <section className={styles.visualPanel} aria-label="Visão geral da plataforma">
        <div className={styles.visualContent}>
          <span className={styles.eyebrow}>INTELIGÊNCIA ELEITORAL</span>
          <Typography.Title>Decisões melhores começam com dados organizados.</Typography.Title>
          <Typography.Paragraph>
            Centralize sua operação, acompanhe a evolução da campanha e mantenha a equipe alinhada
            em uma única plataforma.
          </Typography.Paragraph>
          <div className={styles.featureGrid}>
            <div>
              <TeamOutlined />
              <strong>Base unificada</strong>
              <span>Eleitores e lideranças</span>
            </div>
            <div>
              <PieChartOutlined />
              <strong>Visão territorial</strong>
              <span>Metas e desempenho</span>
            </div>
            <div>
              <SafetyCertificateOutlined />
              <strong>Dados protegidos</strong>
              <span>Acesso por perfil</span>
            </div>
          </div>
          <div className={styles.dashboardPreview} aria-hidden="true">
            <div className={styles.previewHeader}>
              <span />
              <span />
              <span />
            </div>
            <div className={styles.previewBody}>
              <div className={styles.previewSidebar} />
              <div className={styles.previewMain}>
                <Space className={styles.previewCards}>
                  <span />
                  <span />
                  <span />
                </Space>
                <div className={styles.previewChart}>
                  {[42, 68, 51, 86, 72, 94, 78].map((height, index) => (
                    <i key={index} style={{ height: `${height}%` }} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
