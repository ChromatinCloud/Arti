import React from 'react';
import ReactDOM from 'react-dom/client';
import { TechFilteringPage } from '../components/TechFilteringPage';
import '../styles/tumor-only.css';
import '../styles/tumor-normal.css';

// Set initial mode
document.documentElement.setAttribute('data-mode', 'tumor-only');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <TechFilteringPage />
  </React.StrictMode>
);