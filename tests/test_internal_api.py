"""
Test script for the internal API

This demonstrates how Node.js should call the Python FastAPI service.
"""

import requests
import json
import sys

# API endpoint
BASE_URL = "http://localhost:8000"
STREAM_URL = f"{BASE_URL}/internal/chat/stream"
HEALTH_URL = f"{BASE_URL}/health"


def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("Testing Health Endpoint")
    print("="*60)
    
    response = requests.get(HEALTH_URL)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    print("✅ Health check passed")


def test_stream(message: str):
    """Test streaming endpoint with new internal API contract"""
    print("\n" + "="*60)
    print("Testing Stream Endpoint (Internal API)")
    print("="*60)
    
    # This is how Node.js will call the Python service
    request_payload = {
        "input": {
            "message": message
        },
        "conversation": {
            "id": "conv-test-123",
            "user_id": "user-456",
            "company_id": "company-789"
        }
    }
    
    print(f"\nRequest payload:")
    print(json.dumps(request_payload, indent=2))
    print(f"\nMessage: {message}")
    print("\nStreaming events:\n")
    
    # Stream the response
    response = requests.post(
        STREAM_URL,
        json=request_payload,
        headers={"Content-Type": "application/json"},
        stream=True
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return
    
    # Parse SSE events
    event_count = 0
    for line in response.iter_lines(decode_unicode=True):
        if line.startswith("data: "):
            event_count += 1
            data = json.loads(line[6:])  # Remove "data: " prefix
            
            event_type = data.get("event")
            
            # Display events in a readable format
            if event_type == "route_decision":
                print(f"\n📍 Route: {data['route'].upper()}")
            
            elif event_type == "tool_start":
                tool = data['tool']
                print(f"\n🔧 Tool: {tool}")
            
            elif event_type == "token":
                channel = data.get('channel', 'unknown')
                content = data.get('content', '')
                
                # Only show final answer tokens
                if channel == "final":
                    print(content, end='', flush=True)
            
            elif event_type == "complete":
                stats = data.get('stats', {})
                print(f"\n\n✅ Complete - {stats.get('tokens', 0)} tokens")
            
            elif event_type == "error":
                print(f"\n❌ Error: {data.get('error')}")
    
    print(f"\n\nTotal events received: {event_count}")


def demo_node_mapping():
    """
    Show how Node.js would map semantic events to UI concepts
    """
    print("\n" + "="*60)
    print("Node.js Mapping Example (Pseudo-code)")
    print("="*60)
    
    example_code = """
// Node.js BFF layer maps semantic events to UI
async function streamToFrontend(req, res) {
  const pythonResponse = await fetch('http://python:8000/internal/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
      input: { message: req.body.message },
      conversation: {
        id: req.session.conversationId,
        user_id: req.user.id,
        company_id: req.user.companyId
      }
    })
  });
  
  for await (const event of pythonResponse.events) {
    // Map semantic events to UI tokens
    if (event.event === 'tool_start') {
      if (event.tool === 'sql_agent') {
        res.sse({ token: '🔍 Querying database', type: 'tool_call' });
      } else if (event.tool === 'rag_agent') {
        res.sse({ token: '📚 Searching knowledge base', type: 'tool_call' });
      }
    }
    
    else if (event.event === 'token') {
      if (event.channel === 'final') {
        res.sse({ token: event.content, type: 'final_answer' });
      } else {
        res.sse({ token: event.content, type: 'reasoning' });
      }
    }
    
    else if (event.event === 'complete') {
      res.sse({ done: true, metadata: event.stats });
    }
  }
}
"""
    print(example_code)


if __name__ == "__main__":
    # Test questions
    test_questions = [
        "How many technicians are active?",
        "What are the overtime rules?",
    ]
    
    # Run tests
    test_health()
    
    for question in test_questions:
        test_stream(question)
    
    demo_node_mapping()
    
    print("\n" + "="*60)
    print("✅ All tests completed")
    print("="*60)
