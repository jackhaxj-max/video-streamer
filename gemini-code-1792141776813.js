export default async function handler(req, res) {
  // 1. Enable CORS so your frontend can call this endpoint freely
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url } = req.query;

  if (!url) {
    return res.status(400).json({ error: "Please provide a valid URL parameter." });
  }

  try {
    // 2. Fetch the target page HTML with standard spoofed browser headers
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
      },
    });

    const htmlText = await response.text();

    // 3. Extract the direct stream URL (matches .mp4 links or extracted JSON stream parameters)
    const streamMatch = htmlText.match(/https?:\/\/[^\s"'<>]+\.mp4[^\s"'<>]*/i) ||
                        htmlText.match(/playUrl":"([^"]+)"/);

    let streamUrl = streamMatch ? (streamMatch[1] || streamMatch[0]) : null;

    if (!streamUrl) {
      return res.status(404).json({ error: "Could not find a valid video stream link on the target page." });
    }

    // Clean up escaped unicode slashes if present (e.g. \/ -> /)
    streamUrl = streamUrl.replace(/\\\/g, '/');

    // 4. Perform a HEAD request to check the file size (Content-Length)
    let isLargeFile = false;
    let sizeInMB = 0;

    try {
      const headRes = await fetch(streamUrl, { method: 'HEAD' });
      const contentLength = headRes.headers.get('content-length');

      if (contentLength) {
        const bytes = parseInt(contentLength, 10);
        sizeInMB = (bytes / (1024 * 1024)).toFixed(2);
        // If file size exceeds 1024 MB (1 GB)
        if (bytes > 1024 * 1024 * 1024) {
          isLargeFile = true;
        }
      }
    } catch (e) {
      console.log("Size check skipped or blocked by target head request.");
    }

    // 5. Send back response to Frontend
    return res.status(200).json({
      success: true,
      streamUrl: streamUrl,
      isLargeFile: isLargeFile,
      sizeInMB: sizeInMB
    });

  } catch (error) {
    return res.status(500).json({ error: "Failed to parse link: " + error.message });
  }
}