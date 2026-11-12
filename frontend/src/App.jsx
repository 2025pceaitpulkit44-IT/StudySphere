import { Navigate, Route, Routes } from 'react-router-dom'
import RequireAuth from './components/RequireAuth'
import AppLayout from './layouts/AppLayout'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import ComingNext from './pages/ComingNext'
import Profile from './pages/Profile'
import Undertaking from './pages/admin/Undertaking'
import Upload from './pages/admin/Upload'
import KnowledgeBase from './pages/admin/KnowledgeBase'
import AdminHome from './pages/admin/AdminHome'
import StudentDoubts from './pages/admin/StudentDoubts'
import Analytics from './pages/admin/Analytics'
import AskAI from './pages/student/AskAI'
import Dashboard from './pages/student/Dashboard'
import Doubts from './pages/student/Doubts'
import Subjects from './pages/student/Subjects'
import SubjectDetail from './pages/student/SubjectDetail'
import Notes from './pages/student/Notes'
import Quiz from './pages/student/Quiz'
import Progress from './pages/student/Progress'
import Search from './pages/student/Search'

const soon = (feature, batch) => <ComingNext feature={feature} batch={batch} />

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Student area */}
      <Route element={<RequireAuth role="student" />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ask" element={<AskAI />} />
          <Route path="/doubts" element={<Doubts />} />
          <Route path="/subjects" element={<Subjects />} />
          <Route path="/subjects/:id" element={<SubjectDetail />} />
          <Route path="/search" element={<Search />} />
          <Route path="/notes" element={<Notes />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/groups" element={soon('Study Groups (outside the core spec)', 'a later batch')} />
        </Route>
      </Route>

      {/* Admin / faculty area */}
      <Route element={<RequireAuth role="admin" />}>
        <Route element={<AppLayout />}>
          <Route path="/admin" element={<AdminHome />} />
          <Route path="/admin/undertaking" element={<Undertaking />} />
          <Route path="/admin/upload" element={<Upload />} />
          <Route path="/admin/kb" element={<KnowledgeBase />} />
          <Route path="/admin/doubts" element={<StudentDoubts />} />
          <Route path="/admin/analytics" element={<Analytics />} />
        </Route>
      </Route>

      {/* Profile is shared by both roles */}
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/profile" element={<Profile />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
