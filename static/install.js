let deferredInstallPrompt = null;

const installButton = document.querySelector("[data-install-button]");
const installedMessage = document.querySelector("[data-install-ready]");
const isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

if (isStandalone && installedMessage) {
  installedMessage.hidden = false;
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  if (installButton) {
    installButton.hidden = false;
  }
});

installButton?.addEventListener("click", async () => {
  if (!deferredInstallPrompt) {
    return;
  }
  deferredInstallPrompt.prompt();
  await deferredInstallPrompt.userChoice;
  deferredInstallPrompt = null;
  installButton.hidden = true;
});

window.addEventListener("appinstalled", () => {
  if (installButton) {
    installButton.hidden = true;
  }
  if (installedMessage) {
    installedMessage.hidden = false;
  }
});
