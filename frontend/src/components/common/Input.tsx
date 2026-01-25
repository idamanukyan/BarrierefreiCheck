/**
 * Input Component
 *
 * Form input with label, error handling, and icons.
 */

import React, { forwardRef } from 'react';
import clsx from 'clsx';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      hint,
      icon,
      iconPosition = 'left',
      fullWidth = true,
      className,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || props.name;

    return (
      <div className={clsx(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <div className="relative">
          {icon && iconPosition === 'left' && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              'block rounded-lg border bg-white text-gray-900 placeholder-gray-400',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
              'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
              'transition-colors',
              error
                ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-300',
              icon && iconPosition === 'left' && 'pl-10',
              icon && iconPosition === 'right' && 'pr-10',
              !icon && 'px-3',
              'py-2 text-sm',
              fullWidth && 'w-full',
              className
            )}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
            {...props}
          />
          {icon && iconPosition === 'right' && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              {icon}
            </div>
          )}
        </div>
        {error && (
          <p id={`${inputId}-error`} className="mt-1 text-sm text-red-600">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${inputId}-hint`} className="mt-1 text-sm text-gray-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  fullWidth?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, hint, fullWidth = true, className, id, ...props }, ref) => {
    const textareaId = id || props.name;

    return (
      <div className={clsx(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={clsx(
            'block rounded-lg border bg-white text-gray-900 placeholder-gray-400 px-3 py-2 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'transition-colors resize-y min-h-[80px]',
            error
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : 'border-gray-300',
            fullWidth && 'w-full',
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${textareaId}-error` : hint ? `${textareaId}-hint` : undefined}
          {...props}
        />
        {error && (
          <p id={`${textareaId}-error`} className="mt-1 text-sm text-red-600">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${textareaId}-hint`} className="mt-1 text-sm text-gray-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  options: Array<{ value: string; label: string }>;
  fullWidth?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, hint, options, fullWidth = true, className, id, ...props }, ref) => {
    const selectId = id || props.name;

    return (
      <div className={clsx(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={clsx(
            'block rounded-lg border bg-white text-gray-900 px-3 py-2 text-sm',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'disabled:bg-gray-50 disabled:text-gray-500 disabled:cursor-not-allowed',
            'transition-colors appearance-none cursor-pointer',
            error
              ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
              : 'border-gray-300',
            fullWidth && 'w-full',
            className
          )}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={error ? `${selectId}-error` : hint ? `${selectId}-hint` : undefined}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p id={`${selectId}-error`} className="mt-1 text-sm text-red-600">
            {error}
          </p>
        )}
        {hint && !error && (
          <p id={`${selectId}-hint`} className="mt-1 text-sm text-gray-500">
            {hint}
          </p>
        )}
      </div>
    );
  }
);

Select.displayName = 'Select';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string;
  description?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, className, id, ...props }, ref) => {
    const checkboxId = id || props.name;

    return (
      <div className={clsx('flex items-start', className)}>
        <input
          ref={ref}
          type="checkbox"
          id={checkboxId}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer mt-0.5"
          {...props}
        />
        <div className="ml-3">
          <label htmlFor={checkboxId} className="text-sm font-medium text-gray-700 cursor-pointer">
            {label}
          </label>
          {description && (
            <p className="text-sm text-gray-500">{description}</p>
          )}
        </div>
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

export default Input;
