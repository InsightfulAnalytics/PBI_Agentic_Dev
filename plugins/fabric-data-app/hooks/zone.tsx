import type { ClientModule } from 'claude-code'

export type ZoneProps = { id: string }
type Local = { ref: { unpoint?: () => void; id: string } }

const Zone: ClientModule<ZoneProps, Local> = (props, surface) => {
  const { Box } = surface.elements
  let state = surface.state
  if (state === undefined) {
    state = { ref: { id: props.id } }
    surface.setState(state)
  }
  const ref = state.ref
  ref.id = props.id
  ref.unpoint ??= surface.onPointer(e => {
    if (e.type === 'up' && (e.button ?? 'left') === 'left') surface.post({ zone: ref.id, shift: Boolean(e.shift), ctrl: Boolean(e.ctrl) })
  })
  return <Box width="100%" height="100%" />
}

export default Zone
