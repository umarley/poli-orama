import { useQuery } from '@tanstack/react-query';
import { Select, Spin } from 'antd';
import type { SelectProps } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { buscarPessoas } from '@/modules/cadastro/pessoas-service';

type PersonOption = { value: number; label: string };

export interface RemotePersonSelectProps extends Omit<
  SelectProps<number>,
  'filterOption' | 'loading' | 'notFoundContent' | 'onSearch' | 'options' | 'showSearch'
> {
  excludeIds?: Iterable<number>;
  initialOptions?: PersonOption[];
  minimumSearchLength?: number;
}

export function RemotePersonSelect({
  excludeIds,
  initialOptions = [],
  minimumSearchLength = 2,
  placeholder = 'Digite ao menos dois caracteres',
  value,
  ...props
}: RemotePersonSelectProps) {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearch(search.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [search]);

  const peopleQuery = useQuery({
    queryKey: ['cadastro', 'pessoas', 'busca-remota', debouncedSearch],
    queryFn: () => buscarPessoas(debouncedSearch),
    enabled: debouncedSearch.length >= minimumSearchLength,
  });

  const excluded = useMemo(() => new Set(excludeIds ?? []), [excludeIds]);
  const options = useMemo(() => {
    const byId = new Map<number, PersonOption>();
    initialOptions.forEach((option) => byId.set(option.value, option));
    (peopleQuery.data ?? []).forEach((person) =>
      byId.set(person.id, { value: person.id, label: person.nome_completo }),
    );
    return Array.from(byId.values()).filter(
      (option) => option.value === value || !excluded.has(option.value),
    );
  }, [excluded, initialOptions, peopleQuery.data, value]);

  const trimmedSearch = search.trim();
  const notFoundContent = peopleQuery.isFetching ? (
    <Spin size="small" />
  ) : trimmedSearch.length < minimumSearchLength ? (
    `Digite ao menos ${minimumSearchLength} caracteres`
  ) : (
    'Nenhuma pessoa encontrada'
  );

  return (
    <Select<number>
      {...props}
      value={value}
      showSearch
      filterOption={false}
      loading={peopleQuery.isFetching}
      placeholder={placeholder}
      onSearch={setSearch}
      options={options}
      notFoundContent={notFoundContent}
    />
  );
}
