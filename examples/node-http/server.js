const http = require("http");
const os = require("os");

const port = process.env.PORT || 3000;

http
  .createServer((req, res) => {
    if (req.url === "/health") return res.end("ok");
    res.setHeader("Content-Type", "application/json");
    res.end(JSON.stringify({ message: "Hello from Node", host: os.hostname(), path: req.url }));
  })
  .listen(port, () => console.log(`listening on ${port}`));
