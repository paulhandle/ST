'use client'

import { useEffect, useRef } from 'react'
import type { ActivityDetailSampleOut } from '@/lib/api/types'

interface RouteMapProps {
  samples: ActivityDetailSampleOut[]
  emptyText: string
}

export default function RouteMap({ samples, emptyText }: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<import('leaflet').Map | null>(null)

  const gpsPoints = samples
    .filter((s) => s.latitude != null && s.longitude != null)
    .map((s) => [s.latitude as number, s.longitude as number] as [number, number])

  useEffect(() => {
    if (!containerRef.current || gpsPoints.length < 2) return

    let cancelled = false

    import('leaflet').then((L) => {
      if (cancelled || !containerRef.current) return

      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }

      const map = L.default.map(containerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
      })

      L.default.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 18,
      }).addTo(map)

      const polyline = L.default.polyline(gpsPoints, {
        color: 'var(--accent, #f5a623)',
        weight: 4,
        opacity: 0.9,
      })
      polyline.addTo(map)

      map.fitBounds(polyline.getBounds(), { padding: [20, 20] })

      L.default.circleMarker(gpsPoints[0], {
        radius: 7,
        fillColor: '#111111',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 1,
      }).addTo(map)

      L.default.circleMarker(gpsPoints[gpsPoints.length - 1], {
        radius: 7,
        fillColor: 'var(--accent, #f5a623)',
        color: '#ffffff',
        weight: 2,
        fillOpacity: 1,
      }).addTo(map)

      mapRef.current = map
    })

    return () => {
      cancelled = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [gpsPoints.length]) // eslint-disable-line react-hooks/exhaustive-deps

  if (gpsPoints.length < 2) {
    return (
      <div
        className="annot text-faint"
        style={{
          padding: 24,
          border: '1px solid var(--rule-soft)',
          background: 'var(--paper-soft)',
          textAlign: 'center',
        }}
      >
        {emptyText}
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      data-testid="route-map"
      style={{
        width: '100%',
        height: 300,
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        border: '1px solid var(--rule-soft)',
      }}
    />
  )
}
