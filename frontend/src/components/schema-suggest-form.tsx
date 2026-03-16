/** Schema auto-suggest form — upload a document image to get AI-suggested fields. */

import { useState, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, AlertTriangle, Loader2, X } from 'lucide-react'
import { api } from '#/lib/api-client'
import { queryKeys } from '#/lib/query-keys'
import { useToast } from '#/components/toast-provider'
import { SuggestedFieldsEditor } from '#/components/suggested-fields-editor'
import type { SuggestSchemaResponse, SuggestedField, SchemaCreateRequest } from '#/lib/types'

interface SchemaSuggestFormProps {
  onClose: () => void
}

export function SchemaSuggestForm({ onClose }: SchemaSuggestFormProps) {
  const { toast } = useToast()
  const qc = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [lang, setLang] = useState('en')
  const [schemaName, setSchemaName] = useState('')
  const [suggestedFields, setSuggestedFields] = useState<SuggestedField[] | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // POST /schemas/suggest — analyze document
  const analyzeMutation = useMutation({
    mutationFn: async (f: File) => {
      const form = new FormData()
      form.append('file', f)
      return api.postForm<SuggestSchemaResponse>(`/schemas/suggest?lang=${lang}`, form)
    },
    onSuccess: (data) => {
      setSuggestedFields(data.fields)
      if (data.fields.length === 0) {
        toast('No fields detected — VLM may be unavailable or document unclear', 'error')
      }
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  // POST /schemas — save suggested fields as schema
  const saveMutation = useMutation({
    mutationFn: (req: SchemaCreateRequest) => api.post('/schemas', req),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.schemas.list() })
      toast('Schema created from suggestions', 'success')
      onClose()
    },
    onError: (e: Error) => toast(e.message, 'error'),
  })

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }

  const handleSave = () => {
    if (!schemaName.trim() || !suggestedFields?.length) return
    saveMutation.mutate({
      name: schemaName,
      fields: suggestedFields.map(({ label, type, occurrence }) => ({
        label, type: type as 'text' | 'number' | 'date' | 'boolean', occurrence: occurrence as 'required once' | 'optional once' | 'optional multiple',
      })),
    })
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">Auto-Suggest Schema</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
        </div>

        {/* File dropzone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
            isDragging ? 'border-blue-400 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <Upload size={24} className="mx-auto text-gray-400 mb-2" />
          {file ? (
            <p className="text-sm text-gray-700 font-medium">{file.name}</p>
          ) : (
            <p className="text-sm text-gray-500">Drop image or PDF, or click to browse</p>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="image/*,application/pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div className="flex gap-2">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none"
          >
            <option value="en">English</option>
            <option value="ja">Japanese</option>
            <option value="vi">Vietnamese</option>
          </select>
          <button
            onClick={() => file && analyzeMutation.mutate(file)}
            disabled={!file || analyzeMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {analyzeMutation.isPending ? (
              <><Loader2 size={14} className="animate-spin" /> Analyzing document…</>
            ) : 'Analyze Document'}
          </button>
        </div>

        {suggestedFields !== null && (
          <>
            {/* Warning banner */}
            <div className="flex gap-2 rounded-lg bg-yellow-50 border border-yellow-200 p-3">
              <AlertTriangle size={16} className="shrink-0 text-yellow-600 mt-0.5" />
              <p className="text-xs text-yellow-700">AI-suggested fields — please verify accuracy before saving.</p>
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Schema name (required to save)"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
              />
              <SuggestedFieldsEditor fields={suggestedFields} onChange={setSuggestedFields} />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!schemaName.trim() || !suggestedFields.length || saveMutation.isPending}
                className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? 'Saving…' : 'Save as Schema'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
