import { SearchOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Select, Space } from 'antd';

export interface FilterValues {
  search?: string;
  status?: string;
}

interface BaseFilterBarProps {
  initialValues?: FilterValues;
  loading?: boolean;
  onFilter: (values: FilterValues) => void;
  onClear?: () => void;
}

export function BaseFilterBar({ initialValues, loading, onFilter, onClear }: BaseFilterBarProps) {
  const [form] = Form.useForm<FilterValues>();

  const handleClear = () => {
    form.resetFields();
    onClear?.();
  };

  return (
    <Card size="small">
      <Form
        form={form}
        layout="inline"
        initialValues={initialValues}
        onFinish={onFilter}
        aria-label="Filtros da listagem"
      >
        <Form.Item name="search">
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Buscar por nome ou local"
            aria-label="Buscar"
          />
        </Form.Item>
        <Form.Item name="status">
          <Select
            allowClear
            placeholder="Todos os status"
            aria-label="Status"
            options={[
              { value: 'ativo', label: 'Ativo' },
              { value: 'inativo', label: 'Inativo' },
            ]}
            style={{ minWidth: 160 }}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={loading}>
              Filtrar
            </Button>
            <Button htmlType="button" onClick={handleClear}>
              Limpar
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Card>
  );
}
