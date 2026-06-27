import {
  LockOutlined,
  MailOutlined,
  PieChartOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Alert, Button, Checkbox, Form, Input, Space, Typography } from 'antd';
import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { Brand } from '@/components/brand/Brand';
import { useSessionStore } from '@/stores/session-store';

import styles from './LoginPage.module.css';

interface LoginFormValues {
  email: string;
  password: string;
  remember?: boolean;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const setSession = useSessionStore((state) => state.setSession);

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (values: LoginFormValues) => {
    setSubmitting(true);
    setError(null);

    await new Promise((resolve) => window.setTimeout(resolve, 550));

    if (!values.email || values.password.length < 6) {
      setError('Confira seu e-mail e informe uma senha com pelo menos 6 caracteres.');
      setSubmitting(false);
      return;
    }

    setSession(
      {
        id: 'usr-demo',
        name: 'Marina Costa',
        email: values.email,
        initials: 'MC',
      },
      {
        id: 'tenant-demo',
        name: 'Ricardo Almeida',
      },
      {
        id: 'campanha-demo',
        name: 'Ricardo Almeida 2026',
        office: 'Deputado estadual',
        active: true,
        election: {
          id: 'eleicao-demo',
          year: 2026,
          type: 'estadual',
          round: 1,
          date: '2026-10-04',
        },
      },
      'token-demonstracao',
    );

    const destination = (location.state as { from?: string } | null)?.from ?? '/dashboard';
    navigate(destination, { replace: true });
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
            initialValues={{ email: 'gestor@campanha.com.br', remember: true }}
            onFinish={handleSubmit}
            size="large"
          >
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
                { min: 6, message: 'A senha deve ter pelo menos 6 caracteres.' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Digite sua senha"
                autoComplete="current-password"
              />
            </Form.Item>

            <div className={styles.formOptions}>
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>Lembrar acesso</Checkbox>
              </Form.Item>
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

          <Typography.Text type="secondary" className={styles.demoHint}>
            Ambiente inicial: use o e-mail preenchido e a senha <strong>demo123</strong>.
          </Typography.Text>
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
