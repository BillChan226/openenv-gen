import clsx from 'clsx';

/**
 * Layout Container
 * - Centers content
 * - Provides consistent horizontal padding
 * - Limits max width to match the design grid
 */
export function Container({ as: Comp = 'div', className, children, ...props }) {
  return (
    <Comp
      className={clsx('mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8', className)}
      {...props}
    >
      {children}
    </Comp>
  );
}

export default Container;
