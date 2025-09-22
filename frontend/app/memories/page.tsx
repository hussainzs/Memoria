"use client";
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Trash2, AlertTriangle } from 'lucide-react'

interface Memory {
  id: string
  title?: string
  content: string
  type: string
  created_at: string
  recall_count: number
  confidence: number
  tags: string[]
  visibility: string
}

export default function Memories() {
  const [userId, setUserId] = useState("")
  const [userIds, setUserIds] = useState<string[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  async function loadMemories() {
    if (!userId.trim()) return
    
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`http://localhost:8000/memories/?user_id=${userId}`)
      if (!res.ok) throw new Error('Failed to fetch memories')
      const data = await res.json()
      setMemories(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  async function deleteMemory(memoryId: string) {
    setDeletingId(memoryId)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/memories/${memoryId}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        throw new Error('Failed to delete memory')
      }
      
      setMemories(prev => prev.filter(m => m.id !== memoryId))
      setDeleteConfirm(null)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setDeletingId(null)
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

  useEffect(() => {
    if (userId) loadMemories()
  }, [userId])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      fact: '#3b82f6',
      event: '#10b981',
      preference: '#f59e0b',
      entity: '#8b5cf6',
      media: '#ef4444',
      skill: '#06b6d4',
      instruction: '#84cc16'
    }
    return colors[type] || '#6b7280'
  }

  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif', maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <Link href="/" style={{ 
          color: '#6b7280', 
          textDecoration: 'none', 
          marginRight: 16,
          fontSize: 14
        }}>
          ← Back to Home
        </Link>
        <h1 style={{ margin: 0, color: '#1f2937' }}>Memories</h1>
      </div>

      <div style={{ 
        backgroundColor: '#f9fafb', 
        padding: 16, 
        borderRadius: 8, 
        marginBottom: 24,
        border: '1px solid #e5e7eb'
      }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <select 
            value={userId}
            onChange={e => setUserId(e.target.value)}
            style={{ 
              padding: '8px 12px', 
              border: '1px solid #d1d5db', 
              borderRadius: 6,
              minWidth: 320,
              fontSize: 14,
              backgroundColor: 'white'
            }}
          >
            <option value="">Select a user…</option>
            {userIds.map(id => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
          <button 
            onClick={loadMemories}
            disabled={loading || !userId.trim()}
            style={{
              padding: '8px 16px',
              backgroundColor: loading ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 14
            }}
          >
            {loading ? 'Loading...' : 'Load Memories'}
          </button>
        </div>
        {error && (
          <div style={{ 
            color: '#dc2626', 
            fontSize: 14, 
            marginTop: 8,
            padding: 8,
            backgroundColor: '#fef2f2',
            borderRadius: 4,
            border: '1px solid #fecaca'
          }}>
            Error: {error}
          </div>
        )}
      </div>

      {memories.length === 0 && !loading && (
        <div style={{ 
          textAlign: 'center', 
          padding: 48, 
          color: '#6b7280',
          backgroundColor: '#f9fafb',
          borderRadius: 8,
          border: '1px solid #e5e7eb'
        }}>
          <p style={{ fontSize: 16, margin: 0 }}>No memories found for this user.</p>
          <p style={{ fontSize: 14, margin: '8px 0 0 0' }}>
            Try loading memories or check if the user ID is correct.
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gap: 16 }}>
        {memories.map(memory => (
          <div key={memory.id} style={{
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            padding: 20,
            backgroundColor: 'white',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ 
                  margin: '0 0 8px 0', 
                  color: '#1f2937',
                  fontSize: 18
                }}>
                  {memory.title || '(Untitled Memory)'}
                </h3>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
                  <span style={{
                    backgroundColor: getTypeColor(memory.type),
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 500
                  }}>
                    {memory.type}
                  </span>
                  <span style={{ color: '#6b7280', fontSize: 12 }}>
                    {formatDate(memory.created_at)}
                  </span>
                  <span style={{ color: '#6b7280', fontSize: 12 }}>
                    Recalled {memory.recall_count} times
                  </span>
                  <span style={{ color: '#6b7280', fontSize: 12 }}>
                    Confidence: {Math.round(memory.confidence * 100)}%
                  </span>
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {deleteConfirm === memory.id ? (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <button
                      onClick={() => deleteMemory(memory.id)}
                      disabled={deletingId === memory.id}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#dc2626',
                        color: 'white',
                        border: 'none',
                        borderRadius: 6,
                        cursor: deletingId === memory.id ? 'not-allowed' : 'pointer',
                        fontSize: 12,
                        fontWeight: 500,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                    >
                      {deletingId === memory.id ? (
                        <>
                          <div style={{ 
                            width: 12, 
                            height: 12, 
                            border: '2px solid transparent',
                            borderTop: '2px solid white',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite'
                          }} />
                          Deleting...
                        </>
                      ) : (
                        <>
                          <Trash2 className="w-3 h-3" />
                          Confirm Delete
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#6b7280',
                        color: 'white',
                        border: 'none',
                        borderRadius: 6,
                        cursor: 'pointer',
                        fontSize: 12
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(memory.id)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#f3f4f6',
                      color: '#dc2626',
                      border: '1px solid #e5e7eb',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontSize: 12,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4
                    }}
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                )}
              </div>
            </div>
            
            <div style={{ 
              color: '#374151', 
              lineHeight: 1.6,
              marginBottom: 12
            }}>
              {memory.content}
            </div>
            
            {memory.tags && memory.tags.length > 0 && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {memory.tags.map(tag => (
                  <span key={tag} style={{
                    backgroundColor: '#f3f4f6',
                    color: '#374151',
                    padding: '2px 6px',
                    borderRadius: 4,
                    fontSize: 11
                  }}>
                    #{tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </main>
  )
}


