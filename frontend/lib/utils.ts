import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** shadcn's convention: compose class lists, letting the later Tailwind class win. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
