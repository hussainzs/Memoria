"use client";
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  Plus, 
  Save, 
  ArrowLeft, 
  Tag, 
  Type, 
  Eye, 
  FileText,
  AlertCircle,
  CheckCircle
} from 'lucide-react'

interface MemoryFormData {
  user_id: string
  type: string
  title: string
  content: string
  tags: string[]
  source: string
  visibility: string
}

const MEMORY_TYPES = [
  { value: 'fact', label: 'Fact', color: '#3b82f6' },
  { value: 'event', label: 'Event', color: '#10b981' },
  { value: 'preference', label: 'Preference', color: '#f59e0b' },
  { value: 'entity', label: 'Entity', color: '#8b5cf6' },
  { value: 'media', label: 'Media', color: '#ef4444' },
  { value: 'skill', label: 'Skill', color: '#06b6d4' },
  { value: 'instruction', label: 'Instruction', color: '#84cc16' }
]

const VISIBILITY_OPTIONS = [
  { value: 'private', label: 'Private' },
  { value: 'shared', label: 'Shared' },
  { value: 'public', label: 'Public' }
]

export default function CreateMemoryPage() {
  const [formData, setFormData] = useState<MemoryFormData>({
    user_id: "",
    type: 'fact',
    title: '',
    content: '',
    tags: [],
    source: '',
    visibility: 'private'
  })
  
  const [newTag, setNewTag] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [userIds, setUserIds] = useState<string[]>([])

  const handleInputChange = (field: keyof MemoryFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setError(null)
    setSuccess(false)
  }

  const addTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }))
      setNewTag('')
    }
  }

  const removeTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.content.trim()) {
      setError('Content is required')
      return
    }
    
    setLoading(true)
    setError(null)
    setSuccess(false)
    
    try {
      const response = await fetch('http://localhost:8000/memories/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      setSuccess(true)
      
      setFormData(prev => ({
        ...prev,
        title: '',
        content: '',
        tags: [],
        source: ''
      }))
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const res = await fetch('http://localhost:8000/memories/users')
        const data = await res.json()
        setUserIds(data.user_ids || [])
      } catch (_) {}
    }
    loadUsers()
  }, [])

  const getTypeColor = (type: string) => {
    const typeConfig = MEMORY_TYPES.find(t => t.value === type)
    return typeConfig?.color || '#6b7280'
  }

  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <Link href="/memories" style={{ 
          color: '#6b7280', 
          textDecoration: 'none', 
          marginRight: 16,
          fontSize: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 4
        }}>
          <ArrowLeft className="w-4 h-4" />
          Back to Memories
        </Link>
        <h1 style={{ margin: 0, color: '#1f2937', display: 'flex', alignItems: 'center', gap: 12 }}>
          <Plus className="w-6 h-6" />
          Create New Memory
        </h1>
      </div>

      <form onSubmit={handleSubmit} style={{
        backgroundColor: 'white',
        padding: 24,
        borderRadius: 12,
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ marginBottom: 20 }}>
          <label style={{ 
            display: 'block', 
            marginBottom: 8, 
            fontWeight: 500, 
            color: '#374151',
            fontSize: 14
          }}>
            User ID
          </label>
          <select
            value={formData.user_id}
            onChange={e => handleInputChange('user_id', e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 14,
              backgroundColor: 'white'
            }}
            required
          >
            <option value="">Select a user…</option>
            {userIds.map(id => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: 8, 
              fontWeight: 500, 
              color: '#374151',
              fontSize: 14,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}>
              <Type className="w-4 h-4" />
              Memory Type
            </label>
            <select
              value={formData.type}
              onChange={e => handleInputChange('type', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14,
                backgroundColor: 'white'
              }}
            >
              {MEMORY_TYPES.map(type => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: 8, 
              fontWeight: 500, 
              color: '#374151',
              fontSize: 14,
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}>
              <Eye className="w-4 h-4" />
              Visibility
            </label>
            <select
              value={formData.visibility}
              onChange={e => handleInputChange('visibility', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14,
                backgroundColor: 'white'
              }}
            >
              {VISIBILITY_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ 
            display: 'block', 
            marginBottom: 8, 
            fontWeight: 500, 
            color: '#374151',
            fontSize: 14
          }}>
            Title (Optional)
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={e => handleInputChange('title', e.target.value)}
            placeholder="Enter a title for this memory"
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 14
            }}
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ 
            display: 'block', 
            marginBottom: 8, 
            fontWeight: 500, 
            color: '#374151',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}>
            <FileText className="w-4 h-4" />
            Content *
          </label>
          <textarea
            value={formData.content}
            onChange={e => handleInputChange('content', e.target.value)}
            placeholder="Enter the memory content..."
            required
            rows={6}
            style={{
              width: '100%',
              padding: '12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 14,
              fontFamily: 'inherit',
              resize: 'vertical'
            }}
          />
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ 
            display: 'block', 
            marginBottom: 8, 
            fontWeight: 500, 
            color: '#374151',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}>
            <Tag className="w-4 h-4" />
            Tags
          </label>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              value={newTag}
              onChange={e => setNewTag(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Add a tag"
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14
              }}
            />
            <button
              type="button"
              onClick={addTag}
              disabled={!newTag.trim()}
              style={{
                padding: '8px 16px',
                backgroundColor: newTag.trim() ? '#2563eb' : '#9ca3af',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: newTag.trim() ? 'pointer' : 'not-allowed',
                fontSize: 14
              }}
            >
              Add
            </button>
          </div>
          {formData.tags.length > 0 && (
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {formData.tags.map(tag => (
                <span key={tag} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  backgroundColor: '#eff6ff',
                  color: '#1d4ed8',
                  padding: '4px 8px',
                  borderRadius: 6,
                  fontSize: 12,
                  border: '1px solid #bfdbfe'
                }}>
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#1d4ed8',
                      cursor: 'pointer',
                      padding: 0,
                      fontSize: 12
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ 
            display: 'block', 
            marginBottom: 8, 
            fontWeight: 500, 
            color: '#374151',
            fontSize: 14
          }}>
            Source (Optional)
          </label>
          <input
            type="text"
            value={formData.source}
            onChange={e => handleInputChange('source', e.target.value)}
            placeholder="e.g., conversation, document, experience"
            style={{
              width: '100%',
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              fontSize: 14
            }}
          />
        </div>

        {error && (
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            color: '#dc2626', 
            fontSize: 14, 
            marginBottom: 16,
            padding: 12,
            backgroundColor: '#fef2f2',
            borderRadius: 6,
            border: '1px solid #fecaca'
          }}>
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {success && (
          <div style={{ 
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            color: '#059669', 
            fontSize: 14, 
            marginBottom: 16,
            padding: 12,
            backgroundColor: '#f0fdf4',
            borderRadius: 6,
            border: '1px solid #bbf7d0'
          }}>
            <CheckCircle className="w-4 h-4" />
            Memory created successfully! It will be automatically indexed with embeddings, tags, and entities.
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <Link href="/memories" style={{
            padding: '10px 20px',
            backgroundColor: '#f3f4f6',
            color: '#374151',
            textDecoration: 'none',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 500
          }}>
            Cancel
          </Link>
          <button
            type="submit"
            disabled={loading || !formData.content.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 20px',
              backgroundColor: loading ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 500
            }}
          >
            <Save className="w-4 h-4" />
            {loading ? 'Creating...' : 'Create Memory'}
          </button>
        </div>
      </form>
    </main>
  )
}

