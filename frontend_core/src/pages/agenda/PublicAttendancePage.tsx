import { CalendarOutlined, CheckCircleOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Input, Result, Spin, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useParams } from 'react-router-dom';

import {
  confirmPublicAttendance,
  getPublicAttendanceEvent,
} from '@/modules/agenda/public-attendance-service';
import type { PublicAttendanceInput, PublicAttendanceResult } from '@/modules/agenda/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './PublicAttendancePage.module.css';

function formatPhone(value: string) {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }
  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
}

export function PublicAttendancePage() {
  const { uuid = '' } = useParams();
  const [result, setResult] = useState<PublicAttendanceResult | null>(null);
  const eventQuery = useQuery({
    queryKey: ['agenda', 'presenca-publica', uuid],
    queryFn: () => getPublicAttendanceEvent(uuid),
    enabled: Boolean(uuid),
    retry: false,
  });
  const confirmation = useMutation({
    mutationFn: (values: PublicAttendanceInput) => confirmPublicAttendance(uuid, values),
    onSuccess: setResult,
  });

  if (eventQuery.isLoading) {
    return (
      <div className={styles.loading}>
        <Spin size="large" tip="Carregando evento" />
      </div>
    );
  }
  if (eventQuery.error || !eventQuery.data) {
    return (
      <div className={styles.page}>
        <div className={styles.shell}>
          <Card className={styles.card}>
            <Result
              status="404"
              title="Evento não encontrado"
              subTitle="Este link não é válido ou o evento não está mais disponível."
            />
          </Card>
        </div>
      </div>
    );
  }

  const event = eventQuery.data;
  const startsAt = dayjs(event.data_inicio);
  const endsAt = event.data_fim ? dayjs(event.data_fim) : null;
  if (result) {
    const outsideWindow = result.status === 'fora_do_periodo';
    return (
      <div className={styles.page}>
        <div className={styles.shell}>
          <div className={styles.brand}>Elocivico</div>
          <Card className={styles.card}>
            <Result
              status={outsideWindow ? 'warning' : 'success'}
              icon={outsideWindow ? undefined : <CheckCircleOutlined />}
              title={
                result.status === 'confirmada'
                  ? 'Presença confirmada!'
                  : result.status === 'ja_confirmada'
                    ? 'Presença já registrada'
                    : 'Dados recebidos'
              }
              subTitle={result.message}
            />
          </Card>
        </div>
      </div>
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <div className={styles.brand}>Elocivico</div>
        <Card className={styles.card}>
          <header className={styles.eventHeader}>
            <div className={styles.eyebrow}>Confirmação de presença</div>
            <h1>{event.titulo}</h1>
            <div className={styles.eventMeta}>
              <span>
                <CalendarOutlined /> {startsAt.format('DD/MM/YYYY')} · {startsAt.format('HH:mm')}
                {endsAt ? ` às ${endsAt.format('HH:mm')}` : ''}
              </span>
              {event.local_nome && (
                <span>
                  <EnvironmentOutlined /> {event.local_nome}
                </span>
              )}
            </div>
          </header>

          <Typography.Paragraph className={styles.intro}>
            Preencha seus dados para registrar sua participação neste evento.
          </Typography.Paragraph>
          {!event.confirmacao_aberta && (
            <Alert
              showIcon
              type="warning"
              message="Fora do período de confirmação"
              description="Seus dados serão salvos, mas a presença só pode ser confirmada entre 15 minutos antes do início e 1 hora após o término do evento."
              style={{ marginBottom: 20 }}
            />
          )}
          {confirmation.error && (
            <Alert
              showIcon
              type="error"
              message={normalizeApiError(confirmation.error).message}
              style={{ marginBottom: 20 }}
            />
          )}

          <Form<PublicAttendanceInput>
            layout="vertical"
            requiredMark="optional"
            onFinish={(values) => confirmation.mutate(values)}
          >
            <Form.Item
              name="nome_completo"
              label="Nome completo"
              rules={[
                { required: true, message: 'Informe seu nome completo.' },
                { min: 3, message: 'Informe ao menos três caracteres.' },
              ]}
            >
              <Input size="large" autoComplete="name" maxLength={180} />
            </Form.Item>
            <Form.Item
              name="celular"
              label="Celular/WhatsApp"
              rules={[
                { required: true, message: 'Informe seu celular.' },
                {
                  validator: async (_, value: string | undefined) => {
                    const length = value?.replace(/\D/g, '').length ?? 0;
                    if (length && ![10, 11].includes(length)) {
                      throw new Error('Informe um celular com DDD.');
                    }
                  },
                },
              ]}
              normalize={(value: string) => formatPhone(value)}
            >
              <Input
                size="large"
                inputMode="tel"
                autoComplete="tel"
                placeholder="(00) 00000-0000"
              />
            </Form.Item>
            <Form.Item name="email" label="E-mail">
              <Input size="large" type="email" inputMode="email" autoComplete="email" />
            </Form.Item>
            <Form.Item name="data_nascimento" label="Data de nascimento">
              <Input
                size="large"
                type="date"
                autoComplete="bday"
                max={dayjs().format('YYYY-MM-DD')}
              />
            </Form.Item>
            <Button
              className={styles.submit}
              type="primary"
              htmlType="submit"
              loading={confirmation.isPending}
            >
              Confirmar presença
            </Button>
          </Form>
          <Typography.Text className={styles.privacy}>
            Seus dados serão utilizados para o cadastro e controle de participação no evento.
          </Typography.Text>
        </Card>
      </div>
    </main>
  );
}
