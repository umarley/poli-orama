import { Alert, Table } from 'antd';
import type { TableProps } from 'antd';

interface BaseTableProps<T extends object> extends TableProps<T> {
  error?: string | null;
  onRetry?: () => void;
}

export function BaseTable<T extends object>({ error, onRetry, ...tableProps }: BaseTableProps<T>) {
  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message="Não foi possível carregar os dados"
        description={error}
        action={onRetry ? <a onClick={onRetry}>Tentar novamente</a> : undefined}
      />
    );
  }

  return (
    <Table<T>
      scroll={{ x: 720 }}
      locale={{ emptyText: 'Nenhum registro encontrado.' }}
      {...tableProps}
    />
  );
}
