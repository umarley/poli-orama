import { useQuery } from '@tanstack/react-query';
import { Col, Form, Row, Select } from 'antd';

import {
  listarLocaisVotacao,
  listarSecoes,
  listarZonas,
} from '@/modules/territorios/territorios-service';

interface ElectoralLocationFieldsProps {
  municipioId?: number;
}

export function ElectoralLocationFields({ municipioId }: ElectoralLocationFieldsProps) {
  const form = Form.useFormInstance();
  const zoneId = Form.useWatch('zona_eleitoral_id', form) as number | undefined;
  const pollingPlaceId = Form.useWatch('local_votacao_id', form) as number | undefined;
  const zones = useQuery({
    queryKey: ['global', 'zonas', municipioId],
    queryFn: () => listarZonas(undefined, municipioId),
  });
  const pollingPlaces = useQuery({
    queryKey: ['global', 'locais-votacao', municipioId, zoneId],
    queryFn: () =>
      listarLocaisVotacao({ municipio_id: municipioId, zona_eleitoral_id: zoneId }),
    enabled: Boolean(municipioId || zoneId),
  });
  const sections = useQuery({
    queryKey: ['global', 'secoes', zoneId, pollingPlaceId],
    queryFn: () => listarSecoes(zoneId!, pollingPlaceId),
    enabled: Boolean(zoneId),
  });

  return (
    <Row gutter={12}>
      <Col xs={24} md={8}>
        <Form.Item name="zona_eleitoral_id" label="Zona eleitoral">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            loading={zones.isPending}
            options={(zones.data ?? []).map((item) => ({
              value: item.id,
              label: `Zona ${item.numero_zona}${item.descricao ? ` · ${item.descricao}` : ''}`,
            }))}
            onChange={() => {
              form.setFieldsValue({ local_votacao_id: undefined, secao_eleitoral_id: undefined });
            }}
          />
        </Form.Item>
      </Col>
      <Col xs={24} md={10}>
        <Form.Item name="local_votacao_id" label="Local de votação">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            disabled={!zoneId && !municipioId}
            loading={pollingPlaces.isPending}
            options={(pollingPlaces.data ?? []).map((item) => ({
              value: item.id,
              label: item.nome,
            }))}
            onChange={() => form.setFieldValue('secao_eleitoral_id', undefined)}
          />
        </Form.Item>
      </Col>
      <Col xs={24} md={6}>
        <Form.Item name="secao_eleitoral_id" label="Seção">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            disabled={!zoneId}
            loading={sections.isPending}
            options={(sections.data ?? []).map((item) => ({
              value: item.id,
              label: `Seção ${item.numero_secao}`,
            }))}
          />
        </Form.Item>
      </Col>
    </Row>
  );
}
