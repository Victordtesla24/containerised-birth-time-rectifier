# Perplexity MCP Integration for Cursor IDE

This package provides seamless integration between the Perplexity API and Cursor IDE using the Model Context Protocol (MCP).

## Quick Start

```bash
# Install dependencies (also automatically starts the service)
npm install

# If the service isn't running, start it
npm run autostart

# To ensure the service runs at system startup
npm run setup-startup
```

## Features

- **Direct API Bridge**: Connect directly to Perplexity API using the `sonar-reasoning-pro` model
- **Auto-start**: Service runs automatically when you start the IDE
- **Chat Integration**: Use Perplexity directly in Cursor chat with simple commands
- **System Integration**: Option to run as a system service at startup

## Documentation

- [Cursor Integration Guide](./CURSOR-INTEGRATION.md) - How to use Perplexity in Cursor chat
- [API Documentation](https://docs.perplexity.ai) - Official Perplexity API documentation

## Using Perplexity in Chat

After setting up, you can use the following in Cursor chat:

```
@search What is React hooks?
@documentation React useEffect
@apis payment processing
@code-analysis [your code here]
@perplexity [your question here]
```

### Special Usage Pattern

When debugging issues:
```
Use '@perplexity' to validate your solution or find alternative solutions after 2 failed attempts to fix the same or repeated errors
```

## Scripts

| Script | Description |
|--------|-------------|
| `npm run autostart` | Start the Perplexity service |
| `npm run setup-startup` | Configure system startup |
| `npm run perplexity-bridge` | Run the bridge directly |
| `npm run start` | Start all Perplexity services |
| `npm run setup-mcp` | Configure Cursor MCP settings |

## Troubleshooting

If you're having issues, check the logs:
```bash
cat perplexity-bridge.log
cat perplexity-autostart.log
```

For more detailed troubleshooting, see [CURSOR-INTEGRATION.md](./CURSOR-INTEGRATION.md#troubleshooting). 