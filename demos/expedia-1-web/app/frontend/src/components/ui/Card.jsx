import React from 'react';
import clsx from 'clsx';

export function Card({ className, ...props }) {
  return <div className={clsx('card', className)} {...props} />;
}

export function CardHeader({ className, ...props }) {
  return <div className={clsx('border-b border-slate-100 p-5', className)} {...props} />;
}

export function CardBody({ className, ...props }) {
  return <div className={clsx('p-5', className)} {...props} />;
}

export function CardFooter({ className, ...props }) {
  return <div className={clsx('border-t border-slate-100 p-5', className)} {...props} />;
}
