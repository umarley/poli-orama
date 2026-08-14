import { useQuery } from '@tanstack/react-query';
import { Select, Spin } from 'antd';
import type { SelectProps } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { formatLeadershipLabel } from '@/components/forms/leadership-label';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';

export type RemoteLeadershipSelectProps = Omit<
  SelectProps<number>,
  'filterOption' | 'loading' | 'notFoundContent' | 'onSearch' | 'options' | 'showSearch'
>;

export function RemoteLeadershipSelect({
  placeholder = 'Selecione ou digite o nome da liderança',
  ...props
}: RemoteLeadershipSelectProps) {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  const leadershipsQuery = useQuery({
    queryKey: ['cadastro', 'liderancas', 'busca-remota', debouncedSearch],
    queryFn: () => listarLiderancas(debouncedSearch ? { query: debouncedSearch } : {}),
  });

  const options = useMemo(
    () =>
      (leadershipsQuery.data ?? []).map((leadership) => ({
        value: leadership.id,
        label: formatLeadershipLabel(leadership),
      })),
    [leadershipsQuery.data],
  );

  return (
    <Select<number>
      {...props}
      showSearch
      filterOption={false}
      loading={leadershipsQuery.isFetching}
      placeholder={placeholder}
      onSearch={setSearch}
      options={options}
      notFoundContent={
        leadershipsQuery.isFetching ? <Spin size="small" /> : 'Nenhuma liderança encontrada'
      }
    />
  );
}
