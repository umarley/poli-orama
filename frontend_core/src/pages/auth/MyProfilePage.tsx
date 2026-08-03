import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button, Card, Form, Input, Space, Tag, Typography } from 'antd';
import { useEffect } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { PasswordStrengthMeter } from '@/components/forms/PasswordStrengthMeter';
import { PageHeader } from '@/components/layout/PageHeader';
import { changePassword, getCurrentUser, updateCurrentUser } from '@/modules/auth/auth-service';
import {
  PASSWORD_POLICY_HINT,
  passwordMinLengthRule,
} from '@/modules/auth/password-policy';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatPhoneContact, isValidPhoneContact } from '@/utils/phone-format';

import styles from '../tenants/TenantPages.module.css';

interface ProfileFormValues {
  nome: string;
  email: string;
  telefone?: string;
}

interface PasswordFormValues {
  senha_atual: string;
  nova_senha: string;
  confirmar_senha: string;
}

export function MyProfilePage() {
  const updateUser = useSessionStore((state) => state.updateUser);
  const [profileForm] = Form.useForm<ProfileFormValues>();
  const [passwordForm] = Form.useForm<PasswordFormValues>();
  const novaSenha = Form.useWatch('nova_senha', passwordForm);

  const profileQuery = useQuery({
    queryKey: ['auth-me'],
    queryFn: getCurrentUser,
  });

  useEffect(() => {
    if (profileQuery.data) {
      profileForm.setFieldsValue({
        nome: profileQuery.data.nome,
        email: profileQuery.data.email,
        telefone: profileQuery.data.telefone
          ? formatPhoneContact(profileQuery.data.telefone)
          : undefined,
      });
    }
  }, [profileForm, profileQuery.data]);

  const saveProfile = useMutation({
    mutationFn: updateCurrentUser,
    onSuccess: (user) => {
      updateUser(user);
      AppToast.success('Perfil atualizado.');
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const savePassword = useMutation({
    mutationFn: (values: PasswordFormValues) =>
      changePassword(values.senha_atual, values.nova_senha),
    onSuccess: () => {
      passwordForm.resetFields();
      AppToast.success('Senha alterada com sucesso.');
      void getCurrentUser().then(updateUser);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const user = profileQuery.data;

  return (
    <div className={styles.page}>
      <PageHeader
        title="Meu perfil"
        description="Atualize seus dados pessoais e altere sua senha de acesso."
      />

      <Card
        title={
          <Space>
            <UserOutlined />
            Dados pessoais
          </Space>
        }
        loading={profileQuery.isPending}
      >
        <Form
          form={profileForm}
          layout="vertical"
          className={styles.form}
          onFinish={({ nome, telefone }) =>
            saveProfile.mutate({
              nome,
              telefone: telefone?.trim() ? telefone : null,
            })
          }
        >
          <Form.Item name="nome" label="Nome" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="E-mail">
            <Input readOnly autoComplete="email" />
          </Form.Item>
          <Form.Item
            name="telefone"
            label="Telefone"
            normalize={formatPhoneContact}
            rules={[
              {
                validator: (_, value?: string) => {
                  if (!value?.trim()) return Promise.resolve();
                  return isValidPhoneContact(value)
                    ? Promise.resolve()
                    : Promise.reject(
                        new Error('Informe um telefone com DDD e 10 ou 11 dígitos.'),
                      );
                },
              },
            ]}
          >
            <Input inputMode="tel" autoComplete="tel" maxLength={15} placeholder="(00) 00000-0000" />
          </Form.Item>
          {user && (
            <Form.Item label="Perfis de acesso">
              <Space wrap>
                {user.perfis.map((profile) => (
                  <Tag key={profile.id}>{profile.nome}</Tag>
                ))}
              </Space>
            </Form.Item>
          )}
          <Button type="primary" htmlType="submit" loading={saveProfile.isPending}>
            Salvar alterações
          </Button>
        </Form>
      </Card>

      <Card
        title={
          <Space>
            <LockOutlined />
            Alterar senha
          </Space>
        }
      >
        <Typography.Paragraph type="secondary">{PASSWORD_POLICY_HINT}</Typography.Paragraph>
        <Form
          form={passwordForm}
          layout="vertical"
          className={styles.form}
          onFinish={(values) => savePassword.mutate(values)}
        >
          <Form.Item
            name="senha_atual"
            label="Senha atual"
            rules={[{ required: true, message: 'Informe sua senha atual.' }]}
          >
            <Input.Password autoComplete="current-password" />
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
          <Button type="primary" htmlType="submit" loading={savePassword.isPending}>
            Alterar senha
          </Button>
        </Form>
      </Card>
    </div>
  );
}
