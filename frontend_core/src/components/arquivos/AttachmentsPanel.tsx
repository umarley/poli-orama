import {
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  PaperClipOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Image, Input, Modal, Select, Space, Table, Tag, Upload } from 'antd';
import type { UploadFile } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import {
  downloadAttachment,
  getAttachmentBlob,
  listAttachments,
  listAttachmentTypes,
  removeAttachment,
  uploadAttachment,
  uploadPersonPhoto,
} from '@/modules/arquivos/arquivos-service';
import type { Attachment, AttachmentEntity } from '@/modules/arquivos/types';
import { normalizeApiError } from '@/services/api/api-error';
import { formatInteger, formatNumber } from '@/utils/number-format';

interface UploadValues {
  typeId: number;
  description?: string;
  file: UploadFile[];
}

interface AttachmentsPanelProps {
  entity: AttachmentEntity;
  entityId: number;
  canEdit?: boolean;
  allowedTypeCodes?: string[];
  enablePersonPhoto?: boolean;
}

function formatSize(bytes: number | null) {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${formatInteger(bytes)} B`;
  if (bytes < 1024 * 1024) return `${formatNumber(bytes / 1024, 1, 1)} KB`;
  return `${formatNumber(bytes / 1024 / 1024, 1, 1)} MB`;
}

export function AttachmentsPanel({
  entity,
  entityId,
  canEdit = false,
  allowedTypeCodes,
  enablePersonPhoto = false,
}: AttachmentsPanelProps) {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<UploadValues>();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [preview, setPreview] = useState<{ item: Attachment; url: string } | null>(null);
  const queryKey = ['arquivos', entity, entityId];
  const attachments = useQuery({
    queryKey,
    queryFn: () => listAttachments(entity, entityId),
    enabled: entityId > 0,
  });
  const types = useQuery({
    queryKey: ['arquivos', 'tipos'],
    queryFn: listAttachmentTypes,
  });
  const availableTypes = useMemo(
    () =>
      (types.data ?? []).filter(
        (item) => !allowedTypeCodes || allowedTypeCodes.includes(item.codigo),
      ),
    [allowedTypeCodes, types.data],
  );

  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview.url);
    },
    [preview],
  );

  const upload = useMutation({
    mutationFn: async (values: UploadValues) => {
      const selected = values.file[0]?.originFileObj;
      if (!selected) throw new Error('Selecione um arquivo.');
      const selectedType = availableTypes.find((item) => item.id === values.typeId);
      if (enablePersonPhoto && entity === 'pessoa' && selectedType?.codigo === 'foto') {
        return uploadPersonPhoto(entityId, selected);
      }
      return uploadAttachment({
        entity,
        entityId,
        typeId: values.typeId,
        description: values.description,
        file: selected,
      });
    },
    onSuccess: async () => {
      AppToast.success('Arquivo anexado.');
      setUploadOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const remove = useMutation({
    mutationFn: removeAttachment,
    onSuccess: async () => {
      AppToast.success('Anexo removido.');
      await queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const showPreview = async (item: Attachment) => {
    try {
      const blob = await getAttachmentBlob(item.id, true);
      setPreview((current) => {
        if (current) URL.revokeObjectURL(current.url);
        return { item, url: URL.createObjectURL(blob) };
      });
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };
  const download = async (item: Attachment) => {
    try {
      await downloadAttachment(item);
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };

  return (
    <>
      <Card
        title={
          <Space>
            <PaperClipOutlined />
            Anexos
          </Space>
        }
        extra={
          canEdit ? (
            <Button icon={<PlusOutlined />} onClick={() => setUploadOpen(true)}>
              Anexar arquivo
            </Button>
          ) : null
        }
      >
        <Table
          rowKey="id"
          loading={attachments.isLoading}
          dataSource={attachments.data ?? []}
          pagination={false}
          columns={[
            {
              title: 'Arquivo',
              render: (_, item) => (
                <Space direction="vertical" size={0}>
                  <strong>{item.arquivo.nome_original}</strong>
                  <small>{formatSize(item.arquivo.tamanho_bytes)}</small>
                </Space>
              ),
            },
            {
              title: 'Tipo',
              render: (_, item) => <Tag>{item.tipo?.nome ?? 'Arquivo'}</Tag>,
            },
            { title: 'Descrição', dataIndex: 'descricao' },
            {
              title: 'Ações',
              width: 170,
              render: (_, item) => (
                <Space>
                  {item.preview_url ? (
                    <Button
                      aria-label="Visualizar"
                      icon={<EyeOutlined />}
                      onClick={() => void showPreview(item)}
                    />
                  ) : null}
                  <Button
                    aria-label="Baixar"
                    icon={<DownloadOutlined />}
                    onClick={() => void download(item)}
                  />
                  {canEdit ? (
                    <Button
                      danger
                      aria-label="Remover"
                      icon={<DeleteOutlined />}
                      loading={remove.isPending}
                      onClick={() =>
                        Modal.confirm({
                          title: 'Remover anexo?',
                          content: 'O registro será inativado e preservado para auditoria.',
                          okText: 'Remover',
                          okButtonProps: { danger: true },
                          onOk: () => remove.mutateAsync(item.id),
                        })
                      }
                    />
                  ) : null}
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={uploadOpen}
        title="Anexar arquivo"
        okText="Enviar"
        confirmLoading={upload.isPending}
        onCancel={() => setUploadOpen(false)}
        onOk={() => form.validateFields().then((values) => upload.mutate(values))}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="typeId"
            label="Tipo"
            rules={[{ required: true, message: 'Selecione o tipo.' }]}
          >
            <Select
              options={availableTypes.map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
            />
          </Form.Item>
          <Form.Item name="description" label="Descrição">
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item
            name="file"
            label="Arquivo"
            valuePropName="fileList"
            getValueFromEvent={(event) => event?.fileList}
            rules={[{ required: true, message: 'Selecione o arquivo.' }]}
          >
            <Upload.Dragger beforeUpload={() => false} maxCount={1}>
              Clique ou arraste o arquivo para esta área.
            </Upload.Dragger>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={Boolean(preview)}
        title={preview?.item.arquivo.nome_original}
        footer={null}
        width="min(960px, 92vw)"
        onCancel={() => setPreview(null)}
        destroyOnClose
      >
        {preview?.item.arquivo.extensao === 'pdf' ? (
          <iframe
            title="Pré-visualização do PDF"
            src={preview.url}
            sandbox=""
            style={{ border: 0, width: '100%', height: '70vh' }}
          />
        ) : preview ? (
          <Image src={preview.url} alt={preview.item.arquivo.nome_original} />
        ) : null}
      </Modal>
    </>
  );
}
