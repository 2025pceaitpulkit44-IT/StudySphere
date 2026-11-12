import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import {
  BarChart3, BookOpen, ClipboardCheck, FileText, Home, Library, LogOut, Menu,
  MessageCircleQuestion, Search, ShieldCheck, Sparkles, Upload, Users,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Logo, Pill } from '../components/ui'

const STUDENT_NAV = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/ask', label: 'Ask AI', icon: Sparkles },
  { to: '/doubts', label: 'My Doubts', icon: MessageCircleQuestion },
  { to: '/subjects', label: 'Subjects', icon: BookOpen },
  { to: '/notes', label: 'Notes', icon: FileText },
  { to: '/quiz', label: 'Quizzes', icon: ClipboardCheck },
  { to: '/progress', label: 'Progress', icon: BarChart3 },
  { to: '/groups', label: 'Study Groups', icon: Users, demo: true },
]

const ADMIN_NAV = [
  { to: '/admin', label: 'Dashboard', icon: Home, end: true },
  { to: '/admin/undertaking', label: 'Copyright Undertaking', icon: ShieldCheck },
  { to: '/admin/upload', label: 'Upload Material', icon: Upload },
  { to: '/admin/kb', label: 'Knowledge Base', icon: Library },
  { to: '/admin/doubts', label: 'Student Doubts', icon: MessageCircleQuestion },
  { to: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
]

const TITLES = {
  '/': ['Home', 'Your learning at a glance'],
  '/ask': ['Ask StudySphere AI', 'Answers from your college material'],
  '/doubts': ['My Doubts', 'Everything you have asked'],
  '/subjects': ['Subjects', 'Browse by subject and unit'],
  '/notes': ['Notes', 'Study material from your faculty'],
  '/quiz': ['Quizzes', 'Practice from your college material'],
  '/progress': ['Progress', 'Your practice and weak topics'],
  '/groups': ['Study Groups', 'Demo preview'],
  '/profile': ['Profile', 'Your account'],
  '/search': ['Search', 'Across your college material'],
  '/admin': ['Dashboard', 'Knowledge base overview'],
  '/admin/undertaking': ['Copyright & Study-Purpose Undertaking', 'Required before uploading material'],
  '/admin/upload': ['Upload Academic Material', 'Add to the knowledge base'],
  '/admin/kb': ['Knowledge Base', 'Manage uploaded documents'],
  '/admin/doubts': ['Student Doubts', 'Anonymised question analytics'],
  '/admin/analytics': ['Analytics', 'Usage and knowledge base growth'],
}

const initials = (name = '') =>
  name.replace(/\(demo\)/i, '').trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase()).join('') || '?'

export default function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [params] = useSearchParams()
  const [query, setQuery] = useState(params.get('q') || '')

  const isAdmin = user.role === 'admin'
  const items = isAdmin ? ADMIN_NAV : STUDENT_NAV
  const dynamic = pathname.startsWith('/subjects/') ? ['Subject', 'Units and study material'] : null
  const [title, subtitle] = TITLES[pathname] || dynamic || ['StudySphere', '']
  const runSearch = (e) => {
    e.preventDefault()
    if (query.trim().length >= 2) navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex bg-bg">
      {open && <div className="fixed inset-0 bg-ink/30 z-30 lg:hidden" onClick={() => setOpen(false)} />}

      <aside className={`fixed lg:sticky top-0 h-screen w-[228px] bg-white border-r border-line flex flex-col z-40 transition-transform duration-200 ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <div className="px-5 h-16 flex items-center border-b border-line shrink-0"><Logo size="sm" /></div>

        <nav className="flex-1 overflow-y-auto scrollbar-none py-4 px-3 space-y-0.5" aria-label="Main">
          {items.map(({ to, label, icon: Icon, end, demo }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
              className={({ isActive }) => `w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13.5px] font-medium transition-colors ${isActive ? 'bg-primary/8 text-primary' : 'text-ink/75 hover:bg-bg'}`}>
              {({ isActive }) => (
                <>
                  <Icon className={`w-[17px] h-[17px] ${isActive ? 'text-primary' : 'text-muted'}`} strokeWidth={1.7} />
                  <span className="flex-1">{label}</span>
                  {demo && <Pill tone="gold" className="!text-[10px] !px-1.5">Demo</Pill>}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-line space-y-0.5 shrink-0">
          <NavLink to="/profile" onClick={() => setOpen(false)}
            className={({ isActive }) => `w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13.5px] font-medium ${isActive ? 'bg-primary/8 text-primary' : 'text-ink/75 hover:bg-bg'}`}>
            <div className="w-6 h-6 rounded-full bg-gold/25 text-gold-dark flex items-center justify-center text-[10px] font-mono font-semibold">{initials(user.name)}</div>
            Profile
          </NavLink>
          <button onClick={signOut} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-[13.5px] font-medium text-ink/75 hover:bg-bg">
            <LogOut className="w-[17px] h-[17px] text-muted" strokeWidth={1.7} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-16 border-b border-line bg-white/80 backdrop-blur flex items-center justify-between px-5 lg:px-8 sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button onClick={() => setOpen(true)} aria-label="Open menu" className="lg:hidden p-1.5 -ml-1.5 rounded-md hover:bg-bg">
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h1 className="font-display font-semibold text-[16px] leading-none">{title}</h1>
              {subtitle && <p className="text-[12.5px] text-muted mt-0.5">{subtitle}</p>}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!isAdmin && (
              <form onSubmit={runSearch} role="search" className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md border border-line bg-bg w-64">
                <Search className="w-4 h-4 text-muted" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search the knowledge base"
                  placeholder="Search notes, topics…" className="bg-transparent text-sm w-full outline-none" />
              </form>
            )}
            <Pill tone={isAdmin ? 'gold' : 'green'}>{isAdmin ? 'Faculty' : 'Student'}</Pill>
            <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[12px] font-mono font-semibold" title={user.name}>
              {initials(user.name)}
            </div>
          </div>
        </header>

        <main className="flex-1 p-5 lg:p-8 fade-up"><Outlet /></main>
      </div>
    </div>
  )
}
