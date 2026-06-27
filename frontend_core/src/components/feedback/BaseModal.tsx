import { Modal } from 'antd';
import type { ModalProps } from 'antd';
import type { PropsWithChildren } from 'react';

interface BaseModalProps extends Omit<ModalProps, 'open'> {
  isOpen: boolean;
}

export function BaseModal({
  isOpen,
  children,
  destroyOnHidden = true,
  ...props
}: PropsWithChildren<BaseModalProps>) {
  return (
    <Modal open={isOpen} destroyOnHidden={destroyOnHidden} centered {...props}>
      {children}
    </Modal>
  );
}
