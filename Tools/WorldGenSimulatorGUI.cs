using System;
using System.IO;
using System.Linq;
using WinForms = System.Windows.Forms;

namespace WorldGenSimulator
{
    // Helper to resolve DialogResult ambiguity
    internal static class DialogResultHelper
    {
        public static bool IsOk(object result)
        {
            return result != null && result.ToString() == "OK";
        }
    }

    /// <summary>
    /// GUI wrapper for WorldGenSimulator with drag and drop support
    /// </summary>
    public class WorldGenSimulatorGUI : WinForms.Form
    {
        private WinForms.TextBox pathTextBox;
        private WinForms.Button analyzeButton;
        private WinForms.Button browseButton;
        private WinForms.Button analyzeAllButton;
        private WinForms.CheckBox executeCheckBox;
        private WinForms.RichTextBox outputTextBox;
        private WinForms.Panel dropPanel;
        private WinForms.Label dropLabel;

        public WorldGenSimulatorGUI()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text = "WorldGen Simulator - Drag & Drop";
            this.Size = new System.Drawing.Size(900, 700);
            this.StartPosition = WinForms.FormStartPosition.CenterScreen;

            // Drop panel
            dropPanel = new WinForms.Panel
            {
                Dock = WinForms.DockStyle.Top,
                Height = 120,
                BorderStyle = WinForms.BorderStyle.FixedSingle,
                BackColor = System.Drawing.Color.LightGray,
                AllowDrop = true
            };
            dropPanel.DragEnter += DropPanel_DragEnter;
            dropPanel.DragDrop += DropPanel_DragDrop;
            dropPanel.DragOver += DropPanel_DragOver;

            dropLabel = new WinForms.Label
            {
                Text = "Drag and drop a mod source folder here\nor click Browse to select",
                Dock = WinForms.DockStyle.Fill,
                TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
                Font = new System.Drawing.Font("Arial", 11, System.Drawing.FontStyle.Bold)
            };
            dropPanel.Controls.Add(dropLabel);

            // Path text box
            pathTextBox = new WinForms.TextBox
            {
                Dock = WinForms.DockStyle.Top,
                Height = 30,
                ReadOnly = true
            };

            // Options
            executeCheckBox = new WinForms.CheckBox
            {
                Text = "Execute mode (loads and runs mod assemblies - slower but more accurate)",
                Dock = WinForms.DockStyle.Top,
                Height = 25
            };

            // Buttons
            var buttonPanel = new WinForms.Panel { Dock = WinForms.DockStyle.Top, Height = 40 };

            browseButton = new WinForms.Button { Text = "Browse...", Dock = WinForms.DockStyle.Left, Width = 100 };
            browseButton.Click += BrowseButton_Click;

            analyzeButton = new WinForms.Button { Text = "Analyze Selected", Dock = WinForms.DockStyle.Left, Width = 130, Enabled = false };
            analyzeButton.Click += AnalyzeButton_Click;

            analyzeAllButton = new WinForms.Button { Text = "Analyze All Mods", Dock = WinForms.DockStyle.Left, Width = 130 };
            analyzeAllButton.Click += AnalyzeAllButton_Click;

            buttonPanel.Controls.Add(analyzeAllButton);
            buttonPanel.Controls.Add(analyzeButton);
            buttonPanel.Controls.Add(browseButton);

            // Output text box
            outputTextBox = new WinForms.RichTextBox
            {
                Dock = WinForms.DockStyle.Fill,
                ReadOnly = true,
                Font = new System.Drawing.Font("Consolas", 9)
            };

            // Main layout
            var mainPanel = new WinForms.Panel { Dock = WinForms.DockStyle.Fill };
            mainPanel.Controls.Add(outputTextBox);
            mainPanel.Controls.Add(buttonPanel);
            mainPanel.Controls.Add(executeCheckBox);
            mainPanel.Controls.Add(pathTextBox);
            mainPanel.Controls.Add(dropPanel);

            this.Controls.Add(mainPanel);
        }

        private void DropPanel_DragEnter(object sender, WinForms.DragEventArgs e)
        {
            if (e.Data.GetDataPresent(WinForms.DataFormats.FileDrop))
            {
                e.Effect = WinForms.DragDropEffects.Copy;
                dropPanel.BackColor = System.Drawing.Color.LightBlue;
            }
        }

        private void DropPanel_DragOver(object sender, WinForms.DragEventArgs e)
        {
            if (e.Data.GetDataPresent(WinForms.DataFormats.FileDrop))
            {
                e.Effect = WinForms.DragDropEffects.Copy;
            }
        }

        private void DropPanel_DragDrop(object sender, WinForms.DragEventArgs e)
        {
            dropPanel.BackColor = System.Drawing.Color.LightGray;

            if (e.Data.GetDataPresent(WinForms.DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(WinForms.DataFormats.FileDrop);
                if (files.Length > 0)
                {
                    string path = files[0];
                    if (Directory.Exists(path))
                    {
                        pathTextBox.Text = path;
                        analyzeButton.Enabled = true;
                    }
                    else if (File.Exists(path))
                    {
                        pathTextBox.Text = Path.GetDirectoryName(path);
                        analyzeButton.Enabled = true;
                    }
                }
            }
        }

        private void BrowseButton_Click(object sender, EventArgs e)
        {
            using (WinForms.FolderBrowserDialog dialog = new WinForms.FolderBrowserDialog())
            {
                dialog.Description = "Select mod source folder";
                object dialogResult = dialog.ShowDialog();
                if (DialogResultHelper.IsOk(dialogResult))
                {
                    pathTextBox.Text = dialog.SelectedPath;
                    analyzeButton.Enabled = true;
                }
            }
        }

        private void AnalyzeButton_Click(object sender, EventArgs e)
        {
            if (string.IsNullOrEmpty(pathTextBox.Text) || !Directory.Exists(pathTextBox.Text))
            {
                outputTextBox.AppendText("ERROR: Please select a valid mod source folder.\n");
                return;
            }

            analyzeButton.Enabled = false;
            analyzeAllButton.Enabled = false;
            outputTextBox.Clear();
            outputTextBox.AppendText($"Analyzing: {pathTextBox.Text}\n");
            outputTextBox.AppendText("=".PadRight(80, '=') + "\n\n");

            try
            {
                var originalOut = Console.Out;
                var writer = new StringWriter();
                Console.SetOut(writer);

                if (executeCheckBox.Checked)
                {
                    // Use execution simulator
                    var modSourcesPath = Path.GetDirectoryName(pathTextBox.Text);
                    var modsPath = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                        "My Games", "Terraria", "tModLoader", "Mods");
                    var workshopPath = @"E:\SteamLibrary\steamapps\workshop\content\1281930";

                    var simulator = new WorldGenSimulator.WorldGenExecutionSimulator(modSourcesPath, modsPath, workshopPath);
                    simulator.SimulateWorldGen();
                }
                else
                {
                    // Use static analysis
                    var analyzer = new WorldGenSimulator.WorldGenConflictAnalyzer(pathTextBox.Text);
                    analyzer.Analyze();
                }

                Console.SetOut(originalOut);
                outputTextBox.AppendText(writer.ToString());
            }
            catch (Exception ex)
            {
                outputTextBox.AppendText($"Error: {ex.Message}\n{ex.StackTrace}\n");
            }
            finally
            {
                analyzeButton.Enabled = true;
                analyzeAllButton.Enabled = true;
            }
        }

        private void AnalyzeAllButton_Click(object sender, EventArgs e)
        {
            analyzeButton.Enabled = false;
            analyzeAllButton.Enabled = false;
            outputTextBox.Clear();
            outputTextBox.AppendText("Analyzing all mods...\n");
            outputTextBox.AppendText("=".PadRight(80, '=') + "\n\n");

            try
            {
                var originalOut = Console.Out;
                var writer = new StringWriter();
                Console.SetOut(writer);

                string[] args = executeCheckBox.Checked ? new[] { "--all", "--execute" } : new[] { "--all" };
                WorldGenSimulator.Program.Main(args);

                Console.SetOut(originalOut);
                outputTextBox.AppendText(writer.ToString());
            }
            catch (Exception ex)
            {
                outputTextBox.AppendText($"Error: {ex.Message}\n{ex.StackTrace}\n");
            }
            finally
            {
                analyzeButton.Enabled = true;
                analyzeAllButton.Enabled = true;
            }
        }

        [STAThread]
        static void Main(string[] args)
        {
            WinForms.Application.EnableVisualStyles();
            WinForms.Application.SetCompatibleTextRenderingDefault(false);

            // If command line args provided, run in console mode
            if (args.Length > 0)
            {
                WorldGenSimulator.Program.Main(args);
                return;
            }

            // Otherwise show GUI
            WinForms.Application.Run(new WorldGenSimulatorGUI());
        }
    }
}
