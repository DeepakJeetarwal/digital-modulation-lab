
const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

const root = path.join(__dirname, "..");

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 960,
    minWidth: 1100,
    minHeight: 720,
    title: "Digital Modulation Lab",
    backgroundColor: "#F7F5F0",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadFile(path.join(__dirname, "renderer", "index.html"));
}

ipcMain.handle("simulation:run", async (_event, request) => {
  return new Promise((resolve) => {
    const python = path.join(root, ".venv", "Scripts", "python.exe");
    const script = path.join(root, "backend", "simulate.py");

    const child = spawn(python, [script], {
      cwd: root,
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";
    let settled = false;

    const finish = (result) => {
      if (!settled) {
        settled = true;
        resolve(result);
      }
    };

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    child.stdout.on("data", (data) => {
      stdout += data;
    });

    child.stderr.on("data", (data) => {
      stderr += data;
    });

    child.on("error", (error) => {
      finish({
        ok: false,
        error: `Could not start Python: ${error.message}`,
      });
    });

    child.on("close", (code) => {
      if (code !== 0) {
        finish({
          ok: false,
          error: stderr.trim() || `Python exited with code ${code}.`,
        });
        return;
      }

      try {
        const result = JSON.parse(stdout.trim());
        finish(result);
      } catch {
        finish({
          ok: false,
          error: `Invalid Python response. ${stderr.trim()}`,
        });
      }
    });

    child.stdin.on("error", () => {
      // The close/error handlers report the actual failure.
    });

    child.stdin.end(JSON.stringify(request) + "\n");
  });
});

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
