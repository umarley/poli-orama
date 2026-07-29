import { useQuery } from '@tanstack/react-query';
import { Col, Form, Row, Select } from 'antd';

import {
  listarLocaisVotacao,
  listarSecoes,
  listarZonas,
} from '@/modules/territorios/territorios-service';

interface ElectoralLocationFieldsProps {
  codigoMunicipioIbge?: number;
  hideSection?: boolean;
  fullWidthPollingPlace?: boolean;
  requireMunicipality?: boolean;
}

export function ElectoralSectionField() {
  const form = Form.useFormInstance();
  const zoneId = Form.useWatch('zona_eleitoral_id', form) as number | undefined;
  const pollingPlaceId = Form.useWatch('local_votacao_id', form) as number | undefined;
  const sections = useQuery({
    queryKey: ['global', 'secoes', zoneId, pollingPlaceId],
    queryFn: () => listarSecoes(zoneId!, pollingPlaceId),
    enabled: Boolean(zoneId),
  });

  return (
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
  );
}

export function ElectoralLocationFields({
  codigoMunicipioIbge,
  hideSection = false,
  fullWidthPollingPlace = false,
  requireMunicipality = false,
}: ElectoralLocationFieldsProps) {
  const form = Form.useFormInstance();
  const zoneId = Form.useWatch('zona_eleitoral_id', form) as number | undefined;
  const zones = useQuery({
    queryKey: ['global', 'zonas', codigoMunicipioIbge],
    queryFn: () => listarZonas(undefined, codigoMunicipioIbge),
    enabled: !requireMunicipality || Boolean(codigoMunicipioIbge),
  });
  const pollingPlaces = useQuery({
    queryKey: ['global', 'locais-votacao', codigoMunicipioIbge, zoneId],
    queryFn: () =>
      listarLocaisVotacao({
        codigo_municipio_ibge: codigoMunicipioIbge,
        zona_eleitoral_id: zoneId,
      }),
    enabled: Boolean(codigoMunicipioIbge || zoneId),
  });

  return (
    <Row gutter={12}>
      <Col xs={24} md={fullWidthPollingPlace ? 24 : 8}>
        <Form.Item name="zona_eleitoral_id" label="Zona eleitoral">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            disabled={requireMunicipality && !codigoMunicipioIbge}
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
      <Col xs={24} md={fullWidthPollingPlace ? 24 : hideSection ? 16 : 10}>
        <Form.Item name="local_votacao_id" label="Local de votação">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            disabled={!zoneId && !codigoMunicipioIbge}
            loading={pollingPlaces.isPending}
            options={(pollingPlaces.data ?? []).map((item) => ({
              value: item.id,
              label: item.nome,
            }))}
            onChange={() => form.setFieldValue('secao_eleitoral_id', undefined)}
          />
        </Form.Item>
      </Col>
      {hideSection ? null : (
        <Col xs={24} md={6}>
          <ElectoralSectionField />
        </Col>
      )}
    </Row>
  );
}
