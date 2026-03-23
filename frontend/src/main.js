const app = document.getElementById("app");

app.innerHTML = `
  <div style="font-family: Arial, sans-serif; padding: 24px;">
    <h1>A22 Local Frontend</h1>
    <p>Frontend is running inside Docker on WSL.</p>
    <input id="msg" type="text" placeholder="Type a message" style="width: 320px; padding: 8px;" />
    <button id="send" style="margin-left: 8px; padding: 8px 12px;">Send</button>
    <pre id="output" style="margin-top: 16px; background: #f5f5f5; padding: 12px;"></pre>
  </div>
`;

document.getElementById("send").addEventListener("click", async () => {
  const text = document.getElementById("msg").value;
  const output = document.getElementById("output");

  output.textContent = "Loading...";

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });

  const data = await res.json();
  output.textContent = JSON.stringify(data, null, 2);
});
