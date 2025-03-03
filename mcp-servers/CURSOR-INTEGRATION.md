# Perplexity Integration with Cursor

This guide explains how to use the Perplexity API within Cursor IDE's chat interface.

## Table of Contents

1. [Setup](#setup)
2. [Chat Commands](#chat-commands)
3. [Usage Examples](#usage-examples)
4. [Troubleshooting](#troubleshooting)

## Setup

The Perplexity service is automatically started when you install the package or run the `npm run autostart` command. To ensure the service is running:

```bash
# Navigate to the mcp-servers directory
cd path/to/mcp-servers

# Check if the service is running
npm run status

# If not running, start it
npm run autostart
```

## Chat Commands

Once the Perplexity service is running, you can use the following commands in Cursor chat:

| Command | Description |
|---------|-------------|
| `@search {query}` | Performs a general search query |
| `@documentation {technology} {topic}` | Gets documentation for a technology or library |
| `@apis {requirement}` | Finds relevant APIs for your project needs |
| `@code-analysis {code}` | Analyzes code for deprecated features |
| `@perplexity {message}` | General chat with Perplexity AI |

### Special Usage Pattern

When debugging issues:
```
Use '@perplexity' to validate your solution or find alternative solutions after 2 failed attempts to fix the same or repeated errors
```

## Usage Examples

Here are some examples of how to use Perplexity in Cursor chat:

### General Search
```
@search What are the best practices for React hooks?
```

### Getting Documentation
```
@documentation React useEffect hook
```

### Finding APIs
```
@apis payment processing with international support
```

### Code Analysis
```
@code-analysis 
class MyComponent extends React.Component {
  componentWillMount() {
    // Some code
  }
  render() {
    return <div>Hello World</div>;
  }
}
```

### General Chat
```
@perplexity How should I structure my React project for scalability?
```

## Troubleshooting

If you encounter issues with the Perplexity integration:

1. **Service not responding**: Run `npm run autostart` to restart the service
2. **Commands not recognized**: Restart Cursor to reload the MCP configuration
3. **Timeout errors**: Check `perplexity-bridge.log` for details
4. **API key issues**: Update the API key in `direct-perplexity-bridge.js`

For persistent issues, check the logs:
```bash
cat perplexity-autostart.log
cat perplexity-bridge.log
``` 