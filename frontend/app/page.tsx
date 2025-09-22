"use client";
import useSWR from 'swr'
import Link from 'next/link'

const fetcher = (url: string) => fetch(url).then(r => r.json())

export default function Home() {
  const { data } = useSWR('/api/health', fetcher)
  return (
    <main style={{ padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ color: '#2563eb', marginBottom: 24 }}>Memoria</h1>
      <p style={{ marginBottom: 24 }}>
        Long-term memory database for LLMs. Backend status: 
        <span style={{ 
          color: data?.status === 'ok' ? '#16a34a' : '#dc2626',
          fontWeight: 'bold',
          marginLeft: 8
        }}>
          {data?.status ?? 'unknown'}
        </span>
      </p>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: 16,
        marginTop: 32
      }}>
        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: 8, 
          padding: 16,
          backgroundColor: '#f9fafb'
        }}>
          <h3 style={{ marginTop: 0, color: '#374151' }}>View Memories</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            Browse and manage your stored memories
          </p>
          <Link href="/memories" style={{
            display: 'inline-block',
            backgroundColor: '#2563eb',
            color: 'white',
            padding: '8px 16px',
            borderRadius: 6,
            textDecoration: 'none',
            fontSize: 14
          }}>
            Go to Memories →
          </Link>
        </div>
        
        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: 8, 
          padding: 16,
          backgroundColor: '#f9fafb'
        }}>
          <h3 style={{ marginTop: 0, color: '#374151' }}>Ask Questions</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            Ask intelligent questions about your memories
          </p>
          <Link href="/ask" style={{
            display: 'inline-block',
            backgroundColor: '#10b981',
            color: 'white',
            padding: '8px 16px',
            borderRadius: 6,
            textDecoration: 'none',
            fontSize: 14
          }}>
            Ask Memoria →
          </Link>
        </div>

        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: 8, 
          padding: 16,
          backgroundColor: '#f9fafb'
        }}>
          <h3 style={{ marginTop: 0, color: '#374151' }}>Create Memory</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            Add new memories to your database
          </p>
          <Link href="/memories/create" style={{
            display: 'inline-block',
            backgroundColor: '#f59e0b',
            color: 'white',
            padding: '8px 16px',
            borderRadius: 6,
            textDecoration: 'none',
            fontSize: 14
          }}>
            Create Memory →
          </Link>
        </div>

        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: 8, 
          padding: 16,
          backgroundColor: '#f9fafb'
        }}>
          <h3 style={{ marginTop: 0, color: '#374151' }}>Entity Explorer</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            Explore entities and relationships
          </p>
          <Link href="/entities" style={{
            display: 'inline-block',
            backgroundColor: '#8b5cf6',
            color: 'white',
            padding: '8px 16px',
            borderRadius: 6,
            textDecoration: 'none',
            fontSize: 14
          }}>
            Explore Entities →
          </Link>
        </div>

                <div style={{ 
                  border: '1px solid #e5e7eb', 
                  borderRadius: 8, 
                  padding: 16,
                  backgroundColor: '#f9fafb'
                }}>
                  <h3 style={{ marginTop: 0, color: '#374151' }}>Analytics</h3>
                  <p style={{ color: '#6b7280', fontSize: 14 }}>
                    View memory insights and patterns
                  </p>
                  <Link href="/analytics" style={{
                    display: 'inline-block',
                    backgroundColor: '#06b6d4',
                    color: 'white',
                    padding: '8px 16px',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 14
                  }}>
                    View Analytics →
                  </Link>
                </div>

                <div style={{ 
                  border: '1px solid #e5e7eb', 
                  borderRadius: 8, 
                  padding: 16,
                  backgroundColor: '#f9fafb'
                }}>
                  <h3 style={{ marginTop: 0, color: '#374151' }}>Memory Graph</h3>
                  <p style={{ color: '#6b7280', fontSize: 14 }}>
                    Visualize memory relationships as an interactive graph
                  </p>
                  <Link href="/graph" style={{
                    display: 'inline-block',
                    backgroundColor: '#7c3aed',
                    color: 'white',
                    padding: '8px 16px',
                    borderRadius: 6,
                    textDecoration: 'none',
                    fontSize: 14
                  }}>
                    View Graph →
                  </Link>
                </div>
        
        <div style={{ 
          border: '1px solid #e5e7eb', 
          borderRadius: 8, 
          padding: 16,
          backgroundColor: '#f9fafb'
        }}>
          <h3 style={{ marginTop: 0, color: '#374151' }}>API Documentation</h3>
          <p style={{ color: '#6b7280', fontSize: 14 }}>
            Explore the REST API endpoints
          </p>
          <a href="http://localhost:8000/docs" target="_blank" style={{
            display: 'inline-block',
            backgroundColor: '#6b7280',
            color: 'white',
            padding: '8px 16px',
            borderRadius: 6,
            textDecoration: 'none',
            fontSize: 14
          }}>
            Open API Docs →
          </a>
        </div>
      </div>
    </main>
  )
}


