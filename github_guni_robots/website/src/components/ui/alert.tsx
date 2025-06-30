import React, { ReactNode, HTMLAttributes } from 'react';
import classNames from 'classnames';

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
  children: ReactNode;
}

export const Alert = ({ className = '', children, ...props }: AlertProps) => (
  <div className={classNames('p-4 rounded-lg border flex items-start gap-3', className)} {...props}>
    {children}
  </div>
);

export const AlertDescription = ({ className = '', children, ...props }: AlertProps) => (
  <div className={classNames('text-sm', className)} {...props}>
    {children}
  </div>
);
