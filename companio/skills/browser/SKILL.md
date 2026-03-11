---
name: browser
description: Browser automation via Playwright MCP. Navigate, click, fill forms, take screenshots, and extract data from web pages.
---

# Browser Automation Skill (Playwright MCP)

Automate browser interactions using the Playwright MCP server. This skill enables navigating web pages, filling forms, clicking elements, extracting data, and capturing screenshots.

## Prerequisites

### 1. Node.js

`npx` must be available on the system (requires Node.js to be installed).

### 2. Playwright MCP Server Configuration

The Playwright MCP server must be configured in your `config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp@latest"],
        "toolTimeout": 60
      }
    }
  }
}
```

Once configured, tools are auto-registered with the `mcp_playwright_` prefix.

## Available Tools

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to a URL |
| `browser_snapshot` | Get page accessibility snapshot (preferred over screenshot for data extraction) |
| `browser_click` | Click an element by text or role |
| `browser_fill` | Fill an input field with text |
| `browser_type` | Type text character by character (useful for inputs that need keystrokes) |
| `browser_select_option` | Select a dropdown option |
| `browser_press_key` | Press a keyboard key (Enter, Tab, Escape, etc.) |
| `browser_take_screenshot` | Capture a screenshot of the page |
| `browser_hover` | Hover over an element |
| `browser_drag` | Drag and drop an element |
| `browser_evaluate` | Execute JavaScript on the page |
| `browser_file_upload` | Upload a file to a file input |
| `browser_handle_dialog` | Accept or dismiss browser dialogs (alerts, confirms, prompts) |
| `browser_wait_for` | Wait for specific text or element to appear on the page |
| `browser_tabs` | List all open browser tabs |
| `browser_navigate_back` | Go back to the previous page |
| `browser_close` | Close the browser |
| `browser_console_messages` | Get console log messages from the page |
| `browser_network_requests` | Get the network request log |

## Common Patterns

### Web Page Data Extraction

Navigate to a page, take a snapshot of the accessibility tree, and extract the information you need.

```
1. browser_navigate  -> go to the target URL
2. browser_snapshot   -> get structured accessibility tree
3. Parse the snapshot output for the desired data
```

### Form Filling

Navigate to a form, fill in the fields, and submit.

```
1. browser_navigate  -> go to the form page
2. browser_click     -> click the first input field
3. browser_fill      -> fill in the value
4. browser_click     -> click the next field (repeat fill as needed)
5. browser_click     -> click the submit button
```

### Login Flow

Automate logging into a website.

```
1. browser_navigate  -> go to the login page
2. browser_fill      -> fill the username field
3. browser_fill      -> fill the password field
4. browser_click     -> click the login button
5. browser_wait_for  -> wait for the dashboard or redirect to confirm login
```

### Multi-Page Scraping

Scrape data across multiple pages with pagination.

```
1. browser_navigate  -> go to the first page
2. browser_snapshot  -> extract data from current page
3. browser_click     -> click the "Next" button
4. browser_snapshot  -> extract data from the next page
5. Repeat steps 3-4 until done
```

### Screenshot Capture

Take a screenshot of a page after it has fully loaded.

```
1. browser_navigate       -> go to the target URL
2. browser_wait_for       -> wait for key content to appear
3. browser_take_screenshot -> capture the screenshot
```

## Tips

- **Prefer `browser_snapshot` over `browser_take_screenshot` for text data.** Snapshot returns a structured accessibility tree that is far more useful for data extraction and parsing than a visual screenshot.
- **Use `browser_wait_for` after navigation or clicks that trigger page loads.** This ensures the page has finished loading before you interact with it.
- **Use `browser_evaluate` for complex DOM operations** that the other tools cannot handle, such as reading computed styles, scrolling to specific positions, or extracting data via JavaScript selectors.
- **Always call `browser_close` when done** to clean up the browser session and free resources.
- **Tool names use the `mcp_playwright_` prefix when called.** For example, to navigate you would invoke `mcp_playwright_browser_navigate`, to take a snapshot you would invoke `mcp_playwright_browser_snapshot`, and so on.
