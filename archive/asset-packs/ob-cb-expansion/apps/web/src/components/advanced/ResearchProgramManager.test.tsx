import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ResearchProgramManager } from './ResearchProgramManager'
import * as protocolApi from '../../api/protocol'

vi.mock('../../api/protocol')

describe('ResearchProgramManager', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders initial form and steps', () => {
    render(<ResearchProgramManager />)
    expect(screen.getByText('步骤 1: 声明 Research Program')).toBeInTheDocument()
    expect(screen.getByLabelText('课题名称:')).toBeInTheDocument()
  })

  it('navigates between steps correctly', async () => {
    render(<ResearchProgramManager />)
    const step2Btn = screen.getByText('步骤 2: 协议设计')
    fireEvent.click(step2Btn)
    expect(screen.getByText('步骤 2: 设计 Study Protocol Draft')).toBeInTheDocument()
  })

  it('saves program successfully and moves to step 2', async () => {
    vi.mocked(protocolApi.saveProgram).mockResolvedValue({
      id: 'program_default_01',
      title: 'Test Program',
      theoreticalQuestion: 'Why?',
      targetJournal: null,
      owner: null,
      constructKeys: [],
    })

    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    render(<ResearchProgramManager />)
    const saveBtn = screen.getByText('保存并下一步')
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(protocolApi.saveProgram).toHaveBeenCalled()
      expect(alertSpy).toHaveBeenCalledWith('研究计划已成功保存！')
      expect(screen.getByText('步骤 2: 设计 Study Protocol Draft')).toBeInTheDocument()
    })

    alertSpy.mockRestore()
  })
})
