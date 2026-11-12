import { Hammer } from 'lucide-react'
import { EmptyState } from '../components/ui'

/** Honest stand-in for pages whose backend isn't built yet. It does not simulate any data. */
export default function ComingNext({ feature, batch }) {
  return (
    <EmptyState
      icon={Hammer}
      title={`${feature} — not built yet`}
      message={`This page needs backend features scheduled for ${batch}. It will be connected to real data when that batch lands.`}
    />
  )
}
