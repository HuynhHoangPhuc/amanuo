/** Document viewer — renders images or PDFs from job document endpoint. */

import { useState } from 'react'
import { ZoomIn, ZoomOut, RotateCw } from 'lucide-react'

interface DocumentViewerProps {
  src: string
  alt?: string
}

export function DocumentViewer({ src, alt = 'Document' }: DocumentViewerProps) {
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)

  const isPdf = src.toLowerCase().endsWith('.pdf') || src.includes('/document')

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 bg-gray-50 rounded-t-xl">
        <button
          onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}
          className="p-1.5 rounded hover:bg-gray-200 text-gray-600"
          title="Zoom out"
        >
          <ZoomOut size={16} />
        </button>
        <span className="text-xs text-gray-500 w-12 text-center">{Math.round(zoom * 100)}%</span>
        <button
          onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
          className="p-1.5 rounded hover:bg-gray-200 text-gray-600"
          title="Zoom in"
        >
          <ZoomIn size={16} />
        </button>
        <button
          onClick={() => setRotation((r) => (r + 90) % 360)}
          className="p-1.5 rounded hover:bg-gray-200 text-gray-600"
          title="Rotate"
        >
          <RotateCw size={16} />
        </button>
      </div>

      {/* Document area */}
      <div className="flex-1 overflow-auto bg-gray-100 rounded-b-xl p-4 flex items-start justify-center min-h-[400px]">
        {isPdf ? (
          <iframe
            src={src}
            title={alt}
            className="w-full h-full min-h-[500px] rounded border border-gray-200 bg-white"
            style={{ transform: `scale(${zoom}) rotate(${rotation}deg)`, transformOrigin: 'top center' }}
          />
        ) : (
          <img
            src={src}
            alt={alt}
            className="max-w-full shadow-sm rounded border border-gray-200"
            style={{ transform: `scale(${zoom}) rotate(${rotation}deg)`, transformOrigin: 'top center' }}
          />
        )}
      </div>
    </div>
  )
}
