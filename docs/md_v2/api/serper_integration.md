# Serper.dev Integration

Crawl4AI integrates with [Serper.dev](https://serper.dev) to provide powerful search capabilities for hybrid search and web crawling. This document outlines how to use Serper.dev with Crawl4AI, including API key configuration, rate limits, and best practices.

## Setup

### 1. Obtain a Serper.dev API Key

Sign up at [Serper.dev](https://serper.dev) and get your API key from your dashboard.

### 2. Configure the API Key

Set your Serper.dev API key as an environment variable:

```bash
export SERPER_API_KEY="your_serper_api_key"
```

Or add it to your `.env` file:

```
SERPER_API_KEY=your_serper_api_key
```

### 3. Usage in Crawl4AI

Crawl4AI will automatically use your Serper.dev API key when performing hybrid searches or when explicitly configured to use Serper as the search provider.

## Rate Limits

Serper.dev imposes rate limits on API usage based on your subscription package:

| Package | Rate Limit |
|---------|------------|
| Starter | 50 queries per second |
| Standard | 100 queries per second |
| Scale | 200 queries per second |
| Ultimate | 300 queries per second |

Exceeding these limits may result in your requests being throttled or rejected.

## Error Handling

When rate limits are exceeded, Serper.dev will return an error response. Crawl4AI automatically handles these errors with exponential backoff retry logic, but for optimal performance, you should ensure your application doesn't exceed the rate limits for your subscription tier.

## Example Usage

### Hybrid Search with Serper

```python
from crawl4ai import Crawl4AI
from crawl4ai.config import SearchProvider

# Initialize Crawl4AI with Serper.dev as the search provider
crawler = Crawl4AI(search_provider=SearchProvider.SERPER)

# Perform a hybrid search
results = crawler.hybrid_search(
    query="artificial intelligence latest developments",
    num_results=5
)

for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Content: {result.content[:100]}...")
    print("---")
```

### API Request with Serper

When using the Crawl4AI API, you can specify Serper as the search provider:

```json
{
  "query": "artificial intelligence latest developments",
  "search_provider": "serper",
  "num_results": 5
}
```

## Best Practices

1. **Cache Results**: Implement caching for search results to reduce the number of API calls to Serper.dev
2. **Rate Limiting**: Implement your own rate limiting to stay within your subscription limits
3. **Error Handling**: Add proper error handling for cases where the rate limit is exceeded
4. **Monitoring**: Monitor your Serper.dev API usage to ensure you're not approaching limits

## Troubleshooting

If you encounter issues with Serper.dev integration, check the following:

1. Verify your API key is correctly set in the environment variables
2. Ensure you haven't exceeded your rate limits
3. Check your network connection
4. Review Serper.dev documentation for any changes to their API

For more information about Serper.dev API capabilities and documentation, visit the [official Serper.dev documentation](https://serper.dev/docs).
