"use strict";

// Just enough of the `vscode` API to activate extension.js under plain node.
// install() must run before anything requires "vscode".

const fs = require("fs");
const path = require("path");
const Module = require("module");

function install({ workspace, settings = {}, appRoot = process.env.CORTEXIDE_APP || "D:\\tools\\CortexIDE\\resources\\app" }) {
  const disposable = { dispose() {} };
  const noop = () => disposable;
  const commands = new Map();
  const webviewProviders = new Map();
  const treeProviders = new Map();
  const customEditors = new Map();
  const messages = [];
  const workspaceState = new Map();

  class EventEmitter {
    constructor() {
      this.listeners = [];
      this.event = (f) => {
        this.listeners.push(f);
        return disposable;
      };
    }
    fire(v) {
      this.listeners.forEach((f) => f(v));
    }
  }
  const Uri = {
    file: (p) => ({ fsPath: p, scheme: "file", toString: () => "file:///" + p }),
    joinPath: (u, ...parts) => Uri.file(path.join(u.fsPath, ...parts)),
  };
  const say = (kind) => async (m) => {
    messages.push({ kind, text: m });
  };

  const vscode = {
    EventEmitter,
    Uri,
    StatusBarAlignment: { Left: 1, Right: 2 },
    TreeItemCollapsibleState: { None: 0 },
    ConfigurationTarget: { Global: 1 },
    ViewColumn: { Beside: -2 },
    ColorThemeKind: { Light: 1, Dark: 2 },
    TreeItem: class {
      constructor(label) {
        this.label = label;
      }
    },
    ThemeColor: class {},
    env: { appRoot, clipboard: { writeText: async () => {} } },
    languages: { getDiagnostics: () => [] },
    workspace: {
      workspaceFolders: workspace ? [{ uri: Uri.file(workspace) }] : undefined,
      textDocuments: [],
      getConfiguration: (section) => ({
        get: (k, d) => (settings[section + "." + k] !== undefined ? settings[section + "." + k] : d),
        update: async (k, v) => {
          settings[section + "." + k] = v;
        },
      }),
      onDidChangeTextDocument: noop,
      openTextDocument: async () => ({}),
      fs: { delete: async (u) => fs.unlinkSync(u.fsPath) },
    },
    window: {
      activeTextEditor: undefined,
      visibleTextEditors: [],
      activeColorTheme: { kind: 2 },
      onDidChangeActiveColorTheme: noop,
      tabGroups: { activeTabGroup: {} },
      createStatusBarItem: () => ({ show() {}, dispose() {} }),
      registerTreeDataProvider: (id, p) => {
        treeProviders.set(id, p);
        return disposable;
      },
      registerCustomEditorProvider: (id, p) => {
        customEditors.set(id, p);
        return disposable;
      },
      registerWebviewViewProvider: (id, p) => {
        webviewProviders.set(id, p);
        return disposable;
      },
      showInformationMessage: say("info"),
      showWarningMessage: say("warn"),
      showErrorMessage: say("error"),
      showTextDocument: async () => {},
      showQuickPick: async () => undefined,
      showInputBox: async () => undefined,
      showOpenDialog: async () => undefined,
    },
    commands: {
      registerCommand: (id, fn) => {
        commands.set(id, fn);
        return disposable;
      },
      executeCommand: async () => {},
    },
  };

  const origResolve = Module._resolveFilename;
  Module._resolveFilename = function (req, ...rest) {
    return req === "vscode" ? "vscode" : origResolve.call(this, req, ...rest);
  };
  require.cache.vscode = { id: "vscode", filename: "vscode", loaded: true, exports: vscode };

  function makeContext(extPath) {
    return {
      subscriptions: [],
      extensionPath: extPath,
      extensionUri: Uri.file(extPath),
      workspaceState: { get: (k) => workspaceState.get(k), update: async (k, v) => workspaceState.set(k, v) },
      globalState: { get: () => undefined, update: async () => {} },
    };
  }

  return { vscode, commands, webviewProviders, treeProviders, customEditors, messages, workspaceState, makeContext, disposable, noop };
}

module.exports = { install };
