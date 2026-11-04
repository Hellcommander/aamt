"use strict";

const vscode = require("vscode");
const path = require("path");
const { transpileCanvas, readSidecar, writeSidecar } = require("./transpile");

function nonce() {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let s = "";
  for (let i = 0; i < 32; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

function html(webview, extensionUri, n) {
  const react = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "react.production.min.js"));
  const reactDom = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "react-dom.production.min.js"));
  const runtime = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "canvas-runtime.js"));
  const host = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "canvas-host.js"));
  const css = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, "media", "canvas-host.css"));
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} data:; style-src ${webview.cspSource} 'unsafe-inline'; script-src ${webview.cspSource} 'nonce-${n}' 'unsafe-eval';" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="${css}" />
  <title>Canvas</title>
</head>
<body>
  <div id="error" class="canvas-error" hidden></div>
  <div id="root"></div>
  <script nonce="${n}" src="${react}"></script>
  <script nonce="${n}" src="${reactDom}"></script>
  <script nonce="${n}" src="${runtime}"></script>
  <script nonce="${n}" src="${host}"></script>
</body>
</html>`;
}

class CanvasEditorProvider {
  static register(context) {
    const provider = new CanvasEditorProvider(context);
    return vscode.window.registerCustomEditorProvider(
      "localAgentBridge.canvasPreview",
      provider,
      {
        webviewOptions: { retainContextWhenHidden: true },
        supportsMultipleEditorsPerDocument: false,
      }
    );
  }

  constructor(context) {
    this.context = context;
  }

  async resolveCustomTextEditor(document, webviewPanel) {
    webviewPanel.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.context.extensionUri],
    };
    const n = nonce();
    webviewPanel.webview.html = html(webviewPanel.webview, this.context.extensionUri, n);

    const push = () => {
      const { js, diagnostics } = transpileCanvas(
        document.getText(),
        document.fileName,
        vscode.env.appRoot
      );
      webviewPanel.webview.postMessage({
        type: "source",
        file: document.fileName,
        js,
        diagnostics,
        persisted: readSidecar(document.fileName),
        kind: vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.Light ? "light" : "dark",
      });
    };

    const changeDoc = vscode.workspace.onDidChangeTextDocument((e) => {
      if (e.document.uri.toString() === document.uri.toString()) push();
    });
    const changeTheme = vscode.window.onDidChangeActiveColorTheme(() => push());

    webviewPanel.webview.onDidReceiveMessage(async (msg) => {
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "ready") {
        push();
        return;
      }
      if (msg.type === "persist") {
        try {
          const current = readSidecar(document.fileName);
          writeSidecar(document.fileName, Object.assign({}, current, msg.state || {}));
        } catch (err) {
          vscode.window.showErrorMessage("Canvas state save failed: " + (err.message || err));
        }
        return;
      }
      if (msg.type === "action") {
        await this.dispatch(msg.action, document);
      }
    });

    webviewPanel.onDidDispose(() => {
      changeDoc.dispose();
      changeTheme.dispose();
    });

    push();
  }

  async dispatch(action, document) {
    if (!action || typeof action !== "object") return;
    const type = String(action.type || "");
    if (type === "openFile") {
      const raw = String(action.path || "");
      if (!raw) return;
      let uri = path.isAbsolute(raw)
        ? vscode.Uri.file(raw)
        : vscode.Uri.joinPath((vscode.workspace.workspaceFolders || [])[0]?.uri || document.uri, raw);
      const doc = await vscode.workspace.openTextDocument(uri);
      const editor = await vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.Beside });
      const sel = action.selection;
      if (sel && typeof sel.startLine === "number") {
        const start = new vscode.Position(Math.max(0, sel.startLine - 1), Math.max(0, (sel.startColumn || 1) - 1));
        const end = new vscode.Position(Math.max(0, (sel.endLine || sel.startLine) - 1), Math.max(0, (sel.endColumn || sel.startColumn || 1) - 1));
        editor.selection = new vscode.Selection(start, end);
        editor.revealRange(new vscode.Range(start, end));
      }
      return;
    }
    if (type === "newComposerChat") {
      const prompt = String(action.userPrompt || "");
      await vscode.env.clipboard.writeText(document.fileName + (prompt ? "\n" + prompt : ""));
      vscode.window.showInformationMessage("Canvas path copied. Paste it into CortexIDE Agent chat as an @mention.");
      return;
    }
    if (type === "openAgent") {
      vscode.window.showInformationMessage("openAgent is a Cursor host action. Open the transcript in Cursor, or paste the agent id in CortexIDE chat.");
    }
  }
}

module.exports = { CanvasEditorProvider };
