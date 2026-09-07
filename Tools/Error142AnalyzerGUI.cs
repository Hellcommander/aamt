using System;
using System.IO;
using System.Diagnostics;
using WinForms = System.Windows.Forms;

namespace Error142Analyzer
{
    /// <summary>
    /// GUI wrapper for Error142Analyzer with drag and drop support
    /// </summary>
    public class Error142AnalyzerGUI : WinForms.Form
    {
        private WinForms.TextBox pathTextBox;
        private WinForms.Button analyzeButton;
        private WinForms.Button browseButton;
        private WinForms.RichTextBox outputTextBox;
        private WinForms.Label dropLabel;
        private WinForms.Panel dropPanel;

        public Error142AnalyzerGUI()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text = "Error 142 Analyzer - Drag & Drop";
            this.Size = new System.Drawing.Size(800, 600);
            this.StartPosition = WinForms.FormStartPosition.CenterScreen;

            // Drop panel
            dropPanel = new WinForms.Panel
            {
                Dock = WinForms.DockStyle.Fill,
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
                Font = new System.Drawing.Font("Arial", 12, System.Drawing.FontStyle.Bold)
            };
            dropPanel.Controls.Add(dropLabel);

            // Path text box
            pathTextBox = new WinForms.TextBox
            {
                Dock = WinForms.DockStyle.Top,
                Height = 30,
                ReadOnly = true
            };

            // Buttons
            var buttonPanel = new WinForms.Panel
            {
                Dock = WinForms.DockStyle.Top,
                Height = 40
            };

            browseButton = new WinForms.Button
            {
                Text = "Browse...",
                Dock = WinForms.DockStyle.Left,
                Width = 100
            };
            browseButton.Click += BrowseButton_Click;

            analyzeButton = new WinForms.Button
            {
                Text = "Analyze",
                Dock = WinForms.DockStyle.Left,
                Width = 100,
                Enabled = false
            };
            analyzeButton.Click += AnalyzeButton_Click;

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
            else
            {
                e.Effect = WinForms.DragDropEffects.None;
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
                    if (Directory.Exists(path) || File.Exists(path))
                    {
                        // If it's a file, use its directory
                        if (File.Exists(path))
                        {
                            path = Path.GetDirectoryName(path);
                        }

                        pathTextBox.Text = path;
                        analyzeButton.Enabled = true;
                    }
                }
            }
        }

        private void BrowseButton_Click(object sender, EventArgs e)
        {
            using (var dialog = new WinForms.FolderBrowserDialog())
            {
                dialog.Description = "Select mod source folder";
                var result = dialog.ShowDialog();
                if (result == WinForms.DialogResult.OK)
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
                WinForms.MessageBox.Show("Please select a valid mod source folder.", "Invalid Path", WinForms.MessageBoxButtons.OK, WinForms.MessageBoxIcon.Warning);
                return;
            }

            analyzeButton.Enabled = false;
            outputTextBox.Clear();
            outputTextBox.AppendText($"Analyzing: {pathTextBox.Text}\n");
            outputTextBox.AppendText("=".PadRight(80, '=') + "\n\n");

            // Run the analyzer
            try
            {
                var analyzer = new Error142Analyzer(pathTextBox.Text);
                
                // Redirect console output
                var originalOut = Console.Out;
                var writer = new StringWriter();
                Console.SetOut(writer);

                analyzer.Analyze();

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
                var analyzer = new Error142Analyzer(args[0]);
                analyzer.Analyze();
                return;
            }

            // Otherwise show GUI
            WinForms.Application.Run(new Error142AnalyzerGUI());
        }
    }
}
