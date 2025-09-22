"use client";
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  BarChart3, 
  Brain, 
  Clock, 
  TrendingUp, 
  CheckCircle, 
  AlertTriangle,
  Database,
  Activity,
  Target,
  Zap
} from 'lucide-react'

interface MemoryInsights {
  total_memories: number
  total_recalls: number
  average_recalls_per_memory: number
  memory_types: Record<string, number>
  temporal_distribution: {
    recent_memories_7_days: number
    old_memories_30_days: number
    boosted_memories: number
    decaying_memories: number
  }
  recall_patterns: {
    highly_recalled: number
    never_recalled: number
    recently_recalled: number
  }
}

interface VerificationStats {
  total_memories: number
  average_confidence: number
  confidence_distribution: {
    high_confidence: number
    medium_confidence: number
    low_confidence: number
  }
  memory_types: Record<string, number>
  confidence_by_type: Record<string, number>
}

interface TemporalScore {
  id: string
  title: string
  created_at: string
  last_recalled: string | null
  recall_count: number
  temporal_score: number
  confidence: number
}

export default function AnalyticsPage() {
  const [userId, setUserId] = useState("")
  const [userIds, setUserIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [insights, setInsights] = useState<MemoryInsights | null>(null)
  const [verificationStats, setVerificationStats] = useState<VerificationStats | null>(null)
  const [temporalScores, setTemporalScores] = useState<TemporalScore[]>([])
  const [boostedMemories, setBoostedMemories] = useState<any[]>([])

  async function loadAnalytics() {
    if (!userId.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const insightsRes = await fetch(`http://localhost:8000/temporal/memory-insights?user_id=${userId}`)
      if (insightsRes.ok) {
        const insightsData = await insightsRes.json()
        setInsights(insightsData.insights)
      }

      const verificationRes = await fetch(`http://localhost:8000/verification/verification-stats?user_id=${userId}`)
      if (verificationRes.ok) {
        const verificationData = await verificationRes.json()
        setVerificationStats(verificationData.verification_stats)
      }

      const temporalRes = await fetch(`http://localhost:8000/temporal/temporal-scores?user_id=${userId}&limit=10`)
      if (temporalRes.ok) {
        const temporalData = await temporalRes.json()
        setTemporalScores(temporalData.scored_memories)
      }

      const boostedRes = await fetch(`http://localhost:8000/temporal/boosted-memories?user_id=${userId}&limit=5`)
      if (boostedRes.ok) {
        const boostedData = await boostedRes.json()
        setBoostedMemories(boostedData.boosted_memories)
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (userId) loadAnalytics()
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#10b981'
    if (score >= 0.6) return '#f59e0b'
    return '#ef4444'
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

  const StatCard = ({ title, value, icon: Icon, color = '#2563eb', subtitle }: {
    title: string
    value: string | number
    icon: any
    color?: string
    subtitle?: string
  }) => (
    <div style={{
      backgroundColor: 'white',
      padding: 20,
      borderRadius: 12,
      border: '1px solid #e5e7eb',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500, color: '#6b7280' }}>{title}</h3>
        <Icon style={{ color, width: 20, height: 20 }} />
      </div>
      <div style={{ fontSize: 24, fontWeight: 600, color: '#1f2937', marginBottom: 4 }}>
        {value}
      </div>
      {subtitle && (
        <div style={{ fontSize: 12, color: '#6b7280' }}>{subtitle}</div>
      )}
    </div>
  )

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
          <BarChart3 className="w-6 h-6" />
          Analytics Dashboard
        </h1>
      </div>

      {/* User ID Selector */}
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
            onClick={loadAnalytics}
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
            {loading ? 'Loading...' : 'Load Analytics'}
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

      {loading && (
        <div style={{ textAlign: 'center', padding: 48, color: '#6b7280' }}>
          <div style={{ 
            width: 32, 
            height: 32, 
            border: '3px solid #e5e7eb',
            borderTop: '3px solid #2563eb',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 16px'
          }} />
          Loading analytics...
        </div>
      )}

      {!loading && insights && (
        <>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: 16,
            marginBottom: 32
          }}>
            <StatCard
              title="Total Memories"
              value={insights.total_memories}
              icon={Database}
              color="#3b82f6"
            />
            <StatCard
              title="Total Recalls"
              value={insights.total_recalls}
              icon={Activity}
              color="#10b981"
            />
            <StatCard
              title="Avg Recalls/Memory"
              value={insights.average_recalls_per_memory.toFixed(1)}
              icon={TrendingUp}
              color="#f59e0b"
            />
            <StatCard
              title="Recent Memories"
              value={insights.temporal_distribution.recent_memories_7_days}
              icon={Clock}
              color="#8b5cf6"
              subtitle="Last 7 days"
            />
          </div>

          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
            gap: 24,
            marginBottom: 32
          }}>
            <div style={{
              backgroundColor: 'white',
              padding: 20,
              borderRadius: 12,
              border: '1px solid #e5e7eb',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: 16, fontWeight: 600, color: '#1f2937' }}>
                Memory Types
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(insights.memory_types).map(([type, count]) => (
                  <div key={type} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        backgroundColor: getTypeColor(type)
                      }} />
                      <span style={{ fontSize: 14, color: '#374151', textTransform: 'capitalize' }}>
                        {type}
                      </span>
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 500, color: '#1f2937' }}>
                      {count}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              backgroundColor: 'white',
              padding: 20,
              borderRadius: 12,
              border: '1px solid #e5e7eb',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: 16, fontWeight: 600, color: '#1f2937' }}>
                Recall Patterns
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, color: '#374151' }}>Highly Recalled</span>
                  <span style={{ fontSize: 14, fontWeight: 500, color: '#10b981' }}>
                    {insights.recall_patterns.highly_recalled}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, color: '#374151' }}>Recently Recalled</span>
                  <span style={{ fontSize: 14, fontWeight: 500, color: '#3b82f6' }}>
                    {insights.recall_patterns.recently_recalled}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, color: '#374151' }}>Never Recalled</span>
                  <span style={{ fontSize: 14, fontWeight: 500, color: '#6b7280' }}>
                    {insights.recall_patterns.never_recalled}
                  </span>
                </div>
              </div>
            </div>
          </div>

            
          {verificationStats && (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: 16,
              marginBottom: 32
            }}>
              <StatCard
                title="Avg Confidence"
                value={`${(verificationStats.average_confidence * 100).toFixed(1)}%`}
                icon={Target}
                color="#10b981"
              />
              <StatCard
                title="High Confidence"
                value={verificationStats.confidence_distribution.high_confidence}
                icon={CheckCircle}
                color="#10b981"
              />
              <StatCard
                title="Medium Confidence"
                value={verificationStats.confidence_distribution.medium_confidence}
                icon={AlertTriangle}
                color="#f59e0b"
              />
              <StatCard
                title="Low Confidence"
                value={verificationStats.confidence_distribution.low_confidence}
                icon={AlertTriangle}
                color="#ef4444"
              />
            </div>
          )}

          {temporalScores.length > 0 && (
            <div style={{
              backgroundColor: 'white',
              padding: 20,
              borderRadius: 12,
              border: '1px solid #e5e7eb',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              marginBottom: 32
            }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: 16, fontWeight: 600, color: '#1f2937' }}>
                Top Memories by Temporal Score
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {temporalScores.slice(0, 5).map((memory, index) => (
                  <div key={memory.id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    backgroundColor: '#f8fafc',
                    borderRadius: 6,
                    border: '1px solid #e2e8f0'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, color: '#1f2937', marginBottom: 2 }}>
                        {memory.title || '(Untitled)'}
                      </div>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>
                        Created {formatDate(memory.created_at)} • 
                        Recalled {memory.recall_count} times
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ 
                          fontSize: 12, 
                          color: '#6b7280',
                          marginBottom: 2
                        }}>
                          Temporal Score
                        </div>
                        <div style={{ 
                          fontSize: 14, 
                          fontWeight: 600,
                          color: getScoreColor(memory.temporal_score)
                        }}>
                          {(memory.temporal_score * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: getScoreColor(memory.temporal_score)
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {boostedMemories.length > 0 && (
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
                <Zap className="w-4 h-4" style={{ color: '#f59e0b' }} />
                Recently Boosted Memories
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {boostedMemories.map((memory, index) => (
                  <div key={memory.id} style={{
                    padding: '12px',
                    backgroundColor: '#fffbeb',
                    borderRadius: 6,
                    border: '1px solid #fed7aa'
                  }}>
                    <div style={{ fontSize: 14, fontWeight: 500, color: '#1f2937', marginBottom: 4 }}>
                      {memory.title || '(Untitled)'}
                    </div>
                    <div style={{ fontSize: 12, color: '#92400e', marginBottom: 4 }}>
                      {memory.content.substring(0, 100)}...
                    </div>
                    <div style={{ fontSize: 11, color: '#a16207' }}>
                      Created {formatDate(memory.created_at)} • 
                      {memory.last_recalled ? ` Last recalled ${formatDate(memory.last_recalled)}` : ' Never recalled'} • 
                      Recalled {memory.recall_count} times
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </main>
  )
}

