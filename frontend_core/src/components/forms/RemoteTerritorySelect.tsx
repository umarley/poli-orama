import { useQuery } from '@tanstack/react-query';
import { Select, Spin } from 'antd';
import type { SelectProps } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { listarTerritorios } from '@/modules/territorios/territorios-service';

type TerritoryOption = { value: number; label: string };

export interface RemoteTerritorySelectProps extends Omit<
  SelectProps<number>,
  'filterOption' | 'loading' | 'notFoundContent' | 'onSearch' | 'options' | 'showSearch'
> {
  initialOptions?: TerritoryOption[];
}

export function RemoteTerritorySelect({
  initialOptions = [],
  placeholder = 'Selecione ou digite o nome do território',
  value,
  ...props
}: RemoteTerritorySelectProps) {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  const territoriesQuery = useQuery({
    queryKey: ['territorios', 'busca-remota', debouncedSearch],
    queryFn: () => listarTerritorios(false, debouncedSearch || undefined),
  });

  const options = useMemo(() => {
    const byId = new Map<number, TerritoryOption>();
    initialOptions.forEach((option) => byId.set(option.value, option));
    (territoriesQuery.data ?? []).forEach((territory) =>
      byId.set(territory.id, { value: territory.id, label: territory.nome }),
    );
    return Array.from(byId.values());
  }, [initialOptions, territoriesQuery.data]);

  return (
    <Select<number>
      {...props}
      value={value}
      showSearch
      allowClear
      filterOption={false}
      loading={territoriesQuery.isFetching}
      placeholder={placeholder}
      onSearch={setSearch}
      options={options}
      notFoundContent={
        territoriesQuery.isFetching ? <Spin size="small" /> : 'Nenhum território encontrado'
      }
    />
  );
}
