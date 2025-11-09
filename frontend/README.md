# VigilantEye Frontend

React + TypeScript + Vite frontend for the AI surveillance system.

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Development Server

```bash
npm run dev
```

Application will be available at `http://localhost:5173`

## Project Structure

```
frontend/
├── src/
│   ├── pages/        # Page components (5 pages)
│   ├── components/   # Reusable UI components
│   ├── services/     # API client services
│   ├── hooks/        # Custom React hooks
│   ├── utils/        # Utility functions
│   ├── types/        # TypeScript types
│   ├── store/        # Zustand state management
│   └── __tests__/    # Test files
├── public/           # Static assets
└── dist/             # Production build
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint errors
- `npm run format` - Format code with Prettier
- `npm run test` - Run tests
- `npm run test:coverage` - Run tests with coverage

## Technology Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **TanStack Query** - Data fetching
- **Zustand** - State management
- **Axios** - HTTP client
- **Vitest** - Testing

## Pages

1. **Login/SignUp** - Authentication
2. **Home** - Video upload and live stream
3. **Video Directory** - Manage stored videos
4. **Tickets** - View and manage security incidents
5. **Analytics** - System health and metrics dashboard

