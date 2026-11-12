import { Logo } from './ui'

/** Two-panel layout shared by Login and Register (ported from the prototype's LoginPage). */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="min-h-screen w-full bg-bg flex">
      <div className="hidden lg:flex w-[46%] bg-primary relative flex-col justify-between p-14 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-[0.08]"
          style={{ backgroundImage: 'repeating-linear-gradient(to bottom, transparent, transparent 27px, rgba(255,255,255,0.5) 27px, rgba(255,255,255,0.5) 28px)' }} />
        <div className="relative z-10"><Logo light /></div>
        <div className="relative z-10 max-w-md">
          <div className="text-[11px] font-mono uppercase tracking-[0.2em] text-gold mb-4">SVKM Institute of Technology</div>
          <h1 className="font-display text-[38px] leading-[1.15] font-semibold mb-5">Your college knowledge, in one place.</h1>
          <p className="text-white/70 text-[15px] leading-relaxed">
            Ask doubts, understand concepts and learn from your college's own study material — indexed from the notes your faculty share with you.
          </p>
        </div>
        <div className="relative z-10 text-white/50 text-[13px] font-mono">Answers grounded in your college's material</div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-[400px] py-8">
          <div className="lg:hidden mb-10"><Logo /></div>
          <h2 className="font-display text-2xl font-semibold mb-1.5">{title}</h2>
          <p className="text-muted text-sm mb-8">{subtitle}</p>
          {children}
          <p className="text-center text-sm text-muted mt-7">{footer}</p>
        </div>
      </div>
    </div>
  )
}
