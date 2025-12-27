# TrendSignal Frontend

React + TypeScript frontend for the TrendSignal trading signals platform.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Router** - Routing
- **TanStack Query (React Query)** - Server state management
- **React Icons** - Icon library

## Project Structure

```
src/
├── api/           # API client
├── components/    # Reusable components
│   └── SignalCard/
├── hooks/         # Custom React hooks
│   └── useApi.ts  # React Query hooks
├── pages/         # Page components
│   ├── Dashboard.tsx
│   └── SignalDetail.tsx
├── types/         # TypeScript type definitions
├── utils/         # Utility functions
└── App.tsx        # Main app component
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy the environment file:
```bash
cp .env.example .env
```

### Development

Start the development server:
```bash
npm run dev
```

The app will be available at http://localhost:5173

### Build

```bash
npm run build
npm run preview
```

## Features Implemented

- ✅ Dashboard with signal cards
- ✅ Signal detail page
- ✅ Filters (decision, strength, status)
- ✅ Real-time data refresh
- ✅ Responsive design
- ✅ Type-safe API integration

## API Integration

All API calls use React Query for caching and state management.
See `src/hooks/useApi.ts` for available hooks.

