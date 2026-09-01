import type { KeyboardEvent, Ref } from 'react'
import type { WorkspaceView } from './hooks/useWorkspaceState'

interface AppWorkspaceTabsProps {
  navRef: Ref<HTMLDivElement>
  workspaceSteps: Array<{ view: WorkspaceView; label: string; badge: string }>
  activeView: WorkspaceView
  onSelect: (view: WorkspaceView) => void
}

export function AppWorkspaceTabs({
  navRef,
  workspaceSteps,
  activeView,
  onSelect,
}: AppWorkspaceTabsProps) {
  const handleWorkspaceTabKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = workspaceSteps.findIndex((step) => step.view === activeView)
    if (currentIndex === -1) return

    let nextIndex = currentIndex
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      nextIndex = (currentIndex + 1) % workspaceSteps.length
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      nextIndex = (currentIndex - 1 + workspaceSteps.length) % workspaceSteps.length
    } else if (event.key === 'Home') {
      nextIndex = 0
    } else if (event.key === 'End') {
      nextIndex = workspaceSteps.length - 1
    } else {
      return
    }

    event.preventDefault()
    const nextView = workspaceSteps[nextIndex]?.view
    if (!nextView) return
    onSelect(nextView)
    document.getElementById(`workspace-tab-${nextView}`)?.focus()
  }

  return (
    <div
      ref={navRef}
      className="workspace-nav"
      role="tablist"
      aria-label="工作区视图切换"
      onKeyDown={handleWorkspaceTabKeyDown}
    >
      {workspaceSteps.map((step) => {
        const isActive = activeView === step.view
        return (
          <button
            key={step.view}
            type="button"
            role="tab"
            id={`workspace-tab-${step.view}`}
            aria-selected={isActive}
            aria-label={step.label}
            aria-describedby={`workspace-status-${step.view}`}
            aria-controls={isActive ? `workspace-panel-${step.view}` : undefined}
            tabIndex={isActive ? 0 : -1}
            data-workspace-view={step.view}
            className={`workspace-tab ${isActive ? 'is-active' : ''}`}
            onClick={() => onSelect(step.view)}
          >
            <span className="tab-label">{step.label}</span>
            <span className="tab-badge" id={`workspace-status-${step.view}`}>{step.badge}</span>
          </button>
        )
      })}
    </div>
  )
}
