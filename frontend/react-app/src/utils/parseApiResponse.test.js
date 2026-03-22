import { describe, it, expect } from 'vitest'
import { normalizeFastApiDetail, parseApiResponseJson } from './parseApiResponse'

describe('normalizeFastApiDetail', () => {
  it('string passthrough', () => {
    expect(normalizeFastApiDetail('x')).toBe('x')
  })
  it('array of objects with msg', () => {
    expect(normalizeFastApiDetail([{ msg: 'a' }, { msg: 'b' }])).toBe('a；b')
  })
})

describe('parseApiResponseJson', () => {
  it('parses ok json', async () => {
    const res = new Response(JSON.stringify({ success: true, media_id: 'm1' }), { status: 200 })
    await expect(parseApiResponseJson(res)).resolves.toEqual({ success: true, media_id: 'm1' })
  })

  it('non-json error body does not throw SyntaxError', async () => {
    const res = new Response('Internal Server Error', { status: 500 })
    await expect(parseApiResponseJson(res)).rejects.toThrow(/500|服务异常|Internal Server Error/)
  })

  it('json error uses detail', async () => {
    const res = new Response(JSON.stringify({ detail: '封面过大' }), { status: 400 })
    await expect(parseApiResponseJson(res)).rejects.toThrow('封面过大')
  })
})
