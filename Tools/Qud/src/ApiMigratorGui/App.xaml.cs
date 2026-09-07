using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;
using ApiMigrator.Core;

namespace ApiMigratorGui;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += (_, args) =>
        {
            LogCrash("DispatcherUnhandledException", args.Exception);
            MessageBox.Show(
                "An unexpected error occurred:\n\n" + args.Exception.Message +
                "\n\nLogged to _tools\\reports\\gui-crash.log",
                "ApiMigratorGui - Unhandled Error",
                MessageBoxButton.OK, MessageBoxImage.Error);
            args.Handled = true;
        };
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            LogCrash("UnhandledException", args.ExceptionObject);
            try
            {
                MessageBox.Show(
                    "A fatal error occurred:\n\n" + args.ExceptionObject +
                    "\n\nLogged to _tools\\reports\\gui-crash.log",
                    "ApiMigratorGui - Fatal Error",
                    MessageBoxButton.OK, MessageBoxImage.Error);
            }
            catch { /* UI may be gone */ }
        };
        TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            LogCrash("UnobservedTaskException", args.Exception);
            args.SetObserved();
        };

        base.OnStartup(e);
    }

    private static void LogCrash(string kind, object? ex)
    {
        try
        {
            Debug.WriteLine(ex);
            var dir = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "reports"));
            // Prefer real _tools\reports when BaseDirectory is bin\...\win-x64
            var tools = FindToolsRoot();
            if (tools is not null)
                dir = Path.Combine(tools, "reports");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "gui-crash.log");
            File.AppendAllText(path,
                $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {kind}\n{ex}\n\n");
        }
        catch { /* never throw from logger */ }
    }

    private static string? FindToolsRoot()
    {
        try { return CoqPaths.FindToolsRoot(); }
        catch { return null; }
    }
}
