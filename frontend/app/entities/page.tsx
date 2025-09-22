"use client";
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  Network, 
  Search, 
  Tag, 
  Link as LinkIcon,
  Database,
  TrendingUp,
  Clock,
  Filter
} from 'lucide-react'

interface EntitySearchResult {
  entity_name: string
  results: Array<{
    id: string
    title: string
    content: string
    confidence: number
    created_at: string
  }>
  count: number
}

interface Memory {
  id: string
  title?: string
  content: string
  type: string
  created_at: string
  recall_count: number
  confidence: number
  tags: string[]
  entity_ids: string[]
  visibility: string
}

export default function EntitiesPage() {
  const [userId, setUserId] = useState("")
  const [userIds, setUserIds] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<EntitySearchResult | null>(null)
  const [memories, setMemories] = useState<Memory[]>([])
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null)

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

  async function searchEntity() {
    if (!searchQuery.trim() || !userId.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const res = await fetch(
        `http://localhost:8000/memories/search-by-entity?entity_name=${encodeURIComponent(searchQuery)}&user_id=${userId}`
      )
      if (!res.ok) throw new Error('Failed to search entities')
      const data = await res.json()
      setSearchResults(data)
      setSelectedEntity(searchQuery)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) loadMemories()
  }, [userId])

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchEntity()
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
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

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#10b981'
    if (confidence >= 0.6) return '#f59e0b'
    return '#ef4444'
  }

  const extractEntities = () => {
    const entityMap = new Map<string, number>()
    
    memories.forEach(memory => {
      const words = memory.content.toLowerCase().split(/\s+/)
      const techTerms = ['python', 'javascript', 'react', 'node.js', 'docker', 'aws', 'postgresql', 'redis', 'fastapi', 'mongodb']
      
      techTerms.forEach(term => {
        if (words.some(word => word.includes(term))) {
          entityMap.set(term, (entityMap.get(term) || 0) + 1)
        }
      })
    })
    
    return Array.from(entityMap.entries())
      .map(([entity, count]) => ({ entity, count }))
      .sort((a, b) => b.count - a.count)
  }

  const entities = extractEntities()

  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24 }}>
        <Link href="/" style={{ 
          color: '#6b7280', 
          textDecoration: 'none', 
          marginRight: 16,
          fontSize: 14
        }}>
          ← Back to Home
        </Link>
        <h1 style={{ margin: 0, color: '#1f2937', display: 'flex', alignItems: 'center', gap: 12 }}>
          <Network className="w-6 h-6" />
          Entity Explorer
        </h1>
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
          <span style={{ color: '#6b7280', fontSize: 14 }}>
            Explore entities and relationships in your memories
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div style={{
          backgroundColor: 'white',
          padding: 20,
          borderRadius: 12,
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h3 style={{ 
            margin: '0 0 16px 0', 
            fontSize: 16, 
            fontWeight: 600, 
            color: '#1f2937',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <Search className="w-4 h-4" />
            Search by Entity
          </h3>
          
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Enter entity name (e.g., Python, React, Docker)"
              style={{
                flex: 1,
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14
              }}
            />
            <button
              onClick={searchEntity}
              disabled={loading || !searchQuery.trim() || !userId.trim()}
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
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {error && (
            <div style={{ 
              color: '#dc2626', 
              fontSize: 14, 
              marginBottom: 16,
              padding: 8,
              backgroundColor: '#fef2f2',
              borderRadius: 4,
              border: '1px solid #fecaca'
            }}>
              Error: {error}
            </div>
          )}

          {searchResults && (
            <div style={{ marginTop: 16 }}>
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: 12
              }}>
                <h4 style={{ margin: 0, fontSize: 14, fontWeight: 500, color: '#374151' }}>
                  Results for "{searchResults.entity_name}"
                </h4>
                <span style={{ 
                  fontSize: 12, 
                  color: '#6b7280',
                  backgroundColor: '#f3f4f6',
                  padding: '2px 8px',
                  borderRadius: 12
                }}>
                  {searchResults.count} memories
                </span>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {searchResults.results.map((memory, index) => (
                  <div key={memory.id} style={{
                    padding: '12px',
                    backgroundColor: '#f8fafc',
                    borderRadius: 6,
                    border: '1px solid #e2e8f0'
                  }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#1f2937', marginBottom: 4 }}>
                      {memory.title || '(Untitled)'}
                    </div>
                    <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
                      {memory.content.substring(0, 100)}...
                    </div>
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      fontSize: 11,
                      color: '#6b7280'
                    }}>
                      <span>Created {formatDate(memory.created_at)}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          backgroundColor: getConfidenceColor(memory.confidence)
                        }} />
                        <span>Confidence: {Math.round(memory.confidence * 100)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{
          backgroundColor: 'white',
          padding: 20,
          borderRadius: 12,
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h3 style={{ 
            margin: '0 0 16px 0', 
            fontSize: 16, 
            fontWeight: 600, 
            color: '#1f2937',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <Database className="w-4 h-4" />
            Detected Entities
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {entities.map(({ entity, count }, index) => (
              <div 
                key={entity}
                onClick={() => {
                  setSearchQuery(entity)
                  searchEntity()
                }}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: selectedEntity === entity ? '#eff6ff' : '#f8fafc',
                  borderRadius: 6,
                  border: selectedEntity === entity ? '1px solid #3b82f6' : '1px solid #e2e8f0',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag className="w-3 h-3" style={{ color: '#6b7280' }} />
                  <span style={{ 
                    fontSize: 14, 
                    fontWeight: 500, 
                    color: '#1f2937',
                    textTransform: 'capitalize'
                  }}>
                    {entity}
                  </span>
                </div>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 8,
                  fontSize: 12,
                  color: '#6b7280'
                }}>
                  <TrendingUp className="w-3 h-3" />
                  <span>{count} memories</span>
                </div>
              </div>
            ))}
          </div>
          
          {entities.length === 0 && (
            <div style={{ 
              textAlign: 'center', 
              padding: 24, 
              color: '#6b7280',
              fontSize: 14
            }}>
              No entities detected in memories
            </div>
          )}
        </div>
      </div>

      {memories.length > 0 && (
        <div style={{
          backgroundColor: 'white',
          padding: 20,
          borderRadius: 12,
          border: '1px solid #e5e7eb',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          marginTop: 24
        }}>
          <h3 style={{ 
            margin: '0 0 16px 0', 
            fontSize: 16, 
            fontWeight: 600, 
            color: '#1f2937',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <LinkIcon className="w-4 h-4" />
            All Memories with Entity Links
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {memories.map((memory) => (
              <div key={memory.id} style={{
                padding: '16px',
                backgroundColor: '#f8fafc',
                borderRadius: 8,
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ 
                      margin: '0 0 4px 0', 
                      fontSize: 14, 
                      fontWeight: 500, 
                      color: '#1f2937'
                    }}>
                      {memory.title || '(Untitled Memory)'}
                    </h4>
                    <div style={{ 
                      display: 'flex', 
                      gap: 12, 
                      alignItems: 'center', 
                      marginBottom: 8,
                      fontSize: 12,
                      color: '#6b7280'
                    }}>
                      <span style={{
                        backgroundColor: getTypeColor(memory.type),
                        color: 'white',
                        padding: '2px 6px',
                        borderRadius: 8,
                        fontSize: 10,
                        fontWeight: 500
                      }}>
                        {memory.type}
                      </span>
                      <span>Created {formatDate(memory.created_at)}</span>
                      <span>Recalled {memory.recall_count} times</span>
                      <span>Confidence: {Math.round(memory.confidence * 100)}%</span>
                    </div>
                  </div>
                </div>
                
                <div style={{ 
                  color: '#374151', 
                  lineHeight: 1.5,
                  marginBottom: 8,
                  fontSize: 13
                }}>
                  {memory.content}
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {memory.tags && memory.tags.map(tag => (
                      <span key={tag} style={{
                        backgroundColor: '#e5e7eb',
                        color: '#374151',
                        padding: '2px 6px',
                        borderRadius: 4,
                        fontSize: 10
                      }}>
                        #{tag}
                      </span>
                    ))}
                  </div>
                  <div style={{ 
                    fontSize: 11, 
                    color: '#6b7280',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}>
                    <LinkIcon className="w-3 h-3" />
                    {memory.entity_ids?.length || 0} entities
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  )
}

