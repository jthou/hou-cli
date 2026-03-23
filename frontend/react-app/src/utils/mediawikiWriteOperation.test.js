import { describe, it, expect } from 'vitest'
import { operationFromMwDialogMode } from './mediawikiWriteOperation'

describe('operationFromMwDialogMode', () => {
  it('maps three modes', () => {
    expect(operationFromMwDialogMode('create')).toBe('create')
    expect(operationFromMwDialogMode('edit')).toBe('edit')
    expect(operationFromMwDialogMode('append')).toBe('append')
  })
  it('defaults unknown to edit', () => {
    expect(operationFromMwDialogMode('')).toBe('edit')
    expect(operationFromMwDialogMode(undefined)).toBe('edit')
  })
})
