const urlInput = document.getElementById("url-input");
const downloadBtn = document.getElementById("download-btn");
const statusEl = document.getElementById("status");
const previewEl = document.getElementById("preview");
const previewThumb = document.getElementById("preview-thumb");
const previewTitle = document.getElementById("preview-title");
const previewMeta = document.getElementById("preview-meta");

function setStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = "status" + (type ? " " + type : "");
}

function formatDuration(seconds) {
  if (!seconds) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function parseFilename(contentDisposition) {
  if (!contentDisposition) return "video.mp4";
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/);
  return plainMatch ? plainMatch[1] : "video.mp4";
}

async function startDownload() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("Вставьте ссылку на видео", "error");
    return;
  }

  downloadBtn.disabled = true;
  previewEl.classList.add("hidden");
  setStatus("Получаю информацию о видео...");

  try {
    const infoResp = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const info = await infoResp.json();
    if (!infoResp.ok) throw new Error(info.error || "Не удалось получить информацию");

    previewThumb.src = info.thumbnail || "";
    previewTitle.textContent = info.title || "";
    previewMeta.textContent = [info.uploader, formatDuration(info.duration)]
      .filter(Boolean)
      .join(" · ");
    previewEl.classList.remove("hidden");

    setStatus("Скачиваю видео, это может занять время...");

    const downloadResp = await fetch("/download?url=" + encodeURIComponent(url));
    if (!downloadResp.ok) {
      const err = await downloadResp.json().catch(() => ({}));
      throw new Error(err.error || "Ошибка скачивания");
    }

    const blob = await downloadResp.blob();
    const filename = parseFilename(downloadResp.headers.get("Content-Disposition"));

    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);

    setStatus("Готово! Файл сохранён в папку «Загрузки».", "success");
  } catch (err) {
    setStatus("Ошибка: " + err.message, "error");
  } finally {
    downloadBtn.disabled = false;
  }
}

downloadBtn.addEventListener("click", startDownload);
urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") startDownload();
});
