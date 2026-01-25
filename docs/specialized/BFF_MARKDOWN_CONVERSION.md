# BFF Markdown Conversion Implementation Guide

## Overview

This document describes how the Node.js BFF layer should handle structured data from the Python backend and convert it to markdown for the React frontend.

## Architecture

```
Python Backend → Node.js BFF → React Frontend
     ↓              ↓              ↓
Structured      Markdown      Renders
Arrays          Conversion    Markdown
```

## Python Backend Changes (Completed)

The Python backend now returns structured data in token events:

```json
{
  "event": "token",
  "channel": "final",
  "content": "There are",
  "structured_data": [
    {"id": 1, "name": "John", "count": 10},
    {"id": 2, "name": "Jane", "count": 5}
  ]
}
```

**Key Points:**
- `structured_data` is included in the **first token** of the `final` channel only
- If `structured_data` is present, the BFF should convert it to markdown
- If `structured_data` is `null`, use `content` as-is (backward compatible)

## Node.js BFF Implementation

### 1. Create Markdown Formatter Utility

**File**: `utils/markdownFormatter.js`

```javascript
/**
 * Formats SQL query results (structured arrays) as markdown
 */
function formatSQLResult(structuredData) {
  if (!structuredData || !Array.isArray(structuredData)) {
    return null; // No structured data, use raw content
  }
  
  if (structuredData.length === 0) {
    return "No results found.";
  }
  
  // Check if it's a table (array of objects)
  if (typeof structuredData[0] === 'object' && structuredData[0] !== null) {
    return formatAsTable(structuredData);
  }
  
  // Simple list
  return formatAsList(structuredData);
}

function formatAsTable(rows) {
  if (rows.length === 0) {
    return "No results found.";
  }
  
  // Get all unique keys (columns)
  const allKeys = new Set();
  rows.forEach(row => {
    Object.keys(row).forEach(key => allKeys.add(key));
  });
  
  const columns = Array.from(allKeys).sort();
  
  // Build markdown table
  const lines = [];
  
  // Header
  lines.push('| ' + columns.join(' | ') + ' |');
  
  // Separator
  lines.push('| ' + columns.map(() => '---').join(' | ') + ' |');
  
  // Rows (limit to 100 for readability)
  const maxRows = 100;
  rows.slice(0, maxRows).forEach(row => {
    const values = columns.map(col => {
      const value = row[col];
      if (value === null || value === undefined) {
        return '';
      }
      const str = String(value);
      // Truncate long values
      return str.length > 50 ? str.substring(0, 47) + '...' : str;
    });
    lines.push('| ' + values.join(' | ') + ' |');
  });
  
  // Add row count if truncated
  if (rows.length > maxRows) {
    lines.push(`\n*Showing ${maxRows} of ${rows.length} rows*`);
  }
  
  return lines.join('\n');
}

function formatAsList(items) {
  if (items.length === 0) {
    return "No results found.";
  }
  
  // Filter out null/undefined
  const validItems = items.filter(item => item != null);
  
  if (validItems.length === 0) {
    return "No results found.";
  }
  
  // If single item, return as simple text
  if (validItems.length === 1) {
    return String(validItems[0]);
  }
  
  // Format as markdown list
  const lines = validItems.slice(0, 100).map(item => `- ${String(item)}`);
  
  if (validItems.length > 100) {
    lines.push(`\n*Showing 100 of ${validItems.length} items*`);
  }
  
  return lines.join('\n');
}

module.exports = {
  formatSQLResult,
  formatAsTable,
  formatAsList
};
```

### 2. Update SSE Handler

**File**: `routes/chat.js` (or wherever SSE is handled)

```javascript
const { formatSQLResult } = require('../utils/markdownFormatter');

// When receiving token events from Python backend
async function handlePythonSSE(req, res) {
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
  
  for await (const line of pythonResponse.body) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.substring(6));
      
      if (event.event === 'token' && event.channel === 'final') {
        // Check if structured_data is present
        if (event.structured_data) {
          // Convert structured array to markdown
          const markdown = formatSQLResult(event.structured_data);
          
          if (markdown) {
            // Stream markdown to React frontend
            // Option 1: Replace content with markdown
            res.sse({
              event: 'token',
              channel: 'final',
              content: markdown,
              type: 'final_answer'
            });
            continue; // Skip streaming the raw content tokens
          }
        }
        
        // Fallback: stream raw content (backward compatible)
        res.sse({
          event: 'token',
          channel: 'final',
          content: event.content,
          type: 'final_answer'
        });
      } else {
        // Pass through other events as-is
        res.sse(event);
      }
    }
  }
}
```

### 3. Alternative: Stream Markdown Once, Then Content

If you want to stream markdown first, then continue with content:

```javascript
let markdownSent = false;

if (event.event === 'token' && event.channel === 'final') {
  if (event.structured_data && !markdownSent) {
    const markdown = formatSQLResult(event.structured_data);
    if (markdown) {
      // Send markdown as a complete message
      res.sse({
        event: 'message',
        channel: 'final',
        content: markdown,
        type: 'final_answer',
        complete: true
      });
      markdownSent = true;
      continue; // Don't stream individual tokens
    }
  }
  
  // Continue streaming tokens if no structured_data
  res.sse({
    event: 'token',
    channel: 'final',
    content: event.content,
    type: 'final_answer'
  });
}
```

## React Frontend

The React frontend should already support markdown rendering. Ensure:

1. Markdown renderer is configured (e.g., `react-markdown` or similar)
2. Token events with `channel: "final"` are rendered as markdown
3. Tables, lists, and other markdown elements are styled appropriately

## Testing

### Test Cases

1. **Table Result** (array of objects):
   ```json
   {
     "structured_data": [
       {"id": 1, "name": "John", "count": 10},
       {"id": 2, "name": "Jane", "count": 5}
     ]
   }
   ```
   Expected: Markdown table with 3 columns, 2 rows

2. **List Result** (array of primitives):
   ```json
   {
     "structured_data": ["Item 1", "Item 2", "Item 3"]
   }
   ```
   Expected: Markdown list with 3 items

3. **Single Value**:
   ```json
   {
     "structured_data": [{"count": 42}]
   }
   ```
   Expected: Markdown table or formatted value

4. **Empty Array**:
   ```json
   {
     "structured_data": []
   }
   ```
   Expected: "No results found."

5. **No Structured Data** (backward compatible):
   ```json
   {
     "content": "There are 10 technicians"
   }
   ```
   Expected: Stream content as-is

## Benefits

1. **Separation of Concerns**: Python returns structured data, BFF handles presentation
2. **Flexibility**: BFF can adapt formatting per client type
3. **Reusability**: Python backend remains generic
4. **Backward Compatible**: Falls back to raw content if no structured_data

## Migration Notes

- Python backend now always includes `structured_data` when available
- BFF should check for `structured_data` first, then fall back to `content`
- React frontend doesn't need changes (just renders markdown)
