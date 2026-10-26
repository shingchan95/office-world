import { Suspense, lazy } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import './App.css';
const OfficeWorldLazy=lazy(()=>import('./components/OfficeWorld'));
export function App() {
 return <ErrorBoundary><Suspense fallback={<div className="loading-screen"><div className="loading-content"><div className="spinner"/><p>Loading Office World…</p></div></div>}><OfficeWorldLazy/></Suspense></ErrorBoundary>;
}
export default App;
