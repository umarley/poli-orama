import { Alert, Form } from 'antd';
import type { FormProps } from 'antd';
import type { ReactNode } from 'react';

export type BaseFormProps<Values extends object = Record<string, unknown>> = Omit<
  FormProps<Values>,
  'children'
> & {
  children?: ReactNode;
  submitError?: string | null;
};

export function BaseForm<Values extends object = Record<string, unknown>>({
  children,
  layout = 'vertical',
  requiredMark = false,
  scrollToFirstError = true,
  submitError,
  ...formProps
}: BaseFormProps<Values>) {
  return (
    <Form<Values>
      layout={layout}
      requiredMark={requiredMark}
      scrollToFirstError={scrollToFirstError}
      {...formProps}
    >
      {submitError ? (
        <Alert
          type="error"
          showIcon
          message="Nao foi possivel salvar"
          description={submitError}
          role="alert"
        />
      ) : null}
      {children}
    </Form>
  );
}
