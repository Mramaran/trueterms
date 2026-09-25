/**
 * VoiceWaveform.jsx — Real-time audio level canvas visualiser
 *
 * Uses the AnalyserNode ref from useVoice — no React state churn.
 * Three visual modes:
 *   recording  → live frequency bars (blue→violet gradient)
 *   processing → scanning animation
 *   idle       → subtle flatline pulse
 */

import { useRef, useEffect } from 'react'

const W         = 128
const H         = 38
const BAR_COUNT = 22
const BAR_GAP   = 2
const BAR_W     = Math.floor((W - (BAR_COUNT - 1) * BAR_GAP) / BAR_COUNT)
const MIN_H     = 3
const MAX_H     = H - 6

export default function VoiceWaveform({ analyserRef, isRecording, isProcessing }) {
  const canvasRef = useRef(null)
  const rafRef    = useRef(null)
  const phaseRef  = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    // Gradient reused every frame
    function makeGrad(alpha = 1) {
      const g = ctx.createLinearGradient(0, 0, W, 0)
      g.addColorStop(0,   `rgba(59,130,246,${alpha})`)
      g.addColorStop(0.5, `rgba(99,102,241,${alpha})`)
      g.addColorStop(1,   `rgba(139,92,246,${alpha})`)
      return g
    }

    function draw() {
      rafRef.current = requestAnimationFrame(draw)
      ctx.clearRect(0, 0, W, H)
      phaseRef.current += isRecording ? 0.08 : isProcessing ? 0.10 : 0.03

      const heights = new Array(BAR_COUNT).fill(MIN_H)

      if (isRecording && analyserRef?.current) {
        // ── Live audio data ────────────────────────────────────────────────
        const bufLen  = analyserRef.current.frequencyBinCount  // fftSize/2 = 32
        const dataArr = new Uint8Array(bufLen)
        analyserRef.current.getByteFrequencyData(dataArr)
        for (let i = 0; i < BAR_COUNT; i++) {
          const srcIdx = Math.min(Math.floor(i * bufLen / BAR_COUNT), bufLen - 1)
          const v = dataArr[srcIdx] / 255
          heights[i] = Math.max(MIN_H, Math.round(v * MAX_H))
        }
      } else if (isProcessing) {
        // ── Scanning animation ─────────────────────────────────────────────
        for (let i = 0; i < BAR_COUNT; i++) {
          const v = (Math.sin(i * 0.45 + phaseRef.current) + 1) / 2
          heights[i] = Math.max(MIN_H, Math.round(v * MAX_H * 0.55))
        }
      } else {
        // ── Idle: subtle flatline pulse ────────────────────────────────────
        for (let i = 0; i < BAR_COUNT; i++) {
          const v = (Math.sin(i * 0.9 + phaseRef.current) + 1) / 2
          heights[i] = MIN_H + Math.round(v * 4)
        }
      }

      const alpha = isRecording ? 0.92 : isProcessing ? 0.70 : 0.35
      ctx.fillStyle = makeGrad(alpha)

      for (let i = 0; i < BAR_COUNT; i++) {
        const x = i * (BAR_W + BAR_GAP)
        const h = heights[i]
        const y = (H - h) / 2
        const r = Math.min(BAR_W / 2, h / 2, 2.5)
        ctx.beginPath()
        if (ctx.roundRect) {
          ctx.roundRect(x, y, BAR_W, h, r)
        } else {
          ctx.rect(x, y, BAR_W, h)  // fallback for older browsers
        }
        ctx.fill()
      }
    }

    draw()
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [analyserRef, isRecording, isProcessing])

  return (
    <canvas
      ref={canvasRef}
      width={W}
      height={H}
      className="voice-waveform-canvas"
      aria-hidden="true"
    />
  )
}
