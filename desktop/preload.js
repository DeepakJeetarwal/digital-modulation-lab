
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("simulationAPI", {
  run: (request) => ipcRenderer.invoke("simulation:run", request),
});
