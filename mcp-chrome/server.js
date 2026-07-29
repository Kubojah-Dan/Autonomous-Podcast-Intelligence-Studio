/**
 * PulseVault AI — Chrome MCP Web-Search Server
 *
 * Minimal MCP-style HTTP server that exposes three tools used by the
 * GuestResearcherAgent in Phase 2:
 *   - research_person(name)
 *   - fetch_show_website(url)
 *   - search_similar_podcasts(topic)
 *
 * This server is a lightweight stand-in. In Phase 2 it will be swapped
 * for a real Chrome Model Context Protocol connector.
 */

const http = require("http");
const https = require("https");
const { URL } = require("url");

const PORT = process.env.PORT || 8765;

function fetchText(target) {
  return new Promise((resolve) => {
    try {
      const u = new URL(target);
      const client = u.protocol === "https:" ? https : http;
      client
        .get(u, (res) => {
          let data = "";
          res.on("data", (c) => (data += c));
          res.on("end", () => resolve({ status: res.statusCode, body: data.slice(0, 8000) }));
        })
        .on("error", (e) => resolve({ status: 0, error: String(e) }));
    } catch (e) {
      resolve({ status: 0, error: String(e) });
    }
  });
}

async function research_person({ name }) {
  const q = encodeURIComponent(name + " podcast guest bio");
  return {
    tool: "research_person",
    name,
    results: [
      { title: `${name} — Wikipedia`, url: `https://en.wikipedia.org/wiki/${encodeURIComponent(name)}` },
      { title: `${name} on Twitter`, url: `https://twitter.com/search?q=${q}` },
      { title: `${name} recent talks`, url: `https://www.google.com/search?q=${q}` },
    ],
  };
}

async function fetch_show_website({ url }) {
  const r = await fetchText(url);
  return { tool: "fetch_show_website", url, ...r };
}

async function search_similar_podcasts({ topic }) {
  const q = encodeURIComponent(topic + " podcast");
  return {
    tool: "search_similar_podcasts",
    topic,
    results: [
      { title: `Podcasts about ${topic}`, url: `https://podcasts.apple.com/search?term=${q}` },
      { title: `${topic} on Spotify`, url: `https://open.spotify.com/search/${q}` },
    ],
  };
}

const server = http.createServer(async (req, res) => {
  res.setHeader("access-control-allow-origin", "*");
  if (req.method === "GET" && req.url === "/health") {
    res.end(JSON.stringify({ ok: true, tools: ["research_person", "fetch_show_website", "search_similar_podcasts"] }));
    return;
  }
  if (req.method !== "POST") {
    res.statusCode = 405;
    res.end("method not allowed");
    return;
  }
  let raw = "";
  req.on("data", (c) => (raw += c));
  req.on("end", async () => {
    try {
      const { tool, args } = JSON.parse(raw || "{}");
      let out;
      if (tool === "research_person") out = await research_person(args || {});
      else if (tool === "fetch_show_website") out = await fetch_show_website(args || {});
      else if (tool === "search_similar_podcasts") out = await search_similar_podcasts(args || {});
      else throw new Error("unknown tool: " + tool);
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify(out));
    } catch (e) {
      res.statusCode = 400;
      res.end(JSON.stringify({ error: String(e) }));
    }
  });
});

server.listen(PORT, () => console.log(`[mcp-chrome] listening on :${PORT}`));
