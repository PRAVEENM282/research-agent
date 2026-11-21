import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { X } from "lucide-react";

export function Dialog({ open, onOpenChange, title, description, children }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="dialog-overlay" />
        <DialogPrimitive.Content className="dialog-content">
          <div className="dialog-heading">
            <div><DialogPrimitive.Title className="dialog-title">{title}</DialogPrimitive.Title><DialogPrimitive.Description className="dialog-description">{description}</DialogPrimitive.Description></div>
            <DialogPrimitive.Close asChild><button className="icon-button" aria-label="Close dialog"><X size={18} /></button></DialogPrimitive.Close>
          </div>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
