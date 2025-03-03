#!/usr/bin/env node

/**
 * Direct Perplexity API Bridge
 * 
 * This script provides an HTTP bridge to the Perplexity API without using MCP protocol.
 * It follows the official Perplexity API documentation format directly.
 */

const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

// Configuration
const PORT = 3336;
const PERPLEXITY_API_KEY = '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';
const PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions';

// Create Express app
const app = express();
app.use(bodyParser.json());

// Create Perplexity API client
const perplexityClient = axios.create({
  baseURL: 'https://api.perplexity.ai',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${PERPLEXITY_API_KEY}`
  }
});

// Main search endpoint
app.post('/search', async (req, res) => {
  try {
    console.log('Received search request:', req.body);
    
    // Extract query and detail level
    const { query, detail_level = 'normal' } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Missing required parameter: query' });
    }
    
    // Format prompt based on detail level
    let prompt;
    switch (detail_level) {
      case 'brief':
        prompt = `Provide a brief, concise answer to: ${query}`;
        break;
      case 'detailed':
        prompt = `Provide a comprehensive, detailed analysis of: ${query}. Include relevant examples, context, and supporting information where applicable.`;
        break;
      default:
        prompt = `Provide a clear, balanced answer to: ${query}. Include key points and relevant context.`;
    }
    
    console.log('Sending request to Perplexity API...');
    
    // Call Perplexity API
    const response = await perplexityClient.post('/chat/completions', {
      model: 'sonar-reasoning-pro',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: prompt }
      ]
    });
    
    console.log('Received response from Perplexity API');
    
    // Extract the content
    const content = response.data.choices[0].message.content;
    
    // Return the response
    res.json({
      result: content,
      model: response.data.model,
      usage: response.data.usage
    });
  } catch (error) {
    console.error('Error calling Perplexity API:', error);
    
    if (error.response) {
      // The request was made and the server responded with an error status
      console.error('Perplexity API error:', error.response.data);
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      // The request was made but no response was received
      console.error('No response received from Perplexity API');
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      // Something happened in setting up the request
      console.error('Error setting up request:', error.message);
      res.status(500).json({ error: error.message });
    }
  }
});

// Documentation endpoint
app.post('/documentation', async (req, res) => {
  try {
    console.log('Received documentation request:', req.body);
    
    // Extract query and context
    const { query, context = '' } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Missing required parameter: query' });
    }
    
    // Create prompt for documentation
    const prompt = `Provide comprehensive documentation and usage examples for ${query}. ${context ? `Focus on: ${context}` : ""} Include:
    1. Basic overview and purpose
    2. Key features and capabilities
    3. Installation/setup if applicable
    4. Common usage examples
    5. Best practices
    6. Common pitfalls to avoid
    7. Links to official documentation if available`;
    
    console.log('Sending documentation request to Perplexity API...');
    
    // Call Perplexity API
    const response = await perplexityClient.post('/chat/completions', {
      model: 'sonar-reasoning-pro',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: prompt }
      ]
    });
    
    console.log('Received documentation response from Perplexity API');
    
    // Extract the content
    const content = response.data.choices[0].message.content;
    
    // Return the response
    res.json({
      result: content,
      model: response.data.model,
      usage: response.data.usage
    });
  } catch (error) {
    console.error('Error calling Perplexity API for documentation:', error);
    
    if (error.response) {
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

// APIs endpoint
app.post('/apis', async (req, res) => {
  try {
    console.log('Received APIs request:', req.body);
    
    // Extract requirement and context
    const { requirement, context = '' } = req.body;
    
    if (!requirement) {
      return res.status(400).json({ error: 'Missing required parameter: requirement' });
    }
    
    // Create prompt for API search
    const prompt = `Find and evaluate APIs that could be used for: ${requirement}. ${context ? `Context: ${context}` : ""} For each API, provide:
    1. Name and brief description
    2. Key features and capabilities
    3. Pricing model (if available)
    4. Integration complexity
    5. Documentation quality
    6. Community support and popularity
    7. Any potential limitations or concerns
    8. Code example of basic usage`;
    
    console.log('Sending APIs request to Perplexity API...');
    
    // Call Perplexity API
    const response = await perplexityClient.post('/chat/completions', {
      model: 'sonar-reasoning-pro',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: prompt }
      ]
    });
    
    console.log('Received APIs response from Perplexity API');
    
    // Extract the content
    const content = response.data.choices[0].message.content;
    
    // Return the response
    res.json({
      result: content,
      model: response.data.model,
      usage: response.data.usage
    });
  } catch (error) {
    console.error('Error calling Perplexity API for APIs:', error);
    
    if (error.response) {
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

// Code analysis endpoint
app.post('/code-analysis', async (req, res) => {
  try {
    console.log('Received code analysis request:', req.body);
    
    // Extract code and technology
    const { code, technology = '' } = req.body;
    
    if (!code) {
      return res.status(400).json({ error: 'Missing required parameter: code' });
    }
    
    // Create prompt for code analysis
    const prompt = `Analyze this code for deprecated features or patterns${technology ? ` in ${technology}` : ""}:

    ${code}

    Please provide:
    1. Identification of any deprecated features, methods, or patterns
    2. Current recommended alternatives
    3. Migration steps if applicable
    4. Impact of the deprecation
    5. Timeline of deprecation if known
    6. Code examples showing how to update to current best practices`;
    
    console.log('Sending code analysis request to Perplexity API...');
    
    // Call Perplexity API
    const response = await perplexityClient.post('/chat/completions', {
      model: 'sonar-reasoning-pro',
      messages: [
        { role: 'system', content: 'You are a helpful technical expert.' },
        { role: 'user', content: prompt }
      ]
    });
    
    console.log('Received code analysis response from Perplexity API');
    
    // Extract the content
    const content = response.data.choices[0].message.content;
    
    // Return the response
    res.json({
      result: content,
      model: response.data.model,
      usage: response.data.usage
    });
  } catch (error) {
    console.error('Error calling Perplexity API for code analysis:', error);
    
    if (error.response) {
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

// Chat endpoint for continuing conversations
app.post('/chat', async (req, res) => {
  try {
    console.log('Received chat request:', req.body);
    
    // Extract message and history
    const { message, history = [] } = req.body;
    
    if (!message) {
      return res.status(400).json({ error: 'Missing required parameter: message' });
    }
    
    // Prepare messages array with history
    const messages = [
      { role: 'system', content: 'You are a helpful assistant.' }
    ];
    
    // Add history messages if provided
    if (Array.isArray(history) && history.length > 0) {
      history.forEach(msg => {
        if (msg.role && msg.content) {
          messages.push({ role: msg.role, content: msg.content });
        }
      });
    }
    
    // Add the current message
    messages.push({ role: 'user', content: message });
    
    console.log('Sending chat request to Perplexity API...');
    console.log('Messages:', messages);
    
    // Call Perplexity API
    const response = await perplexityClient.post('/chat/completions', {
      model: 'sonar-reasoning-pro',
      messages: messages
    });
    
    console.log('Received chat response from Perplexity API');
    
    // Extract the content
    const content = response.data.choices[0].message.content;
    
    // Return the response with updated history
    res.json({
      result: content,
      model: response.data.model,
      usage: response.data.usage,
      updated_history: [
        ...messages,
        { role: 'assistant', content }
      ]
    });
  } catch (error) {
    console.error('Error calling Perplexity API for chat:', error);
    
    if (error.response) {
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

// Generic endpoint for any Perplexity API request
app.post('/completions', async (req, res) => {
  try {
    console.log('Received completions request:', req.body);
    
    // Directly pass the request to Perplexity API
    const response = await perplexityClient.post('/chat/completions', req.body);
    
    console.log('Received completions response from Perplexity API');
    
    // Return the full response
    res.json(response.data);
  } catch (error) {
    console.error('Error calling Perplexity API for completions:', error);
    
    if (error.response) {
      res.status(error.response.status).json({
        error: error.response.data.error?.message || 'Error from Perplexity API',
        details: error.response.data
      });
    } else if (error.request) {
      res.status(500).json({ error: 'No response from Perplexity API' });
    } else {
      res.status(500).json({ error: error.message });
    }
  }
});

// Status endpoint
app.get('/status', (req, res) => {
  res.json({
    status: 'running',
    uptime: process.uptime(),
    timestamp: new Date().toISOString(),
    endpoints: [
      { path: '/search', description: 'General search queries' },
      { path: '/documentation', description: 'Get documentation for technologies and libraries' },
      { path: '/apis', description: 'Find and evaluate APIs' },
      { path: '/code-analysis', description: 'Check for deprecated code and get migration advice' },
      { path: '/chat', description: 'Maintain a conversation with history' },
      { path: '/completions', description: 'Direct access to Perplexity chat completions API' }
    ]
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════╗
║            DIRECT PERPLEXITY API BRIDGE                ║
╚════════════════════════════════════════════════════════╝

Server running on http://localhost:${PORT}

Available endpoints:
- /search - General search queries
- /documentation - Get documentation for technologies and libraries
- /apis - Find and evaluate APIs
- /code-analysis - Check for deprecated code and get migration advice
- /chat - Maintain a conversation with history
- /completions - Direct access to Perplexity chat completions API
- /status - Check server status

This bridge communicates directly with the Perplexity API using sonar-reasoning-pro model.

Press Ctrl+C to stop the server.
`);
}); 