import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

export function Modal({ open, onOpenChange, title, description, children, footer, trigger, contentClassName }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger ? <Dialog.Trigger asChild>{trigger}</Dialog.Trigger> : null}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40" />
        <Dialog.Content
          className={
            contentClassName ||
            'fixed left-1/2 top-1/2 w-[calc(100vw-2rem)] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-5 shadow-lg focus:outline-none'
          }
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <Dialog.Title className="text-lg font-semibold text-gray-900">{title}</Dialog.Title>
              {description ? <Dialog.Description className="mt-1 text-sm text-gray-600">{description}</Dialog.Description> : null}
            </div>
            <Dialog.Close asChild>
              <button type="button" className="rounded p-1 hover:bg-gray-100 focus-ring" aria-label="Close" data-testid="modal-close">
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          <div className="mt-4">{children}</div>

          {footer ? <div className="mt-5 flex items-center justify-end gap-2">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
