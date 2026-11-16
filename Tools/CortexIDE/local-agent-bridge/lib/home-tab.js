"use strict";
// The New Tab page: an editor tab shown in place of VS Code's Welcome page when the Local Agent is
// opened or focused, as Cursor's agent layout does. It has a composer that starts a chat in the
// Agent panel, the open tabs, this workspace's panels (Changes, Browser, Terminal, Files, Canvas,
// Side Chat), its canvases, your own panels and the recent chats.

const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

const VIEW_TYPE = "localAgentBridge.home";
const TITLE = "New Tab";

/** VS Code's own start pages, closed when the New Tab page takes their place. */
const WELCOME_LABELS = /^(welcome|get started|getting started|walkthrough:.*|release notes:.*)$/i;

function cfg() {
  return vscode.workspace.getConfiguration("localAgentBridge");
}

class HomeTab {
  /** @param {import("vscode").ExtensionContext} context @param {any} agent the AgentViewProvider */
  constructor(context, agent) {
    this.context = context;
    this.agent = agent;
    this.panel = null;
    agent.home = this;
  }

  static register(context, agent) {
    const home = new HomeTab(context, agent);
    context.subscriptions.push(vscode.commands.registerCommand("localAgentBridge.openHome", () => home.open({ force: true })));
    // Restore the page after a window reload instead of leaving an empty tab behind.
    if (vscode.window.registerWebviewPanelSerializer) {
      context.subscriptions.push(
        vscode.window.registerWebviewPanelSerializer(VIEW_TYPE, {
          deserializeWebviewPanel: async (panel) => home.adopt(panel),
        })
      );
    }
    return home;
  }

  /** All editor tabs, except this page. */
  otherTabs() {
    const out = [];
    try {
      for (const g of vscode.window.tabGroups.all) for (const t of g.tabs) if (!this.isMine(t)) out.push(t);
    } catch {
      /* no tab API */
    }
    return out;
  }

  isMine(t) {
    return !!(t && t.input && t.input.viewType && String(t.input.viewType).endsWith(VIEW_TYPE));
  }

  /** VS Code's Welcome / walkthrough tabs (custom editors without a file). */
  welcomeTabs() {
    return this.otherTabs().filter((t) => WELCOME_LABELS.test(String(t.label || "").trim()) && !(t.input && t.input.uri));
  }

  /**
   * The Agent view became visible. With localAgentBridge.newTab = "replaceWelcome" (default) the
   * page opens when the editor area is empty or only holds the Welcome page; "always" opens it
   * whenever the agent is shown; "off" never.
   */
  async onAgentShown() {
    const mode = cfg().get("newTab", "replaceWelcome");
    if (mode === "off") return;
    const welcome = this.welcomeTabs();
    const others = this.otherTabs().filter((t) => !welcome.includes(t));
    if (mode === "replaceWelcome" && others.length && !welcome.length) return;
    if (mode === "replaceWelcome" && others.length && welcome.length) {
      // Other files are open as well: just swap the Welcome page for this one, without stealing focus.
      await this.open({ preserveFocus: true });
      await this.closeWelcome(welcome);
      return;
    }
    await this.open({ preserveFocus: true });
    await this.closeWelcome(welcome);
  }

  async closeWelcome(tabs) {
    if (!tabs.length || !vscode.window.tabGroups.close) return;
    try {
      await vscode.window.tabGroups.close(tabs, true);
    } catch {
      /* already gone */
    }
  }

  /** Show the page (creating it when needed). */
  async open({ preserveFocus = false, force = false } = {}) {
    if (this.panel) {
      if (force || !this.panel.visible) this.panel.reveal(this.panel.viewColumn || vscode.ViewColumn.One, preserveFocus);
      this.refresh();
      return this.panel;
    }
    const panel = vscode.window.createWebviewPanel(VIEW_TYPE, TITLE, { viewColumn: vscode.ViewColumn.One, preserveFocus }, { enableScripts: true, retainContextWhenHidden: false });
    this.adopt(panel);
    return panel;
  }

  adopt(panel) {
    this.panel = panel;
    try {
      panel.iconPath = vscode.Uri.file(path.join(this.context.extensionPath, "media", "icon.svg"));
    } catch {
      /* no icon */
    }
    panel.webview.options = { enableScripts: true };
    panel.webview.html = page(this.context.extensionPath);
    panel.webview.onDidReceiveMessage((m) => this.onMessage(m));
    panel.onDidChangeViewState(() => panel.visible && this.refresh());
    panel.onDidDispose(() => {
      if (this.panel === panel) this.panel = null;
    });
  }

  refresh(data) {
    if (!this.panel) return;
    let d = data;
    try {
      d = d || this.agent.panelData();
    } catch {
      d = {};
    }
    this.panel.webview.postMessage({ type: "data", ...d });
  }

  async onMessage(m) {
    try {
      if (!m || !m.type) return;
      if (m.type === "ready") this.refresh();
      else if (m.type === "send") await this.agent.startFromHome(m.text, m.mode);
      else if (m.type === "panel") await this.agent.panelAction(m);
      else if (m.type === "chat") await this.agent.openChatFromHome(m.id);
      else if (m.type === "history") {
        await this.agent.focus();
        await this.agent.showHistory();
      } else if (m.type === "model") await this.agent.pickModel();
      else if (m.type === "linkCanvas") await vscode.commands.executeCommand("localAgentBridge.linkCanvas");
      else if (m.type === "newCanvas") {
        await this.agent.focus();
        await this.agent.newChat();
        this.agent.post({ type: "seed", text: "Follow the canvas skill and make a canvas (.canvas.tsx in the workspace canvases folder) that shows " });
      }
    } catch (e) {
      vscode.window.showErrorMessage("New Tab: " + ((e && e.message) || e));
    }
  }
}

function page(extPath) {
  try {
    const html = fs.readFileSync(path.join(extPath || path.join(__dirname, ".."), "media", "home.html"), "utf8");
    const comp = fs.readFileSync(path.join(__dirname, "composer.js"), "utf8").replace(/<\/script/gi, "<\\/script");
    return html.replace("/*@composer*/", () => comp);
  } catch (e) {
    return "<!DOCTYPE html><html><body><p>New Tab page is missing: " + String((e && e.message) || e).replace(/[<&]/g, "") + "</p></body></html>";
  }
}

module.exports = { HomeTab, page, VIEW_TYPE, WELCOME_LABELS };
