#!/usr/bin/env node

/**
 * llms.txt Crawler
 * 
 * Fetches llms.txt from a website and crawls all pages listed within it.
 * 
 * Usage:
 *   node crawl.js --url https://example.com --output ./output
 */

import { program } from 'commander';
import { mkdir, writeFile, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join, basename } from 'path';
import { URL } from 'url';

// Configuration
const DEFAULT_DELAY = 500;
const DEFAULT_CONCURRENT = 3;
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

/**
 * Parse command line arguments
 */
program
  .name('llms-txt-crawler')
  .description('Fetch and crawl llms.txt files from websites')
  .requiredOption('-u, --url <url>', 'Base URL of the site with llms.txt')
  .option('-o, --output <dir>', 'Output directory', './output')
  .option('-f, --format <format>', 'Output format: md, json, txt', 'md')
  .option('-d, --delay <ms>', 'Delay between requests in milliseconds', DEFAULT_DELAY.toString())
  .option('-c, --concurrent <num>', 'Maximum concurrent requests', DEFAULT_CONCURRENT.toString())
  .parse();

const options = program.opts();

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetch URL with retry logic
 */
async function fetchWithRetry(url, retries = MAX_RETRIES) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'llms-txt-crawler/1.0 (https://github.com/agy-kit)',
          'Accept': 'text/plain, text/markdown, text/html, */*'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.text();
    } catch (error) {
      console.error(`  Attempt ${attempt}/${retries} failed for ${url}: ${error.message}`);
      
      if (attempt < retries) {
        await sleep(RETRY_DELAY * attempt);
      } else {
        throw error;
      }
    }
  }
}

/**
 * Parse llms.txt content and extract page URLs
 * 
 * Format:
 * # Site Name
 * ## Section
 * - [Title](url): Description
 */
function parseLlmsTxt(content, baseUrl) {
  const pages = [];
  const lines = content.split('\n');
  
  // Match markdown links: [Title](url) or - [Title](url): Description
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)(?::\s*(.*))?/g;
  
  let currentSection = '';
  
  for (const line of lines) {
    // Track section headers
    if (line.startsWith('## ')) {
      currentSection = line.substring(3).trim();
      continue;
    }
    
    // Find all links in the line
    let match;
    while ((match = linkRegex.exec(line)) !== null) {
      const [, title, url, description] = match;
      
      // Resolve relative URLs
      let fullUrl;
      try {
        fullUrl = new URL(url, baseUrl).href;
      } catch {
        console.warn(`  Skipping invalid URL: ${url}`);
        continue;
      }
      
      pages.push({
        title: title.trim(),
        url: fullUrl,
        description: description?.trim() || '',
        section: currentSection
      });
    }
    
    // Reset regex lastIndex for next line
    linkRegex.lastIndex = 0;
  }
  
  return pages;
}

/**
 * Generate a safe filename from URL
 */
function urlToFilename(url, format) {
  try {
    const parsed = new URL(url);
    let filename = parsed.pathname
      .replace(/^\//, '')
      .replace(/\//g, '_')
      .replace(/\.[^.]+$/, '') // Remove existing extension
      || 'index';
    
    // Sanitize filename
    filename = filename.replace(/[^a-zA-Z0-9_-]/g, '_');
    
    return `${filename}.${format}`;
  } catch {
    return `page_${Date.now()}.${format}`;
  }
}

/**
 * Process a batch of pages concurrently
 */
async function processBatch(pages, outputDir, format, delay) {
  const results = [];
  
  for (const page of pages) {
    try {
      console.log(`  Fetching: ${page.url}`);
      const content = await fetchWithRetry(page.url);
      
      const filename = urlToFilename(page.url, format);
      const filepath = join(outputDir, 'pages', filename);
      
      let outputContent;
      if (format === 'json') {
        outputContent = JSON.stringify({
          title: page.title,
          url: page.url,
          description: page.description,
          section: page.section,
          content: content,
          crawledAt: new Date().toISOString()
        }, null, 2);
      } else {
        // Markdown or text format
        outputContent = `---
title: ${page.title}
url: ${page.url}
section: ${page.section}
crawledAt: ${new Date().toISOString()}
---

${content}`;
      }
      
      await writeFile(filepath, outputContent, 'utf-8');
      
      results.push({
        ...page,
        filename,
        success: true
      });
      
      console.log(`  ✓ Saved: ${filename}`);
    } catch (error) {
      console.error(`  ✗ Failed: ${page.url} - ${error.message}`);
      results.push({
        ...page,
        success: false,
        error: error.message
      });
    }
    
    // Delay between requests
    if (delay > 0) {
      await sleep(delay);
    }
  }
  
  return results;
}

/**
 * Main crawler function
 */
async function crawl() {
  const baseUrl = options.url;
  const outputDir = options.output;
  const format = options.format;
  const delay = parseInt(options.delay, 10);
  const concurrent = parseInt(options.concurrent, 10);
  
  console.log('llms.txt Crawler');
  console.log('================');
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Output: ${outputDir}`);
  console.log(`Format: ${format}`);
  console.log(`Delay: ${delay}ms`);
  console.log(`Concurrent: ${concurrent}`);
  console.log('');
  
  // Create output directories
  await mkdir(join(outputDir, 'pages'), { recursive: true });
  
  // Fetch llms.txt
  const llmsTxtUrl = new URL('/llms.txt', baseUrl).href;
  console.log(`Fetching llms.txt from: ${llmsTxtUrl}`);
  
  let llmsTxtContent;
  try {
    llmsTxtContent = await fetchWithRetry(llmsTxtUrl);
  } catch (error) {
    console.error(`Failed to fetch llms.txt: ${error.message}`);
    process.exit(1);
  }
  
  // Save original llms.txt
  await writeFile(join(outputDir, 'llms.txt'), llmsTxtContent, 'utf-8');
  console.log('✓ Saved llms.txt\n');
  
  // Parse llms.txt
  const pages = parseLlmsTxt(llmsTxtContent, baseUrl);
  console.log(`Found ${pages.length} pages to crawl\n`);
  
  if (pages.length === 0) {
    console.log('No pages found in llms.txt');
    return;
  }
  
  // Process pages in batches
  console.log('Crawling pages...');
  const allResults = [];
  
  for (let i = 0; i < pages.length; i += concurrent) {
    const batch = pages.slice(i, i + concurrent);
    const batchResults = await processBatch(batch, outputDir, format, delay);
    allResults.push(...batchResults);
  }
  
  // Generate index
  const index = {
    source: llmsTxtUrl,
    crawledAt: new Date().toISOString(),
    totalPages: pages.length,
    successful: allResults.filter(r => r.success).length,
    failed: allResults.filter(r => !r.success).length,
    pages: allResults
  };
  
  await writeFile(join(outputDir, 'index.json'), JSON.stringify(index, null, 2), 'utf-8');
  
  // Summary
  console.log('\n================');
  console.log('Crawl Complete!');
  console.log(`Total: ${pages.length}`);
  console.log(`Success: ${index.successful}`);
  console.log(`Failed: ${index.failed}`);
  console.log(`Output: ${outputDir}`);
}

// Run
crawl().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
