'use client';
import { useEffect } from 'react';

/**
 * Suppresses noisy network/WebSocket errors from surfacing as the Next.js
 * red error overlay in development. Real errors still log to console.
 * Network errors are expected (e.g. backend warming up, WebSocket unavailable)
 * and should never crash the UI — pages already handle their own data failures.
 */
export default function ErrorSuppressor() {
  useEffect(() => {
    const onRejection = (e: PromiseRejectionEvent) => {
      const msg = String(e.reason?.message || e.reason || '');
      if (msg.includes('Network Error') || msg.includes('timeout') || e.reason?.code === 'ERR_NETWORK') {
        e.preventDefault();   // stop the overlay
        console.warn('Suppressed network error:', msg);
      }
    };
    const onError = (e: ErrorEvent) => {
      const msg = String(e.message || '');
      if (msg.includes('Network Error') || msg.includes('WebSocket')) {
        e.preventDefault();
        console.warn('Suppressed error:', msg);
      }
    };
    window.addEventListener('unhandledrejection', onRejection);
    window.addEventListener('error', onError);
    return () => {
      window.removeEventListener('unhandledrejection', onRejection);
      window.removeEventListener('error', onError);
    };
  }, []);
  return null;
}
