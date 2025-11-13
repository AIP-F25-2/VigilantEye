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

## Authentication

### Overview

VigilentEye uses JWT-based authentication with access and refresh tokens. The frontend automatically handles token storage, injection, refresh, and expiration.

### Features

- **JWT Authentication**: Access tokens (1 hour) and refresh tokens (30 days)
- **Auto Token Refresh**: Automatic token refresh on 401 errors via Axios interceptor
- **Auto-Logout**: Proactive logout before token expiration + reactive logout on 401
- **Protected Routes**: Route-level and component-level authentication guards
- **Role-Based Access**: Admin and staff role support with conditional UI rendering
- **Form Validation**: Email format, password strength validation with Zod
- **Session Persistence**: User session persists across browser sessions (localStorage)
- **Real-Time Notifications**: Toast notifications for auth events (login, logout, errors)

### Auth State Management

**Zustand Store (`authStore.ts`):**

- Global auth state: user, isAuthenticated, isLoading
- Actions: login, logout, setUser, setLoading
- Persisted to localStorage (survives page refresh)
- Single source of truth for auth state

**Usage:**

```typescript
import { useAuth } from '@/hooks/useAuth'

const { user, isAuthenticated, isAdmin, logout } = useAuth()

if (isAdmin) {
  // Show admin features
}
```

### Authentication Flow

**Login Flow:**

1. User enters credentials in Login page
2. Form validation (Zod schema)
3. Call `authService.login(credentials)`
4. Backend returns `{ access_token, refresh_token, user }`
5. Store tokens in localStorage
6. Update Zustand store with user
7. Redirect to home (or return URL)
8. Axios interceptor automatically adds token to all requests

**Token Refresh Flow (Automatic):**

1. API request returns 401 Unauthorized
2. Axios interceptor catches 401 (see `api.ts` lines 36-63)
3. Call `/auth/refresh` with refresh_token
4. Backend returns new access_token
5. Update localStorage with new token
6. Retry original request with new token
7. If refresh fails, clear tokens and redirect to login

**Logout Flow:**

1. User clicks logout button
2. Call `authService.logout()`
3. Backend revokes session
4. Clear tokens from localStorage
5. Clear Zustand store
6. Redirect to login page

**Session Restoration (Page Refresh):**

1. App loads, check if tokens exist in localStorage
2. If tokens exist, call `authService.getCurrentUser()`
3. If successful, restore user in Zustand store
4. If fails (401), clear tokens and show login
5. User session seamlessly restored

### Protected Routes

**Route-Level Protection:**

```typescript
<Route path="/videos" element={
  <ProtectedRoute>
    <VideosPage />
  </ProtectedRoute>
} />

<Route path="/admin" element={
  <ProtectedRoute requiredRole="admin">
    <AdminPage />
  </ProtectedRoute>
} />
```

**Component-Level Protection:**

```typescript
import { RoleGuard } from '@/components/RoleGuard'

<RoleGuard role="admin">
  <button onClick={deleteVideo}>Delete Video</button>
</RoleGuard>
```

**Hook-Based Protection:**

```typescript
import { useRequireAuth } from '@/hooks/useRequireAuth'

function ProtectedPage() {
  const { user, isLoading } = useRequireAuth('admin')
  
  if (isLoading) return <LoadingSpinner />
  
  return <div>Admin content</div>
}
```

### Password Validation

**Requirements:**

- Minimum 8 characters
- At least 1 uppercase letter (A-Z)
- At least 1 lowercase letter (a-z)
- At least 1 digit (0-9)
- (Optional) At least 1 special character

**Strength Indicator:**

- **Weak**: < 8 characters or missing requirements
- **Medium**: 8+ characters with uppercase, lowercase, digit
- **Strong**: 12+ characters with all requirements

**Visual Feedback:**

- Progress bar with color coding (red/yellow/green)
- Requirements checklist with checkmarks
- Real-time validation as user types

### Token Management

**Token Storage:**

- Access token: `localStorage.getItem('access_token')`
- Refresh token: `localStorage.getItem('refresh_token')`
- User object: Zustand store (persisted to localStorage)

**Token Injection:**

- Automatic via Axios request interceptor (see `api.ts` lines 13-25)
- All API requests include `Authorization: Bearer {token}` header
- No manual token handling needed in components

**Token Refresh:**

- Automatic via Axios response interceptor (see `api.ts` lines 27-67)
- Triggered on 401 Unauthorized responses
- Retries original request with new token
- Redirects to login if refresh fails

**Token Expiration:**

- Access token: 1 hour (backend configured)
- Refresh token: 30 days (backend configured)
- Auto-logout timer: Logout 1 minute before expiration
- Warning toast: Show 5 minutes before expiration

### Error Handling

**Form Validation Errors:**

- Displayed below each input field
- Red text with error icon
- Real-time validation on blur

**API Errors:**

- Displayed as toast notifications
- Error messages from backend (username exists, invalid credentials)
- Special handling for rate limiting (429)

**Network Errors:**

- Toast notification: "Network error, please try again"
- Retry button (optional)

**Session Errors:**

- Auto-redirect to login on 401
- Toast notification: "Session expired, please login again"

### Security

**Token Storage:**

- localStorage is acceptable for JWTs (not sensitive cookies)
- Tokens are httpOnly=false (needed for JavaScript access)
- HTTPS required in production (tokens in headers)

**XSS Protection:**

- React escapes by default
- No dangerouslySetInnerHTML used
- Tokens not exposed in URLs

**CSRF Protection:**

- Not needed for JWT (stateless authentication)
- Backend uses JWT, not cookies

**Auto-Logout:**

- Prevents stale sessions
- Clears tokens on expiration
- Proactive + reactive logout

### Troubleshooting

**Cannot login:**

- Check credentials are correct
- Verify backend is running: `http://localhost:5000/health`
- Check network tab for API errors
- Verify CORS is configured (backend allows frontend origin)

**Session not persisting:**

- Check localStorage for tokens: `localStorage.getItem('access_token')`
- Verify Zustand persist is working: check localStorage for 'vigilanteye-auth'
- Check browser console for errors

**Auto-logout not working:**

- Check token expiration time: decode token in browser console
- Verify auto-logout timer is set (check useEffect in App.tsx)
- Check Axios interceptor is handling 401 (see api.ts)

**Protected routes not working:**

- Check ProtectedRoute component is wrapping routes
- Verify isAuthenticated is true in Zustand store
- Check for redirect loops (login → home → login)

**Token refresh fails:**

- Check refresh_token exists in localStorage
- Verify backend /auth/refresh endpoint is working
- Check token hasn't expired (refresh token valid for 30 days)
- Review Axios interceptor logic (api.ts lines 36-63)

## Home Page - Video Ingestion

### Overview

The Home page is the central hub for video ingestion, providing two methods: uploading pre-recorded videos and starting live camera streams for real-time surveillance.

### Features

**Video Upload:**

- Drag-and-drop upload zone with visual feedback
- Click to browse alternative (dual input methods)
- File validation (format: MP4/AVI/MOV/MKV, size: max 500 MB)
- Real-time upload progress bar (0-100%)
- Automatic metadata extraction on backend (duration, fps, resolution)
- Toast notifications for success/error

**Live Camera Streaming:**

- RTSP stream URL input for IP cameras
- Optional camera name for identification
- Start/stop stream controls
- Active streams list showing all running streams
- Maximum 4 concurrent streams (configurable)
- Stream status indicators

**Real-Time Analysis Notifications:**

- WebSocket connection to backend `/analysis` namespace
- Automatic notifications when video analysis completes
- Suspicious activity alerts with ticket ID
- Clean analysis confirmations
- Connection status indicator

### Components

**HomePage (`pages/Home.tsx`):**

- Main page component with two-column layout (upload + streaming)
- Manages upload state, stream state, WebSocket connection
- Handles file selection, upload progress, stream start/stop
- Displays real-time notifications via toast

**UploadZone (`components/UploadZone.tsx`):**

- Reusable drag-and-drop upload component
- Built-in file validation with error display
- Progress bar integration
- Visual feedback for drag states (default, dragging, uploading, error)
- Accessible with keyboard navigation

**useWebSocket Hook (`hooks/useWebSocket.ts`):**

- Custom hook for Socket.IO connection management
- Automatic connect/disconnect lifecycle
- Connection status tracking
- Reconnection handling (automatic retries)
- Reusable across components

### Video Service

**videoService.ts:**

- `uploadVideo(file, cameraId?, onProgress?)` - Upload with progress tracking
- `startStream(cameraId, streamUrl, name?)` - Start RTSP stream
- `stopStream(cameraId)` - Stop active stream
- `getActiveStreams()` - List currently streaming cameras
- `analyzeVideo(videoId)` - Trigger manual analysis (used in VideoDirectory)
- `getAnalysisStatus(videoId)` - Check analysis progress

### Usage

**Upload Video:**

1. Navigate to Home page (requires authentication)
2. Drag video file to upload zone or click to browse
3. File validated (format, size)
4. Upload starts automatically with progress bar
5. Success notification shown when complete
6. Video appears in Video Directory (Phase 14)

**Start Live Stream:**

1. Enter RTSP stream URL (e.g., `rtsp://192.168.1.100:554/stream`)
2. Optionally enter camera name (e.g., "Front Entrance")
3. Click "Start Camera" button
4. Stream starts on backend (frames buffered for analysis)
5. Stream appears in active streams list
6. Click "Stop Camera" to end stream

**Real-Time Notifications:**

- WebSocket automatically connects on page load
- When video analysis completes:
  - Suspicious: Red toast with "🚨 Suspicious activity detected! Ticket #TKT-001"
  - Clean: Green toast with "✅ No suspicious activity detected"
- Notifications auto-dismiss after 4-6 seconds
- Click notification to view ticket details (future enhancement)

### Configuration

**File Upload Limits:**

- Maximum size: 500 MB (configurable via `MAX_VIDEO_SIZE_MB`)
- Supported formats: MP4, AVI, MOV, MKV
- Validation: Client-side (immediate feedback) + server-side (security)

**Streaming Limits:**

- Maximum concurrent streams: 4 (configurable via `MAX_CONCURRENT_STREAMS`)
- Supported protocols: RTSP, HTTP (MJPEG), RTMP
- Stream URL format: `rtsp://ip:port/path` or `http://ip:port/stream`

**WebSocket:**

- Namespace: `/analysis`
- Events: `analysis_complete`, `analysis_started`, `analysis_error`
- Auto-reconnect: Enabled (5 attempts, 1s delay)
- Connection indicator: Green/red dot in page header

### Troubleshooting

**Upload fails:**

- Check file format is supported (MP4, AVI, MOV, MKV)
- Verify file size is under 500 MB
- Check storage quota not exceeded (backend enforces per-user quota)
- Review network tab for API errors (413 for too large, 409 for quota)

**Drag-and-drop not working:**

- Ensure browser supports HTML5 drag-and-drop (all modern browsers)
- Check file is being dropped in the upload zone (not outside)
- Try click to browse as alternative
- Check browser console for JavaScript errors

**Stream won't start:**

- Verify RTSP URL is correct and accessible from backend server
- Check camera supports RTSP protocol
- Verify maximum streams not reached (4 concurrent)
- Check network connectivity between backend and camera
- Review backend logs for stream connection errors

**WebSocket not connecting:**

- Check backend is running: `http://localhost:5000/health`
- Verify Flask-SocketIO is initialized (backend Phase 12)
- Check CORS allows WebSocket connections
- Review browser console for Socket.IO errors
- Check firewall settings (WebSocket uses different protocol)

**Notifications not appearing:**

- Verify WebSocket is connected (check connection indicator)
- Check video analysis is actually running (trigger via analyze button)
- Review browser console for event listener errors
- Verify toast notifications are working (test with manual toast.success())

**Upload progress not showing:**

- Check Axios onUploadProgress callback is firing (add console.log)
- Verify progress state is updating (React DevTools)
- Check progress bar CSS is correct (width style)
- Ensure upload is actually in progress (not instant for small files)

**Mobile layout broken:**

- Check Tailwind responsive classes (md:grid-cols-2, sm:px-6)
- Test on actual mobile device or browser DevTools mobile emulation
- Verify viewport meta tag in index.html
- Check for horizontal scroll (overflow issues)

### Future Enhancements

**Local Camera Access (WebRTC):**

- Use `navigator.mediaDevices.getUserMedia()` for local webcam
- Display live preview in `<video>` element
- Capture frames and send to backend via WebSocket
- Requires additional backend endpoint for frame ingestion

**Chunked Upload:**

- Split large files into chunks (e.g., 10 MB each)
- Upload chunks sequentially or in parallel
- Resume upload on failure (store chunk progress)
- Better for very large files (>1 GB)

**Upload Queue:**

- Allow multiple file selection
- Queue uploads and process sequentially
- Show queue status with progress for each file
- Cancel individual uploads

**Stream Preview:**

- Display live stream preview in browser (requires HLS/DASH transcoding)
- Show stream health metrics (bitrate, dropped frames)
- Thumbnail preview for RTSP streams

## Video Directory Page - Video Management

### Overview

The Video Directory page provides a comprehensive interface for managing uploaded and streamed videos with filtering, pagination, and video management actions.

### Features

**Video Display:**

- Table view (default) - Detailed metadata in columns, better for desktop
- Grid view (toggle) - Visual cards with thumbnails, better for mobile
- Thumbnails with lazy loading
- Status badges (uploading, ready, analyzing, analyzed, error)
- Analysis result badges (pending, clean, suspicious)
- TTL countdown showing time until auto-deletion (2 hours)

**Actions:**

- **Play**: Open video in modal player with HTML5 controls
- **Analyze**: Trigger AI analysis manually (shown when status='ready')
- **Delete**: Admin-only action with confirmation dialog and optional reason
- **Download**: Download video file to local device (optional)

**Filters:**

- Search by filename (debounced 500ms)
- Filter by status (uploading, ready, analyzing, analyzed, error)
- Filter by camera source (dropdown of available cameras)
- Filter by analysis result (pending, clean, suspicious)
- Date range filter (from/to dates)
- Reset all filters button

**Pagination:**

- 20 videos per page (desktop), 10-15 on mobile
- Page controls: Previous | 1 2 3 ... 10 | Next
- Shows "Showing 1-20 of 142 videos"
- Smooth transitions with React Query keepPreviousData

**Real-Time Updates:**

- WebSocket connection for analysis completion events
- Automatic status updates when analysis completes
- Toast notifications for suspicious/clean results
- No manual refresh needed

### Components

**VideoDirectoryPage (`pages/VideoDirectory.tsx`):**

- Main page component with React Query data fetching
- Manages view mode (table/grid), pagination, filters, modals
- Handles actions (play, delete, analyze, download)
- WebSocket integration for real-time updates

**VideoStatusBadge (`components/VideoStatusBadge.tsx`):**

- Displays video processing status with color-coded badges
- Icons for each status (uploading, ready, analyzing, error)
- Consistent styling across views

**AnalysisResultBadge (`components/AnalysisResultBadge.tsx`):**

- Displays analysis outcome (pending, clean, suspicious)
- Color-coded: gray (pending), green (clean), red (suspicious)
- Used to quickly identify threats

**TTLCountdown (`components/TTLCountdown.tsx`):**

- Real-time countdown to video expiration
- Updates every second
- Color-coded warnings (green >30min, yellow 10-30min, red <10min)
- Shows "Expired" when TTL passed

**VideoPlayerModal (`components/VideoPlayerModal.tsx`):**

- Modal with HTML5 video player
- Fetches video blob via API
- Native controls (play, pause, seek, volume, fullscreen)
- Shows video metadata (filename, duration, resolution)
- Keyboard accessible (Escape to close)

**DeleteConfirmDialog (`components/DeleteConfirmDialog.tsx`):**

- Confirmation dialog for destructive delete action
- Shows video details and warning message
- Optional reason input for admin audit trail
- Prevents accidental deletions

**FilterBar (`components/FilterBar.tsx`):**

- Centralized filter controls
- Search input with debouncing
- Dropdowns for status, camera, analysis result
- Date range inputs
- Reset filters button

### React Query Integration

**Data Fetching:**

```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['videos', page, filters],
  queryFn: () => videoService.getVideos(page, 20, filters),
  keepPreviousData: true,
  staleTime: 5 * 60 * 1000, // 5 minutes
})
```

**Mutations:**

```typescript
const deleteMutation = useMutation({
  mutationFn: videoService.deleteVideo,
  onSuccess: () => {
    queryClient.invalidateQueries(['videos'])
    toast.success('Video deleted successfully')
  },
})

const analyzeMutation = useMutation({
  mutationFn: videoService.analyzeVideo,
  onSuccess: () => {
    toast.success('Analysis started')
  },
})
```

**Benefits:**

- Automatic caching (5-minute stale time)
- Automatic refetching on window focus
- Loading and error states handled automatically
- Optimistic updates for better UX
- Cache invalidation on mutations

### Usage

**View Videos:**

1. Navigate to Video Directory (/videos)
2. Videos displayed in table view (default)
3. Toggle to grid view for visual browsing
4. Use filters to narrow down results
5. Click page numbers to navigate pages

**Play Video:**

1. Click Play button or video thumbnail
2. Modal opens with video player
3. Use native controls to play, pause, seek
4. Click outside modal or press Escape to close

**Analyze Video:**

1. Find video with status='ready' and no analysis result
2. Click Analyze button (BarChart3 icon)
3. Video status changes to 'analyzing'
4. Wait for analysis to complete (~30-40 seconds)
5. WebSocket notification shows result (suspicious/clean)
6. Analysis badge updates automatically

**Delete Video (Admin Only):**

1. Admin users see Delete button (Trash2 icon)
2. Click Delete button
3. Confirmation dialog appears with warning
4. Optionally enter deletion reason
5. Click "Delete Video" to confirm
6. Video removed from list, success toast shown

**Filter Videos:**

1. Use search box to find by filename
2. Select status from dropdown (e.g., "Analyzed")
3. Select analysis result (e.g., "Suspicious")
4. Set date range (from/to)
5. Filters apply automatically (debounced)
6. Click "Reset Filters" to clear all

### Configuration

**Pagination:**

- Videos per page: 20 (desktop), 15 (tablet), 10 (mobile)
- Configurable via component state

**TTL Display:**

- Videos expire after 2 hours (backend configured)
- Countdown shows time remaining
- Color warnings at 30 min and 10 min

**WebSocket:**

- Namespace: `/analysis`
- Events: `analysis_complete`
- Auto-reconnect enabled

### Troubleshooting

**Videos not loading:**

- Check authentication (must be logged in)
- Verify backend is running: `http://localhost:5000/health`
- Check network tab for API errors
- Try manual refresh button

**Thumbnails not showing:**

- Check backend thumbnail generation (Phase 4)
- Verify thumbnail endpoint: `GET /api/videos/{id}/thumbnail`
- Check image src in browser DevTools
- Fallback to placeholder image if thumbnail missing

**Delete button not visible:**

- Only admins can delete videos
- Check user role: `user.role === 'admin'`
- Staff users don't see delete button (RoleGuard hides it)

**Analyze button disabled:**

- Only videos with status='ready' can be analyzed
- Already analyzed videos show result badge instead
- Videos being analyzed show 'analyzing' status

**Real-time updates not working:**

- Check WebSocket connection (connection indicator)
- Verify backend WebSocket is running (Flask-SocketIO)
- Check browser console for Socket.IO errors
- Try manual refresh to see updated status

**Pagination not working:**

- Check React Query is fetching with correct page parameter
- Verify backend returns pagination metadata
- Check page state is updating (React DevTools)
- Try clicking page numbers directly

**Filters not applying:**

- Check filter state is updating (React DevTools)
- Verify React Query refetches when filters change (query key includes filters)
- Check backend supports filter parameters
- Try resetting filters and applying again

**TTL countdown not updating:**

- Check setInterval is running (add console.log)
- Verify expires_at timestamp is valid
- Check component is mounted (not unmounted prematurely)
- Ensure interval is cleared on unmount

## Tickets Page - Incident Management

### Overview

The Tickets page provides a comprehensive interface for managing security incidents detected by the AI system, with filtering, real-time updates, and detailed incident investigation capabilities.

### Features

**Ticket Display:**

- Table view with sortable columns (ID, Title, Status, Priority, Threat Level, Created, Assigned To, Actions)
- Status badges (OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, CLOSED) with color coding
- Priority badges (LOW, MEDIUM, HIGH, CRITICAL) with severity colors
- Threat level badges (low, medium, high, critical) from AI assessment
- TTL countdown showing time until auto-close (2 hours)
- Real-time status updates via WebSocket

**Actions:**

- **View Details**: Open comprehensive modal with evidence, AI analysis, persons, timeline
- **Acknowledge**: Acknowledge ticket and assign to current user (shown when status='OPEN')
- **Close**: Close ticket with optional reason (shown when status != 'CLOSED')
- **Escalate**: Send escalation alert to secondary Telegram channel (shown when not escalated)
- **Download Report**: Download PDF report with complete incident details

**Filters:**

- Search by ticket title (debounced 500ms)
- Filter by status (OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, CLOSED)
- Filter by priority (LOW, MEDIUM, HIGH, CRITICAL)
- Filter by threat level (low, medium, high, critical)
- Filter by assigned user (All, Unassigned, Me, specific users)
- Date range filter (from/to dates)
- Reset all filters button

**Pagination:**

- 20 tickets per page (desktop), 10-15 on mobile
- Page controls: Previous | 1 2 3 ... 10 | Next
- Shows "Showing 1-20 of 42 tickets"
- Smooth transitions with React Query keepPreviousData

**Real-Time Updates:**

- WebSocket connection for ticket status changes
- Automatic updates when tickets acknowledged, closed, escalated
- Toast notifications for ticket events
- No manual refresh needed

**Ticket Detail Modal:**

- **Overview Tab**: Ticket details, status, priority, threat level, timestamps, assigned user, SLA metrics
- **Evidence Tab**: Image gallery with lightbox, audio players, video clips
- **AI Analysis Tab**: LLM reasoning, confidence score, key factors, all 5 AI module outputs (scene, persons, objects, speech, audio)
- **Persons Tab**: Persons of interest with demographics, thumbnails, similar person matches from ChromaDB
- **Timeline Tab**: Chronological history of all ticket events with icons and relative times
- **Action Buttons**: Acknowledge, Close, Escalate, Download Report (footer)

### Components

**TicketsPage (`pages/Tickets.tsx`):**

- Main page component with React Query data fetching
- Manages pagination, filters, modals, actions
- WebSocket integration for real-time updates
- Table view with all ticket metadata

**TicketDetailModal (`components/TicketDetailModal.tsx`):**

- Comprehensive modal with 5 tabbed sections
- Fetches complete ticket details with all relationships
- Action buttons for ticket management
- Keyboard accessible (Escape to close, arrow keys for tabs)

**TicketStatusBadge (`components/TicketStatusBadge.tsx`):**

- Displays ticket status with color-coded badges
- Icons for each status (Circle, CheckCircle, Activity, Check, Lock)
- Consistent styling across views

**PriorityBadge (`components/PriorityBadge.tsx`):**

- Displays ticket priority with severity colors
- Icons for each priority (Info, AlertCircle, AlertTriangle, AlertOctagon)
- Color progression: gray → yellow → orange → red

**ThreatLevelBadge (`components/ThreatLevelBadge.tsx`):**

- Displays AI-assessed threat level
- Same color coding as priority (low=gray, high=red)
- Provides quick visual threat assessment

**EvidenceGallery (`components/EvidenceGallery.tsx`):**

- Grid of evidence images with lightbox for full-size view
- HTML5 audio players for audio evidence
- Lazy loading for performance
- Download buttons for each evidence file

**PersonCard (`components/PersonCard.tsx`):**

- Card displaying person demographics and thumbnail
- Shows age, gender, ethnicity, clothing, confidence
- Similarity score for matched persons
- Compact mode for similar persons grid

**TicketTimeline (`components/TicketTimeline.tsx`):**

- Vertical timeline with event dots and connecting lines
- Icons and colors for each event type
- Relative timestamps ("2 hours ago")
- Expandable event details

**CloseTicketDialog (`components/CloseTicketDialog.tsx`):**

- Confirmation dialog for closing tickets
- Optional reason textarea for audit trail
- Prevents accidental closures

### React Query Integration

**Data Fetching:**

```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['tickets', page, filters],
  queryFn: () => ticketService.getTickets(page, 20, filters),
  keepPreviousData: true,
  staleTime: 5 * 60 * 1000, // 5 minutes
})
```

**Mutations:**

```typescript
const acknowledgeMutation = useMutation({
  mutationFn: ticketService.acknowledgeTicket,
  onSuccess: () => {
    queryClient.invalidateQueries(['tickets'])
    toast.success('Ticket acknowledged successfully')
  },
})

const closeMutation = useMutation({
  mutationFn: ticketService.closeTicket,
  onSuccess: () => {
    queryClient.invalidateQueries(['tickets'])
    toast.success('Ticket closed successfully')
  },
})

const escalateMutation = useMutation({
  mutationFn: ticketService.escalateTicket,
  onSuccess: () => {
    toast.success('Escalation alert sent to Telegram')
  },
})
```

**Benefits:**

- Automatic caching (5-minute stale time)
- Optimistic updates for better UX
- Cache invalidation on mutations
- Loading and error states handled automatically

### Usage

**View Tickets:**

1. Navigate to Tickets page (/tickets)
2. Tickets displayed in table view
3. Use filters to narrow down results
4. Click page numbers to navigate pages

**View Ticket Details:**

1. Click View Details button or ticket row
2. Modal opens with 5 tabs (Overview, Evidence, AI Analysis, Persons, Timeline)
3. Navigate tabs to see different aspects of incident
4. Use action buttons to manage ticket
5. Close modal with X button or Escape key

**Acknowledge Ticket:**

1. Find ticket with status='OPEN'
2. Click Acknowledge button
3. Ticket status changes to 'ACKNOWLEDGED'
4. Ticket assigned to current user
5. Success toast shown
6. SLA breach indicated if >15 minutes

**Close Ticket:**

1. Click Close button on ticket
2. Confirmation dialog appears
3. Optionally enter closure reason
4. Click "Close Ticket" to confirm
5. Ticket status changes to 'CLOSED'
6. Success toast shown

**Escalate Ticket:**

1. Click Escalate button on ticket
2. Escalation alert sent to secondary Telegram channel
3. Ticket marked as escalated
4. Escalation count incremented
5. Success toast shown

**Download Report:**

1. Click Download Report button
2. PDF report generated on backend (cached for 1 hour)
3. Report downloaded to browser
4. Success toast shown
5. Report includes: incident overview, timeline, AI analysis, evidence, persons, recommendations

**Filter Tickets:**

1. Use search box to find by title
2. Select status from dropdown (e.g., "OPEN")
3. Select priority (e.g., "HIGH")
4. Select assigned user (e.g., "Me")
5. Set date range (from/to)
6. Filters apply automatically (debounced)
7. Click "Reset Filters" to clear all

### Configuration

**Pagination:**

- Tickets per page: 20 (desktop), 15 (tablet), 10 (mobile)
- Configurable via component state

**TTL Display:**

- Tickets auto-close after 2 hours (backend configured)
- Countdown shows time remaining
- Color warnings at 30 min and 10 min

**WebSocket:**

- Namespace: `/tickets` (new) or `/analysis` (reuse)
- Events: `ticket_status_changed`, `ticket_acknowledged`, `ticket_closed`, `ticket_escalated`
- Auto-reconnect enabled

### Troubleshooting

**Tickets not loading:**

- Check authentication (must be logged in)
- Verify backend is running
- Check network tab for API errors
- Try manual refresh button

**Cannot acknowledge ticket:**

- Only OPEN tickets can be acknowledged
- Check ticket status is 'OPEN'
- Verify user is authenticated
- Check backend logs for errors

**Cannot close ticket:**

- Tickets must not already be closed
- Check current status
- Verify user has permission (assigned user or admin)

**Evidence not loading:**

- Check evidence files exist in storage
- Verify evidence endpoint: `/api/storage/evidence/{id}/download`
- Check authorization (user must be assigned to ticket or admin)
- Review browser console for errors

**Real-time updates not working:**

- Check WebSocket connection (connection indicator)
- Verify backend WebSocket is running (Flask-SocketIO)
- Check browser console for Socket.IO errors
- Try manual refresh to see updated status

**Report download fails:**

- Check ticket has evidence and analysis data
- Verify report endpoint: `/api/tickets/{id}/report/download`
- Check authorization (assigned user or admin)
- Review backend logs for report generation errors

**Similar persons not showing:**

- Check ChromaDB is running and has embeddings
- Verify person detection ran during analysis
- Check time window (2 hours) - older persons may be expired
- Review backend logs for ChromaDB errors

## Analytics Dashboard - System Monitoring

### Overview

The Analytics Dashboard provides comprehensive system monitoring and security analytics with real-time metrics, performance tracking, and incident trends visualization.

### Features

**Security Analytics:**

- **Tickets Over Time**: Line chart showing incident trends (hourly/daily)
- **Threat Distribution**: Pie chart showing breakdown by threat level (low, medium, high, critical)
- **Response Time Metrics**: Bar chart showing p50, p95, p99 response times
- **Top Cameras**: Bar chart ranking cameras by incident count

**System Health Monitoring:**

- **API Latency**: p50, p95, p99 percentiles in milliseconds
- **AI Model Performance**: Average inference times for each AI model
- **Database Status**: Connection status and response times (MySQL, Redis, ChromaDB)
- **Storage Usage**: Disk usage percentage and breakdown by type
- **Celery Workers**: Active worker count and task queue status

**Real-Time Updates:**

- Auto-refresh every 30 seconds for health/metrics
- Auto-refresh every 60 seconds for analytics charts
- Manual refresh button for immediate updates
- Pause/resume auto-refresh toggle
- Last updated timestamp display

**Historical Data:**

- Date range selector with presets (Last 24h, 7d, 30d, Custom)
- Custom date range picker for specific periods
- Charts update automatically when date range changes

### Components

**AnalyticsPage (`pages/Analytics.tsx`):**

- Main dashboard with React Query auto-refresh
- 4 chart sections + system health section
- Date range filtering for historical data
- Responsive grid layout (2x2 charts, 4-column health cards)

**Chart Components (Recharts):**

- **TicketsOverTimeChart**: Line chart for trend visualization
- **ThreatDistributionChart**: Pie chart for categorical data
- **ResponseTimeChart**: Bar chart for latency percentiles
- **TopCamerasChart**: Bar chart for camera ranking

**HealthMetricsCard (`components/HealthMetricsCard.tsx`):**

- Reusable card for displaying single metric
- Status indicators (healthy, warning, error) with color coding
- Optional trend indicators (up/down arrows)
- Icon support for visual identification

**DateRangeSelector (`components/DateRangeSelector.tsx`):**

- Preset buttons for common ranges (24h, 7d, 30d)
- Custom date picker for specific periods
- Validation (from <= to)
- Clear button to reset filter

### React Query Integration

**Auto-Refresh Queries:**

```typescript
// Health data - refresh every 30 seconds
const { data: healthData } = useQuery({
  queryKey: ['health'],
  queryFn: healthService.getHealth,
  refetchInterval: 30000,
})

// Metrics data - refresh every 30 seconds
const { data: metricsData } = useQuery({
  queryKey: ['metrics'],
  queryFn: healthService.getMetrics,
  refetchInterval: 30000,
})

// Analytics data - refresh every 60 seconds, filtered by date range
const { data: analyticsData } = useQuery({
  queryKey: ['analytics', dateRange],
  queryFn: () => analyticsService.getAnalytics(dateRange),
  refetchInterval: 60000,
})
```

**Benefits:**

- Automatic polling for real-time monitoring
- Pauses when tab inactive (saves resources)
- Manual refresh available
- Cached data for instant display

### Usage

**View System Health:**

1. Navigate to Analytics page (/analytics)
2. System health cards display current status
3. Green indicators = healthy, Yellow = warning, Red = error
4. Auto-refreshes every 30 seconds

**View Security Analytics:**

1. Charts display incident trends and distributions
2. Default: Last 24 hours of data
3. Use date range selector to view historical data
4. Charts update automatically when range changes

**Monitor Performance:**

1. Check API latency metrics (p50, p95, p99)
2. Review AI model inference times
3. Monitor database connection pool usage
4. Track storage usage percentage

**Identify Problem Areas:**

1. Check Top Cameras chart for high-incident cameras
2. Review Threat Distribution for critical threat trends
3. Monitor Response Time chart for performance degradation
4. Check Tickets Over Time for incident spikes

**Pause Auto-Refresh:**

1. Click "Pause Auto-Refresh" button
2. Data stops updating automatically
3. Use manual refresh button to update on-demand
4. Click "Resume Auto-Refresh" to re-enable

### Configuration

**Auto-Refresh Intervals:**

- Health/Metrics: 30 seconds (real-time monitoring)
- Analytics Charts: 60 seconds (less critical)
- Configurable via toggle button (pause/resume)

**Date Range Presets:**

- Last 24 hours (default)
- Last 7 days
- Last 30 days
- Custom range (date picker)

**Chart Heights:**

- Desktop: 300px per chart
- Mobile: Auto height (responsive)

**Health Thresholds:**

- API Latency: <500ms = healthy, 500-1000ms = warning, >1000ms = error
- Storage Usage: <80% = healthy, 80-90% = warning, >90% = error
- Database: connected = healthy, disconnected = error
- Celery Workers: >0 = healthy, 0 = error

### Troubleshooting

**Charts not loading:**

- Check backend health endpoints are implemented (Phase 16)
- Verify React Query is fetching data (check network tab)
- Check for JavaScript errors in console
- Try manual refresh button

**Auto-refresh not working:**

- Check auto-refresh is enabled (not paused)
- Verify refetchInterval is set in React Query options
- Check tab is active (React Query pauses when inactive)
- Review browser console for errors

**Health metrics showing error:**

- Check backend services are running (MySQL, Redis, ChromaDB, Celery)
- Verify backend health endpoint returns correct data
- Check network connectivity
- Review backend logs for service errors

**Charts showing "No data":**

- Check date range is valid (from <= to)
- Verify tickets exist for selected period
- Try "All Time" preset to see all data
- Check backend analytics endpoint returns data

**Performance is slow:**

- Reduce auto-refresh frequency (increase refetchInterval)
- Limit chart data points (backend should aggregate)
- Disable auto-refresh when not actively monitoring
- Check backend performance (slow queries, AI models)

**Recharts errors:**

- Verify Recharts is installed: `npm list recharts`
- Check data format matches Recharts requirements (array of objects with name/value)
- Review browser console for Recharts warnings
- Ensure ResponsiveContainer wraps all charts

### Future Enhancements

**Advanced Analytics:**

- Heatmap of incidents by time of day and day of week
- Correlation analysis (weather vs incidents, time vs threat level)
- Predictive analytics (forecast incident trends)
- Anomaly detection (unusual patterns)

**Custom Dashboards:**

- User-configurable dashboard layouts
- Drag-and-drop chart arrangement
- Save custom dashboard preferences
- Multiple dashboard views (security, performance, operations)

**Export Capabilities:**

- Export charts as images (PNG, SVG)
- Export data as CSV for external analysis
- Scheduled reports (daily/weekly email summaries)

**Alerting:**

- Threshold-based alerts (e.g., alert if p95 > 1000ms)
- Email/Telegram notifications for health issues
- Alert history and acknowledgment

## Pages

1. **Login/SignUp** - Authentication
2. **Home** - Video upload and live stream
3. **Video Directory** - Manage stored videos
4. **Tickets** - View and manage security incidents
5. **Analytics** - System health and metrics dashboard

