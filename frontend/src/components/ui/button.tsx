import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ButtonHTMLAttributes } from "react";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" | "danger"; size?: "default" | "small" };

export function Button({ className, variant = "primary", size = "default", ...props }: ButtonProps) {
  return <button className={cn("button", `button-${variant}`, `button-${size}`, className)} {...props} />;
}
