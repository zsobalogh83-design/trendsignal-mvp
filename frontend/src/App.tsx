import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { SignalDetail } from './pages/SignalDetail';
import { NewsFeed } from './pages/NewsFeed';
import { Configuration } from './pages/Configuration';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signal/:tickerId" element={<SignalDetail />} />
          <Route path="/news" element={<NewsFeed />} />
          <Route path="/settings" element={<Configuration />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
