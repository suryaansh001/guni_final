import React, { ReactNode, HTMLAttributes } from 'react';
import classNames from 'classnames';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  className?: string;
  children: ReactNode;
}

export const Card = ({ className = '', children, ...props }: CardProps) => (
  <div className={classNames('bg-white rounded-lg shadow border', className)} {...props}>
    {children}
  </div>
);

export const CardHeader = ({ className = '', children, ...props }: CardProps) => (
  <div className={classNames('px-6 py-4 border-b', className)} {...props}>
    {children}
  </div>
);

export const CardTitle = ({ className = '', children, ...props }: CardProps) => (
  <h2 className={classNames('text-lg font-semibold', className)} {...props}>
    {children}
  </h2>
);

export const CardContent = ({ className = '', children, ...props }: CardProps) => (
  <div className={classNames('px-6 py-4', className)} {...props}>
    {children}
  </div>
);
