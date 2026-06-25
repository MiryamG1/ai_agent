# Weather Israel MCP 🦚

An MCP server (`weather-Israel`) that gives an LLM access to weather
forecasts for Israeli cities - not via an official API, but through
**real browser control** (Playwright) that mimics a human user visiting
[weather2day.co.il](https://www.weather2day.co.il/forecast), typing a city
name, selecting it from the autocomplete list, and reading the forecast
shown on the page.

The project consists of two MCP servers connected to the same Host:

| Server | Data Source | Method |
|---|---|---|
| `weather_USA.py` | NWS API (USA) | Standard API call |
| `weather_Israel.py` | weather2day.co.il | Browser automation (Playwright) |

## Project Goal

Practice building a standalone MCP Server from scratch, and integrate
Playwright to give an LLM hands-free browser control - as opposed to
fetching data through a built-in API.

## Folder Structure

```
MCP/
├── client.py            # Generic MCP Client - connects to a single MCP Server
├── host.py               # Terminal chat that connects all Servers to the LLM
├── weather_USA.py        # MCP Server for US forecasts (API)
└── weather_Israel.py     # MCP Server for Israeli forecasts (Playwright)
```

## How It Works

`weather_Israel.py` exposes four Tools to the LLM, meant to be called in
sequence on the same shared browser state:

1. **`open_weather_forecast_israel`** - opens a visible browser and navigates to the forecast page.
2. **`enter_weather_forecast_city_israel`** - types a city name into the search field.
3. **`select_weather_forecast_city_israel`** - picks the first suggestion from the dropdown list, which triggers the page to refresh with that city's forecast.
4. **`get_weather_forecast_content_israel`** - extracts the current conditions and today's hourly forecast from the page, and returns them as text to the LLM.

Based on the question asked, the LLM decides on its own to call these
Tools in the correct order (and to pick `weather_Israel` rather than
`weather_USA` when the question is about an Israeli city).

## Running the Project

This project is managed with [uv](https://docs.astral.sh/uv/).

```bash
cd MCP

# Install dependencies
uv sync

# Install the Chromium browser for Playwright
uv run playwright install chromium

# Run the chat
uv run host.py
```

After running, a terminal chat will open. Type a question to get an
answer (Ctrl+C or type `quit` to exit).

> **Note:** For Israeli forecasts, a visible Chromium window will open on
> screen - this is expected behavior, not a bug. You can watch the
> browser type the city name, select it from the list, and the page
> refresh with the forecast.

## Example Questions

```
What's the weather forecast today in Tel Aviv?
```
```
Give me the hourly forecast for today in Bnei Brak
```
```
Do I need an umbrella today in Haifa?
```
```
What's the forecast in New York? (USA - routes to the US forecast, no browser involved)
```
```
Are there any weather alerts in California?
```

## Tech Stack

- **[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)** - the protocol that exposes Tools to an LLM.
- **[Playwright](https://playwright.dev/python/)** - browser automation (navigation, typing, clicks, text extraction).
- **Anthropic API (Claude)** - the LLM that decides which Tools to call and in what order.
