import { useEffect, useMemo, useRef, useState } from 'react'
import { FiExternalLink, FiMapPin } from 'react-icons/fi'

const LEAFLET_CSS_ID = 'mynivas-leaflet-css'
const LEAFLET_SCRIPT_ID = 'mynivas-leaflet-script'

function loadLeafletAssets() {
  if (window.L) {
    return Promise.resolve(window.L)
  }

  return new Promise((resolve, reject) => {
    if (!document.getElementById(LEAFLET_CSS_ID)) {
      const css = document.createElement('link')
      css.id = LEAFLET_CSS_ID
      css.rel = 'stylesheet'
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      document.head.appendChild(css)
    }

    const existingScript = document.getElementById(LEAFLET_SCRIPT_ID)
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.L), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Failed to load map assets')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = LEAFLET_SCRIPT_ID
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true
    script.onload = () => resolve(window.L)
    script.onerror = () => reject(new Error('Failed to load map assets'))
    document.body.appendChild(script)
  })
}

function makePriceMarker(property, isActive) {
  const border = isActive ? '#ffffff' : 'rgba(99, 102, 241, 0.9)'
  const background = isActive
    ? 'linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)'
    : 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)'

  return `
    <div style="
      min-width: 92px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 2px solid ${border};
      background: ${background};
      color: white;
      font-weight: 700;
      font-size: 12px;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.35);
      text-align: center;
      white-space: nowrap;
    ">
      ${property.price}
    </div>
  `
}

export default function PropertyDiscoveryMap({
  properties,
  center,
  selectedId,
  onSelect,
  onOpenProperty,
}) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markersLayerRef = useRef(null)
  const [mapError, setMapError] = useState('')

  const mapProperties = useMemo(
    () => properties.filter((property) => property.latitude != null && property.longitude != null),
    [properties]
  )

  useEffect(() => {
    let cancelled = false

    loadLeafletAssets()
      .then((L) => {
        if (cancelled || !mapRef.current) return

        if (!mapInstanceRef.current) {
          mapInstanceRef.current = L.map(mapRef.current, {
            zoomControl: true,
            attributionControl: false,
          }).setView(
            [center?.latitude || 19.076, center?.longitude || 72.8777],
            mapProperties.length > 1 ? 11 : 12
          )

          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
          }).addTo(mapInstanceRef.current)

          markersLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setMapError(error.message || 'Could not load the map view.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [center?.latitude, center?.longitude, mapProperties.length])

  useEffect(() => {
    const L = window.L
    if (!L || !mapInstanceRef.current || !markersLayerRef.current) return

    markersLayerRef.current.clearLayers()

    if (mapProperties.length === 0) {
      if (center?.latitude && center?.longitude) {
        mapInstanceRef.current.setView([center.latitude, center.longitude], 11)
      }
      return
    }

    const bounds = []
    mapProperties.forEach((property) => {
      const isActive = property.id === selectedId
      const marker = L.marker([property.latitude, property.longitude], {
        icon: L.divIcon({
          className: 'mynivas-price-marker',
          html: makePriceMarker(property, isActive),
          iconSize: [110, 40],
          iconAnchor: [55, 40],
        }),
      })

      marker.on('click', () => onSelect(property))
      marker.bindPopup(`
        <div style="min-width: 220px; color: #0f172a;">
          <div style="font-weight: 700; margin-bottom: 4px;">${property.name}</div>
          <div style="font-size: 12px; margin-bottom: 6px;">${property.address || property.city || ''}</div>
          <div style="font-size: 13px; font-weight: 700; color: #4338ca;">${property.price}</div>
        </div>
      `)

      marker.addTo(markersLayerRef.current)
      bounds.push([property.latitude, property.longitude])
    })

    if (bounds.length === 1) {
      mapInstanceRef.current.setView(bounds[0], 13)
    } else {
      mapInstanceRef.current.fitBounds(bounds, { padding: [40, 40] })
    }
  }, [center, mapProperties, onSelect, selectedId])

  useEffect(() => {
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-950/50 overflow-hidden">
      <div className="grid grid-cols-1 xl:grid-cols-[320px_minmax(0,1fr)] min-h-[540px]">
        <div className="border-b xl:border-b-0 xl:border-r border-slate-800 bg-slate-950/80">
          <div className="p-4 border-b border-slate-800">
            <p className="text-xs uppercase tracking-[0.25em] text-slate-500 mb-2">Matched Listings</p>
            <p className="text-sm text-slate-300">
              {properties.length} properties aligned with your query
            </p>
          </div>

          <div className="max-h-[540px] overflow-y-auto p-3 space-y-3">
            {properties.map((property) => {
              const isSelected = property.id === selectedId
              return (
                <div
                  key={property.id}
                  onClick={() => onSelect(property)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onSelect(property)
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  className={`w-full text-left rounded-2xl border p-4 transition ${
                    isSelected
                      ? 'border-indigo-400 bg-indigo-500/15'
                      : 'border-slate-800 bg-slate-900/60 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <p className="font-semibold text-white leading-snug">{property.name}</p>
                      <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                        <FiMapPin />
                        {property.locality || property.city || property.address}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-indigo-200">{property.price}</p>
                      <p className="text-[11px] text-slate-500">{Math.round((property.similarity_score || 0) * 100)}% fit</p>
                    </div>
                  </div>

                  {property.match_reasons?.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {property.match_reasons.slice(0, 2).map((reason) => (
                        <span key={reason} className="rounded-full bg-slate-800 px-2.5 py-1 text-[11px] text-slate-300">
                          {reason}
                        </span>
                      ))}
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      onOpenProperty(property)
                    }}
                    className="inline-flex items-center gap-2 text-sm font-medium text-cyan-300 hover:text-cyan-200"
                  >
                    Open details
                    <FiExternalLink />
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        <div className="relative min-h-[540px]">
          {mapError ? (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900 text-slate-300 p-6 text-center">
              {mapError}
            </div>
          ) : null}
          <div ref={mapRef} className="h-full min-h-[540px] w-full" />
        </div>
      </div>
    </div>
  )
}
