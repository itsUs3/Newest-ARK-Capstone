import { useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { FiLoader } from 'react-icons/fi'
import { generateGnnFloorplan } from '../utils/api'

const EXAMPLES = {
  'EX 1': {
    boundary_wkt: 'POLYGON ((25 63, 230 63, 230 200, 25 200, 25 63))',
    front_door_wkt: 'POLYGON ((208 168, 212 168, 212 194, 208 194, 208 168))',
    room_centroids: [[184, 77], [67, 94]],
    bathroom_centroids: [[185, 134], [126, 74]],
    kitchen_centroids: [[52, 176]],
  },
  'EX 2': {
    boundary_wkt: 'POLYGON ((26 47, 216 47, 216 186, 26 186, 26 47))',
    front_door_wkt: 'POLYGON ((26 56, 56 56, 56 59, 26 59, 26 56))',
    room_centroids: [[198, 87], [174, 166]],
    bathroom_centroids: [[51, 169], [148, 91]],
    kitchen_centroids: [[44, 105]],
  },
}

export default function FloorplanGenerator() {
  const [exampleName, setExampleName] = useState('EX 1')
  const [boundaryWkt, setBoundaryWkt] = useState(EXAMPLES['EX 1'].boundary_wkt)
  const [doorWkt, setDoorWkt] = useState(EXAMPLES['EX 1'].front_door_wkt)
  const [roomCentroids, setRoomCentroids] = useState(JSON.stringify(EXAMPLES['EX 1'].room_centroids, null, 2))
  const [bathroomCentroids, setBathroomCentroids] = useState(JSON.stringify(EXAMPLES['EX 1'].bathroom_centroids, null, 2))
  const [kitchenCentroids, setKitchenCentroids] = useState(JSON.stringify(EXAMPLES['EX 1'].kitchen_centroids, null, 2))

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const loadExample = (name) => {
    const ex = EXAMPLES[name]
    setExampleName(name)
    setBoundaryWkt(ex.boundary_wkt)
    setDoorWkt(ex.front_door_wkt)
    setRoomCentroids(JSON.stringify(ex.room_centroids, null, 2))
    setBathroomCentroids(JSON.stringify(ex.bathroom_centroids, null, 2))
    setKitchenCentroids(JSON.stringify(ex.kitchen_centroids, null, 2))
    setResult(null)
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    let parsedRooms
    let parsedBath
    let parsedKitchen

    try {
      parsedRooms = JSON.parse(roomCentroids)
      parsedBath = JSON.parse(bathroomCentroids)
      parsedKitchen = JSON.parse(kitchenCentroids)
    } catch {
      toast.error('Centroids must be valid JSON arrays, e.g. [[120,90],[50,70]]')
      return
    }

    setLoading(true)
    try {
      const payload = {
        boundary_wkt: boundaryWkt,
        front_door_wkt: doorWkt,
        room_centroids: parsedRooms,
        bathroom_centroids: parsedBath,
        kitchen_centroids: parsedKitchen,
      }

      const response = await generateGnnFloorplan(payload)
      setResult(response.data)
      if (response.data.success) {
        toast.success('GNN floor plan generated')
      } else {
        toast.error(response.data.error || 'Generation failed')
      }
    } catch (error) {
      const message = error?.response?.data?.detail || 'Failed to generate floor plan'
      toast.error(message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
          <h1 className="text-3xl font-semibold text-white">Floor Plan Generation Using GNNs</h1>
          <p className="text-slate-400 mt-1">Boundary + front door + room centroids → graph message passing → layout image</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 space-y-4">
            <form onSubmit={handleGenerate} className="rounded-lg border border-slate-800 bg-slate-900 p-4 space-y-3">
              <h2 className="text-base font-semibold text-white">Inputs</h2>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Example</label>
                <select value={exampleName} onChange={(e) => loadExample(e.target.value)} className="input-field w-full">
                  {Object.keys(EXAMPLES).map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Boundary WKT</label>
                <textarea value={boundaryWkt} onChange={(e) => setBoundaryWkt(e.target.value)} rows={3} className="input-field w-full" />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Front Door WKT</label>
                <textarea value={doorWkt} onChange={(e) => setDoorWkt(e.target.value)} rows={2} className="input-field w-full" />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Room Centroids (JSON)</label>
                <textarea value={roomCentroids} onChange={(e) => setRoomCentroids(e.target.value)} rows={4} className="input-field w-full font-mono text-xs" />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Bathroom Centroids (JSON)</label>
                <textarea value={bathroomCentroids} onChange={(e) => setBathroomCentroids(e.target.value)} rows={3} className="input-field w-full font-mono text-xs" />
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1.5">Kitchen Centroids (JSON)</label>
                <textarea value={kitchenCentroids} onChange={(e) => setKitchenCentroids(e.target.value)} rows={3} className="input-field w-full font-mono text-xs" />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-100 disabled:opacity-50"
              >
                {loading ? <FiLoader className="animate-spin" /> : null}
                {loading ? 'Generating...' : 'Generate with GNN'}
              </button>
            </form>
          </div>

          <div className="lg:col-span-2 rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-base font-semibold text-white mb-3">Output</h2>
            {!result ? (
              <div className="text-slate-400 text-sm py-8 text-center">Run generation to view graph output</div>
            ) : !result.success ? (
              <div className="rounded-lg border border-red-900 bg-red-950/20 p-4 text-red-200 text-sm">
                <p className="font-semibold mb-1">Generation failed</p>
                <p>{result.error || result.message || 'Unknown error'}</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-center">
                    <p className="text-xs text-slate-400">Nodes</p>
                    <p className="text-xl font-semibold text-white mt-1">{result.graph?.node_count || 0}</p>
                  </div>
                  <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 text-center">
                    <p className="text-xs text-slate-400">Edges</p>
                    <p className="text-xl font-semibold text-white mt-1">{result.graph?.edge_count || 0}</p>
                  </div>
                </div>

                {result.image_base64 ? (
                  <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 mb-4">
                    <img
                      src={`data:image/png;base64,${result.image_base64}`}
                      alt="Generated floor plan"
                      className="w-full rounded-md"
                    />
                  </div>
                ) : null}

                <div className="rounded-lg border border-slate-700 bg-slate-950 p-3 max-h-[38vh] overflow-auto">
                  <p className="text-xs text-slate-400 mb-2">Node Predictions</p>
                  <div className="space-y-2">
                    {(result.nodes || []).map((n) => (
                      <div key={n.id} className="text-xs text-slate-200 border border-slate-800 rounded px-2 py-2">
                        <span className="font-semibold">#{n.id}</span> {n.type} • centroid [{n.centroid?.[0]}, {n.centroid?.[1]}] • {n.predicted_width} × {n.predicted_height}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
