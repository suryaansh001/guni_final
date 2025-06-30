import React from 'react';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ background: 'white', color: 'black', minHeight: '100vh' }}>
      <style>{`
        a, .link, .text-link {
          color: #2563eb !important; /* Tailwind blue-600 */
          text-decoration: underline;
        }
        h1, h2, h3, h4, h5, h6, p, span, div, th, td, label, input, select, button {
          color: black !important;
        }
      `}</style>
      {children}
    </div>
  );
}