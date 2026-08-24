async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
  document.body.append(textArea);
  textArea.select();

  const copied = document.execCommand("copy");
  textArea.remove();

  if (!copied) {
    throw new Error("Copy command failed");
  }
}

document.querySelectorAll(".main-content pre").forEach((pre) => {
  const wrapper = document.createElement("div");
  const button = document.createElement("button");

  wrapper.className = "code-block";
  button.className = "copy-code-button";
  button.type = "button";
  button.textContent = "Copy";
  button.setAttribute("aria-label", "Copy code to clipboard");

  pre.before(wrapper);
  wrapper.append(pre, button);

  button.addEventListener("click", async () => {
    try {
      await copyText(pre.textContent);
      button.textContent = "Copied!";
    } catch {
      button.textContent = "Copy failed";
    }

    window.setTimeout(() => {
      button.textContent = "Copy";
    }, 2000);
  });
});
