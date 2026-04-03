import 'react';

declare module 'react' {
  interface HTMLAttributes<T> extends AriaAttributes, DOMAttributes<T> {
    // Custom attributes for @fiddle-digital/string-tune
    string?: string;
    'string-radius'?: string | number;
    'string-strength'?: string | number;
    'string-tension'?: string | number;
    'string-friction'?: string | number;
    'string-position-strength'?: string | number;
    'string-position-tension'?: string | number;
    'string-position-friction'?: string | number;
    'string-rotation-strength'?: string | number;
    'string-rotation-tension'?: string | number;
    'string-rotation-friction'?: string | number;
    'string-continuous-push'?: string | boolean;
    'string-reveal-stagger'?: string | number;
    'string-reveal-duration'?: string | number;
  }
}
