using System;
using System.Windows.Forms;

namespace AAMT.AudioBench
{
    /// <summary>
    /// Audio Bench, the program: hosts the toolkit's bench page (Tools/Shared/audio_bench_gui.html) in a window, with the
    /// bench server (audio_bench_server.py) started from the toolkit repo underneath it and its log in view. Everything
    /// that shapes audio is the repo's Python; this exe only finds it, runs it, and shows it.
    /// </summary>
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm(args));
        }
    }
}
