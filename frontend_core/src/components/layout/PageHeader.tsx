import { Breadcrumb, Flex, Typography } from 'antd';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import styles from './PageHeader.module.css';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
}

export function PageHeader({ title, description, breadcrumbs = [], actions }: PageHeaderProps) {
  return (
    <div className={styles.root}>
      {breadcrumbs.length > 0 && (
        <Breadcrumb
          items={breadcrumbs.map((item) => ({
            title: item.to ? <Link to={item.to}>{item.label}</Link> : item.label,
          }))}
        />
      )}
      <Flex className={styles.heading} justify="space-between" align="flex-start" gap={16}>
        <div>
          <Typography.Title level={3}>{title}</Typography.Title>
          {description && <Typography.Text type="secondary">{description}</Typography.Text>}
        </div>
        {actions && <div className={styles.actions}>{actions}</div>}
      </Flex>
    </div>
  );
}
