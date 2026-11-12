import { Loader2 } from 'lucide-react'

export function Button({ children, variant = 'primary', size = 'md', loading = false, className = '', disabled, ...rest }) {
  const base = 'inline-flex items-center justify-center gap-2 font-medium transition-colors rounded-md disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = { sm: 'px-3 py-1.5 text-[13px]', md: 'px-4 py-2.5 text-sm', lg: 'px-5 py-3 text-[15px]' }
  const variants = {
    primary: 'bg-primary text-white hover:bg-primary-dark',
    secondary: 'bg-white text-ink border border-line hover:border-primary/40 hover:bg-primary/5',
    gold: 'bg-gold text-primary-dark hover:bg-gold-dark',
    ghost: 'text-primary hover:bg-primary/5',
    subtle: 'bg-primary/5 text-primary hover:bg-primary/10',
    danger: 'bg-[#B3472E] text-white hover:bg-[#8f3722]',
  }
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} disabled={disabled || loading} {...rest}>
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  )
}

export function Pill({ children, tone = 'neutral', className = '' }) {
  const tones = {
    neutral: 'bg-bg text-muted border border-line',
    green: 'bg-primary/8 text-primary border border-primary/15',
    gold: 'bg-gold/15 text-gold-dark border border-gold/30',
    open: 'bg-[#F3E9DC] text-[#8A5A20] border border-[#E4CBA6]',
    answered: 'bg-[#EEF2EF] text-[#3A675F] border border-[#D6E1DC]',
    danger: 'bg-[#F7E4DF] text-[#8f3722] border border-[#E9C3B9]',
  }
  return <span className={`text-[11.5px] px-2 py-0.5 rounded font-medium tracking-wide ${tones[tone]} ${className}`}>{children}</span>
}

export function ProgressBar({ value, tone = 'primary', h = 'h-1.5' }) {
  return (
    <div className={`w-full progress-track rounded-full ${h} overflow-hidden`}>
      <div className={`${h} rounded-full ${tone === 'gold' ? 'bg-gold' : 'bg-primary'}`} style={{ width: `${value}%`, transition: 'width .5s ease' }} />
    </div>
  )
}

export function SectionHeader({ eyebrow, title, action }) {
  return (
    <div className="flex items-end justify-between mb-4 pb-3 border-b border-line rule-band">
      <div>
        {eyebrow && <div className="text-[11px] font-mono uppercase tracking-widest text-muted mb-1">{eyebrow}</div>}
        <h2 className="font-display text-[19px] font-semibold text-ink">{title}</h2>
      </div>
      {action}
    </div>
  )
}

export function Field({ label, id, error, hint, children, ...inputProps }) {
  return (
    <div>
      <label htmlFor={id} className="text-[13px] font-medium text-ink block mb-1.5">{label}</label>
      {children || (
        <input id={id} {...inputProps}
          aria-invalid={!!error}
          className="w-full px-3.5 py-2.5 rounded-md border border-line bg-white text-sm placeholder:text-muted/70 focus:border-primary" />
      )}
      {hint && !error && <p className="text-[12px] text-muted mt-1">{hint}</p>}
      {error && <p className="text-[12px] text-[#B3472E] mt-1">{error}</p>}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-muted text-sm" role="status">
      <Loader2 className="w-4 h-4 animate-spin" /> {label}
    </div>
  )
}

export function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="card-index rounded-lg p-10 text-center">
      {Icon && <Icon className="w-8 h-8 text-muted mx-auto mb-3" />}
      <h3 className="font-display font-semibold text-[16px] mb-1">{title}</h3>
      {message && <p className="text-sm text-muted max-w-sm mx-auto">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Confirm', danger = false, loading = false, onConfirm, onCancel }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40" onClick={onCancel}>
      <div role="dialog" aria-modal="true" aria-labelledby="confirm-title"
        className="fade-up bg-white rounded-lg border border-line w-full max-w-sm p-5" onClick={(e) => e.stopPropagation()}>
        <h3 id="confirm-title" className="font-display font-semibold text-[17px] mb-1.5">{title}</h3>
        <p className="text-sm text-muted mb-5">{message}</p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onCancel} disabled={loading}>Cancel</Button>
          <Button variant={danger ? 'danger' : 'primary'} size="sm" onClick={onConfirm} loading={loading}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  )
}

export function Logo({ light = false, size = 'md' }) {
  const box = size === 'sm' ? 'w-7 h-7 text-[13px]' : 'w-8 h-8 text-sm'
  return (
    <div className="flex items-center gap-2.5">
      <div className={`${box} rounded-md flex items-center justify-center font-display font-bold ${light ? 'bg-gold text-primary-dark' : 'bg-primary text-white'}`}>S</div>
      <span className={`font-display font-semibold tracking-tight ${size === 'sm' ? 'text-[15px]' : 'text-lg'} ${light ? 'text-white' : ''}`}>StudySphere</span>
    </div>
  )
}
