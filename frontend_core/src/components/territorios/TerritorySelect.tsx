import { useQuery } from '@tanstack/react-query';
import { Select } from 'antd';
import type { SelectProps } from 'antd';

import { listarTerritorios } from '@/modules/territorios/territorios-service';

type TerritorySelectProps = Omit<SelectProps<number>, 'options'>;

export function TerritorySelect(props: TerritorySelectProps) {
  const query = useQuery({
    queryKey: ['territorios', 'options'],
    queryFn: () => listarTerritorios(false),
  });

  return (
    <Select<number>
      allowClear
      showSearch
      optionFilterProp="label"
      placeholder="Selecione um território"
      loading={query.isPending}
      options={(query.data ?? []).map((item) => ({
        value: item.id,
        label: `${item.nome} · ${item.tipo_nome}`,
      }))}
      {...props}
    />
  );
}
