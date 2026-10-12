import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../src/api/errors'
import BackupSection from '../src/components/BackupSection.vue'

const backup = {
  name: 'noteclaire-20261004-120000.zip',
  size: 2_500_000,
  created_at: '2026-10-04T12:00:00Z',
}
const api = vi.hoisted(() => ({
  backups: vi.fn(),
  createBackup: vi.fn(),
  restoreBackup: vi.fn(),
  restoreBackupFile: vi.fn(),
  backupUrl: (name: string) => `/api/backups/${name}`,
}))
vi.mock('../src/api/client', () => ({ api }))

describe('BackupSection', () => {
  it('sauvegarde à la demande et propose le téléchargement', async () => {
    api.backups.mockResolvedValueOnce([]).mockResolvedValue([backup])
    api.createBackup.mockResolvedValue(backup)
    const wrapper = mount(BackupSection)
    await flushPromises()
    expect(wrapper.text()).toContain('Aucune sauvegarde')

    await wrapper.find('button').trigger('click')
    await flushPromises()
    expect(api.createBackup).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Sauvegarde faite.')
    expect(wrapper.text()).toContain('2,4 Mo')
    const link = wrapper.find('a')
    expect(link.attributes('href')).toBe('/api/backups/noteclaire-20261004-120000.zip')
  })

  it('restaure une sauvegarde après confirmation', async () => {
    api.backups.mockResolvedValue([backup])
    api.restoreBackup.mockResolvedValue(undefined)
    const assign = vi.fn()
    vi.stubGlobal('location', { assign })
    const confirm = vi.spyOn(window, 'confirm')
    const wrapper = mount(BackupSection)
    await flushPromises()

    confirm.mockReturnValueOnce(false)
    await wrapper.find('li button').trigger('click')
    expect(api.restoreBackup).not.toHaveBeenCalled()

    confirm.mockReturnValueOnce(true)
    await wrapper.find('li button').trigger('click')
    await flushPromises()
    expect(api.restoreBackup).toHaveBeenCalledWith(backup.name)
    expect(assign).toHaveBeenCalledWith('/')
    vi.unstubAllGlobals()
  })

  it('montre le refus d’une sauvegarde incompatible', async () => {
    api.backups.mockResolvedValue([backup])
    api.restoreBackup.mockRejectedValue(new ApiError('backup_incompatible', 422))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mount(BackupSection)
    await flushPromises()
    await wrapper.find('li button').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })
})
