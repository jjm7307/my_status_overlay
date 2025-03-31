function savePageContent() {
  const content = document.body.innerText;

  const data = {
    url: window.location.href,
    timestamp: new Date().toISOString(),
    saved_at: new Date().toLocaleString("ko-KR", { hour12: false }),
    content: content
  };

  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const filename = `page_content_${Date.now()}.json`;

  chrome.runtime.sendMessage({
    action: "download",
    url: url,
    filename: filename
  });

  console.log(`[AutoSave] Saved at ${data.saved_at}`);
}

window.addEventListener("load", () => {
  setTimeout(savePageContent, 10000);
});
