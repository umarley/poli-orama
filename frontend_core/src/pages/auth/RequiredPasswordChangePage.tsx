import { LockOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PasswordStrengthMeter } from '@/components/forms/PasswordStrengthMeter';
import { Brand } from '@/components/brand/Brand';
import { getDefaultRoute } from '@/app/navigation';
import { changePassword, getCurrentUser } from '@/modules/auth/auth-service';
import {
  PASSWORD_POLICY_HINT,
  passwordMinLengthRule,
} from '@/modules/auth/password-policy';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import styles from '../auth/LoginPage.module.css';

interface PasswordFormValues {
  senha_atual: string;
  nova_senha: string;
  confirmar_senha: string;
}

export function RequiredPasswordChangePage() {
  const navigate = useNavigate();
  const updateUser = useSessionStore((state) => state.updateUser);
  const user = useSessionStore((state) => state.user);
  const [form] = Form.useForm<PasswordFormValues>();
  const novaSenha = Form.useWatch('nova_senha', form);

  const savePassword = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      changePassword(values.senha_atual, values.nova_senha),
    onSuccess: async () => {
      const profile = await getCurrentUser();
      updateUser(profile);
      AppToast.success('Senha alterada com sucesso. Você já pode usar o sistema.');
      navigate(
        getDefaultRoute(profile.permissoes, profile.perfis.map((item) => item.codigo)),
        { replace: true },
      );
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  return (
    <main className={styles.page}>
      <section className={styles.formPanel}>
        <div className={styles.formWrapper}>
          <Brand />
          <Typography.Title level={2}>Defina uma nova senha</Typography.Title>
          <Typography.Paragraph type="secondary">
            {user?.name ? `${user.name}, ` : ''}sua senha foi redefinida por um administrador.
            Por segurança, você precisa escolher uma nova senha antes de continuar.
          </Typography.Paragraph>

          <Alert
            type="warning"
            showIcon
            message="Troca de senha obrigatória"
            description="Use a senha temporária recebida como 'Senha atual' e crie uma nova senha pessoal."
            style={{ marginBottom: 16 }}
          />

          <Card>
            <Typography.Paragraph type="secondary">{PASSWORD_POLICY_HINT}</Typography.Paragraph>
            <Form form={form} layout="vertical" onFinish={(values) => savePassword.mutate(values)}>
              <Form.Item
                name="senha_atual"
                label="Senha atual (temporária)"
                rules={[{ required: true, message: 'Informe a senha temporária.' }]}
              >
                <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
              </Form.Item>
              <Form.Item
                name="nova_senha"
                label="Nova senha"
                rules={[{ required: true }, passwordMinLengthRule]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <PasswordStrengthMeter password={novaSenha ?? ''} />
              <Form.Item
                name="confirmar_senha"
                label="Confirmar nova senha"
                dependencies={['nova_senha']}
                rules={[
                  { required: true, message: 'Confirme a nova senha.' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('nova_senha') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('As senhas não coincidem.'));
                    },
                  }),
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
              <Button type="primary" htmlType="submit" block loading={savePassword.isPending}>
                Salvar nova senha
              </Button>
            </Form>
          </Card>
        </div>
      </section>
    </main>
  );
}
