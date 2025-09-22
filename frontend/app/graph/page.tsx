"use client";
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

interface GraphNode {
  id: string;
  label: string;
  title: string;
  content: string;
  type: string;
  created_at: string;
  recall_count: number;
  confidence: number;
  tags: string[];
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  created_at: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  count: number;
}

export default function GraphPage() {
  const [userId, setUserId] = useState("");
  const [userIds, setUserIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const networkRef = useRef<HTMLDivElement>(null);
  const networkInstance = useRef<Network | null>(null);

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      fact: '#3b82f6',
      event: '#10b981',
      preference: '#f59e0b',
      entity: '#8b5cf6',
      media: '#ef4444',
      skill: '#06b6d4',
      instruction: '#84cc16'
    };
    return colors[type] || '#6b7280';
  };

  async function loadGraphData() {
    if (!userId.trim()) return;
    
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/memories/graph?user_id=${userId}&limit=100`);
      if (!res.ok) throw new Error('Failed to fetch graph data');
      const data = await res.json();
      setGraphData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const loadUsers = async () => {
      try {
        const res = await fetch('http://localhost:8000/memories/users');
        const data = await res.json();
        setUserIds(data.user_ids || []);
      } catch (_) {}
    };
    loadUsers();
  }, []);

  useEffect(() => {
    if (graphData && networkRef.current) {
      const nodes = new DataSet(
        graphData.nodes.map(node => ({
          id: node.id,
          label: node.label,
          title: `${node.title || 'Untitled'}\nType: ${node.type}\nConfidence: ${Math.round(node.confidence * 100)}%\nRecalls: ${node.recall_count}`,
          color: {
            background: getTypeColor(node.type),
            border: getTypeColor(node.type),
            highlight: {
              background: getTypeColor(node.type),
              border: '#000000'
            }
          },
          size: Math.max(10, Math.min(30, 10 + node.recall_count * 2)),
          font: {
            color: '#111827',
            size: 12
          }
        }))
      );

      const edges = new DataSet(
        graphData.edges.map(edge => ({
          id: edge.id,
          from: edge.source,
          to: edge.target,
          label: edge.relation || '',
          color: {
            color: '#94a3b8',
            highlight: '#3b82f6'
          },
          width: 2
        }))
      );

      const options = {
        nodes: {
          shape: 'dot',
          scaling: {
            min: 10,
            max: 30
          }
        },
        edges: {
          smooth: {
            type: 'continuous'
          }
        },
        physics: {
          enabled: true,
          stabilization: { iterations: 100 },
          barnesHut: {
            gravitationalConstant: -2000,
            centralGravity: 0.1,
            springLength: 95,
            springConstant: 0.04,
            damping: 0.09
          }
        },
        interaction: {
          hover: true,
          selectConnectedEdges: false
        }
      };

      const data = { nodes, edges };
      const network = new Network(networkRef.current, data, options);
      networkInstance.current = network;

      network.on('selectNode', (params) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const node = graphData.nodes.find(n => n.id === nodeId);
          setSelectedNode(node || null);
        }
      });

      network.on('deselectNode', () => {
        setSelectedNode(null);
      });

      return () => {
        if (networkInstance.current) {
          networkInstance.current.destroy();
          networkInstance.current = null;
        }
      };
    }
  }, [graphData]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

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
        <h1 style={{ margin: 0, color: '#1f2937' }}>Memory Graph</h1>
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
            onClick={loadGraphData}
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
            {loading ? 'Loading...' : 'Load Graph'}
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

      {graphData && graphData.count === 0 && !loading && (
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
            Create some memories first to see the graph visualization.
          </p>
        </div>
      )}

      {graphData && graphData.count > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24 }}>
          {/* Graph Visualization */}
          <div style={{ 
            border: '1px solid #e5e7eb', 
            borderRadius: 8, 
            backgroundColor: 'white',
            minHeight: '600px',
            position: 'relative'
          }}>
            <div 
              ref={networkRef} 
              style={{ 
                width: '100%', 
                height: '600px',
                borderRadius: 8
              }} 
            />
            
            {/* Graph Info Overlay */}
            <div style={{
              position: 'absolute',
              top: 12,
              right: 12,
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 12,
              color: '#374151',
              border: '1px solid #e5e7eb'
            }}>
              <div>Nodes: {graphData.nodes.length}</div>
              <div>Edges: {graphData.edges.length}</div>
            </div>
          </div>

          {/* Node Details Panel */}
          <div style={{ 
            border: '1px solid #e5e7eb', 
            borderRadius: 8, 
            padding: 20,
            backgroundColor: 'white',
            height: 'fit-content'
          }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#1f2937' }}>Memory Details</h3>
            
            {selectedNode ? (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ 
                    margin: '0 0 8px 0', 
                    color: '#1f2937',
                    fontSize: 16
                  }}>
                    {selectedNode.title || '(Untitled Memory)'}
                  </h4>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
                    <span style={{
                      backgroundColor: getTypeColor(selectedNode.type),
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 500
                    }}>
                      {selectedNode.type}
                    </span>
                    <span style={{ color: '#6b7280', fontSize: 12 }}>
                      {formatDate(selectedNode.created_at)}
                    </span>
                  </div>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <h5 style={{ margin: '0 0 8px 0', color: '#374151', fontSize: 14 }}>Content:</h5>
                  <p style={{ 
                    color: '#6b7280', 
                    fontSize: 13, 
                    lineHeight: 1.5,
                    margin: 0,
                    maxHeight: '120px',
                    overflow: 'auto'
                  }}>
                    {selectedNode.content}
                  </p>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <h5 style={{ margin: '0 0 8px 0', color: '#374151', fontSize: 14 }}>Metadata:</h5>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>
                    <div>Recalls: {selectedNode.recall_count}</div>
                    <div>Confidence: {Math.round(selectedNode.confidence * 100)}%</div>
                  </div>
                </div>

                {selectedNode.tags && selectedNode.tags.length > 0 && (
                  <div>
                    <h5 style={{ margin: '0 0 8px 0', color: '#374151', fontSize: 14 }}>Tags:</h5>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {selectedNode.tags.map(tag => (
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
                  </div>
                )}
              </div>
            ) : (
              <div style={{ 
                textAlign: 'center', 
                color: '#6b7280',
                padding: 20
              }}>
                <p style={{ margin: 0, fontSize: 14 }}>
                  Click on a memory node to view details
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Legend */}
      {graphData && graphData.count > 0 && (
        <div style={{ 
          marginTop: 24,
          padding: 16,
          backgroundColor: '#f9fafb',
          borderRadius: 8,
          border: '1px solid #e5e7eb'
        }}>
          <h4 style={{ margin: '0 0 12px 0', color: '#374151' }}>Legend</h4>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {['fact', 'event', 'preference', 'entity', 'media', 'skill', 'instruction'].map(type => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: getTypeColor(type)
                }} />
                <span style={{ fontSize: 12, color: '#6b7280', textTransform: 'capitalize' }}>
                  {type}
                </span>
              </div>
            ))}
          </div>
          <p style={{ 
            margin: '8px 0 0 0', 
            fontSize: 12, 
            color: '#6b7280' 
          }}>
            Node size indicates recall frequency. Larger nodes have been recalled more often.
          </p>
        </div>
      )}
    </main>
  );
}
