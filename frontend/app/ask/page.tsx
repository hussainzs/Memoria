"use client";
import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Send, Brain, MessageSquare, Clock, CheckCircle, AlertCircle } from 'lucide-react'

interface AskResponse {
  answer: string
  citations: Array<{
    memory_id: string
    confidence: number
  }>
  verification?: {
    is_verified: boolean
    fact_check_score: number
    citation_score: number
    consistency_score: number
    issues: string[]
    suggestions: string[]
  }
}

interface ChatMessage {
  id: string
  question: string
  response: AskResponse
  timestamp: Date
}

export default function AskPage() {
  const [userId, setUserId] = useState("")
  const [userIds, setUserIds] = useState<string[]>([])
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])

  async function askQuestion() {
    if (!question.trim() || !userId.trim()) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('http://localhost:8000/ask/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          question: question.trim()
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data: AskResponse = await response.json()
      
      const newMessage: ChatMessage = {
        id: Date.now().toString(),
        question: question.trim(),
        response: data,
        timestamp: new Date()
      }
      
      setChatHistory(prev => [newMessage, ...prev])
      setQuestion("")
      
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      askQuestion()
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#10b981' // green
    if (confidence >= 0.6) return '#f59e0b' // yellow
    return '#ef4444' // red
  }

  const getVerificationIcon = (isVerified: boolean) => {
    return isVerified ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <AlertCircle className="w-4 h-4 text-yellow-500" />
    )
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
        <h1 style={{ margin: 0, color: '#1f2937', display: 'flex', alignItems: 'center', gap: 12 }}>
          <Brain className="w-6 h-6" />
          Ask Memoria
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
            Ask questions about your memories
          </span>
        </div>
      </div>

      <div style={{ 
        backgroundColor: 'white', 
        padding: 20, 
        borderRadius: 12, 
        marginBottom: 24,
        border: '1px solid #e5e7eb',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ 
              display: 'block', 
              marginBottom: 8, 
              fontWeight: 500, 
              color: '#374151' 
            }}>
              Your Question
            </label>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask anything about your memories... (e.g., 'What programming languages do I know?', 'Tell me about my coffee preferences')"
              disabled={loading}
              style={{
                width: '100%',
                minHeight: 80,
                padding: '12px',
                border: '1px solid #d1d5db',
                borderRadius: 8,
                fontSize: 14,
                fontFamily: 'inherit',
                resize: 'vertical',
                backgroundColor: loading ? '#f9fafb' : 'white'
              }}
            />
          </div>
          <button 
            onClick={askQuestion}
            disabled={loading || !question.trim() || !userId.trim()}
            style={{
              padding: '12px 20px',
              backgroundColor: loading ? '#9ca3af' : '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 14,
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              minWidth: 120,
              justifyContent: 'center'
            }}
          >
            {loading ? (
              <>
                <div style={{ 
                  width: 16, 
                  height: 16, 
                  border: '2px solid transparent',
                  borderTop: '2px solid white',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
                Asking...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Ask
              </>
            )}
          </button>
        </div>
        
        {error && (
          <div style={{ 
            color: '#dc2626', 
            fontSize: 14, 
            marginTop: 12,
            padding: 12,
            backgroundColor: '#fef2f2',
            borderRadius: 6,
            border: '1px solid #fecaca',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <AlertCircle className="w-4 h-4" />
            Error: {error}
          </div>
        )}
      </div>

      {chatHistory.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ 
            margin: '0 0 16px 0', 
            color: '#374151',
            fontSize: 18,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <MessageSquare className="w-5 h-5" />
            Conversation History
          </h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {chatHistory.map((message) => (
              <div key={message.id} style={{
                backgroundColor: 'white',
                borderRadius: 12,
                border: '1px solid #e5e7eb',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}>
                <div style={{ 
                  padding: '16px 20px', 
                  backgroundColor: '#f8fafc',
                  borderBottom: '1px solid #e5e7eb'
                }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    marginBottom: 8
                  }}>
                    <h3 style={{ 
                      margin: 0, 
                      color: '#1f2937',
                      fontSize: 16,
                      fontWeight: 500
                    }}>
                      {message.question}
                    </h3>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 8,
                      color: '#6b7280',
                      fontSize: 12
                    }}>
                      <Clock className="w-3 h-3" />
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>

                <div style={{ padding: '20px' }}>
                  <div style={{ 
                    color: '#374151', 
                    lineHeight: 1.6,
                    marginBottom: 16,
                    fontSize: 15
                  }}>
                    {message.response.answer}
                  </div>

                  {message.response.verification && (
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 8,
                      marginBottom: 16,
                      padding: '8px 12px',
                      backgroundColor: message.response.verification.is_verified ? '#f0fdf4' : '#fffbeb',
                      borderRadius: 6,
                      border: `1px solid ${message.response.verification.is_verified ? '#bbf7d0' : '#fed7aa'}`
                    }}>
                      {getVerificationIcon(message.response.verification.is_verified)}
                      <span style={{ 
                        fontSize: 12, 
                        fontWeight: 500,
                        color: message.response.verification.is_verified ? '#166534' : '#92400e'
                      }}>
                        {message.response.verification.is_verified ? 'Verified Answer' : 'Limited Verification'}
                      </span>
                      <div style={{ 
                        display: 'flex', 
                        gap: 12, 
                        marginLeft: 'auto',
                        fontSize: 11,
                        color: '#6b7280'
                      }}>
                        <span>Fact Check: {Math.round(message.response.verification.fact_check_score * 100)}%</span>
                        <span>Citations: {Math.round(message.response.verification.citation_score * 100)}%</span>
                        <span>Consistency: {Math.round(message.response.verification.consistency_score * 100)}%</span>
                      </div>
                    </div>
                  )}

                  {message.response.citations && message.response.citations.length > 0 && (
                    <div style={{ 
                      backgroundColor: '#f8fafc',
                      padding: 12,
                      borderRadius: 6,
                      border: '1px solid #e2e8f0'
                    }}>
                      <h4 style={{ 
                        margin: '0 0 8px 0', 
                        fontSize: 13, 
                        fontWeight: 500,
                        color: '#475569'
                      }}>
                        Sources ({message.response.citations.length})
                      </h4>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {message.response.citations.map((citation, index) => (
                          <div key={index} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '4px 8px',
                            backgroundColor: 'white',
                            borderRadius: 4,
                            border: '1px solid #d1d5db',
                            fontSize: 11
                          }}>
                            <span style={{ color: '#6b7280' }}>
                              Memory {index + 1}
                            </span>
                            <div style={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              backgroundColor: getConfidenceColor(citation.confidence)
                            }} />
                            <span style={{ color: '#6b7280' }}>
                              {Math.round(citation.confidence * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {chatHistory.length === 0 && (
        <div style={{ 
          textAlign: 'center', 
          padding: 48, 
          color: '#6b7280',
          backgroundColor: '#f9fafb',
          borderRadius: 12,
          border: '1px solid #e5e7eb'
        }}>
          <Brain className="w-12 h-12 mx-auto mb-4" style={{ color: '#d1d5db' }} />
          <p style={{ fontSize: 16, margin: '0 0 8px 0' }}>Start a conversation with your memories</p>
          <p style={{ fontSize: 14, margin: 0 }}>
            Ask questions about your stored memories and get intelligent answers.
          </p>
        </div>
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

