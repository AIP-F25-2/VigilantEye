import { Routes, Route, Navigate } from 'react-router-dom'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/signup" element={<div>SignUp Page</div>} />
        <Route path="/" element={<div>Home Page</div>} />
        <Route path="/videos" element={<div>Video Directory</div>} />
        <Route path="/tickets" element={<div>Tickets Page</div>} />
        <Route path="/analytics" element={<div>Analytics Page</div>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App

