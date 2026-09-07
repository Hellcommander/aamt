using System;
using System.IO;
using WinForms = System.Windows.Forms;

namespace Error142Simulator
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
    /// GUI wrapper for Error142Simulator with drag and drop support
    /// </summary>
    public class Error142SimulatorGUI : WinForms.Form
    {
        private WinForms.TextBox modPathTextBox;
        private WinForms.TextBox tmlPathTextBox;
        private WinForms.Button analyzeButton;
        private WinForms.Button browseModButton;
        private WinForms.Button browseTmlButton;
        private WinForms.RichTextBox outputTextBox;
        private WinForms.Panel dropPanel;
        private WinForms.Label dropLabel;

        public Error142SimulatorGUI()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text = "Error 142 Simulator - Drag & Drop";
            this.Size = new System.Drawing.Size(900, 700);
            this.StartPosition = WinForms.FormStartPosition.CenterScreen;

            // Drop panel
            dropPanel = new WinForms.Panel
            {
                Dock = WinForms.DockStyle.Top,
                Height = 150,
                BorderStyle = WinForms.BorderStyle.FixedSingle,
                BackColor = System.Drawing.Color.LightGray,
                AllowDrop = true
            };
            dropPanel.DragEnter += DropPanel_DragEnter;
            dropPanel.DragDrop += DropPanel_DragDrop;
            dropPanel.DragOver += DropPanel_DragOver;

            dropLabel = new WinForms.Label
            {
                Text = "Drag and drop mod source folder here\nor use Browse buttons below",
                Dock = WinForms.DockStyle.Fill,
                TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
                Font = new System.Drawing.Font("Arial", 11, System.Drawing.FontStyle.Bold)
            };
            dropPanel.Controls.Add(dropLabel);

            // Path text boxes
            var pathPanel = new WinForms.Panel { Dock = WinForms.DockStyle.Top, Height = 100 };

            var modLabel = new WinForms.Label { Text = "Mod Source Path:", Dock = WinForms.DockStyle.Top, Height = 20 };
            modPathTextBox = new WinForms.TextBox { Dock = WinForms.DockStyle.Top, Height = 25, ReadOnly = true };

            var tmlLabel = new WinForms.Label { Text = "tModLoader Source Path:", Dock = WinForms.DockStyle.Top, Height = 20 };
            tmlPathTextBox = new WinForms.TextBox { Dock = WinForms.DockStyle.Top, Height = 25, ReadOnly = true };

            pathPanel.Controls.Add(tmlPathTextBox);
            pathPanel.Controls.Add(tmlLabel);
            pathPanel.Controls.Add(modPathTextBox);
            pathPanel.Controls.Add(modLabel);

            // Buttons
            var buttonPanel = new WinForms.Panel { Dock = WinForms.DockStyle.Top, Height = 40 };

            browseModButton = new WinForms.Button { Text = "Browse Mod...", Dock = WinForms.DockStyle.Left, Width = 120 };
            browseModButton.Click += BrowseModButton_Click;

            browseTmlButton = new WinForms.Button { Text = "Browse tModLoader...", Dock = WinForms.DockStyle.Left, Width = 150 };
            browseTmlButton.Click += BrowseTmlButton_Click;

            analyzeButton = new WinForms.Button { Text = "Simulate", Dock = WinForms.DockStyle.Left, Width = 100, Enabled = false };
            analyzeButton.Click += AnalyzeButton_Click;

            buttonPanel.Controls.Add(analyzeButton);
            buttonPanel.Controls.Add(browseTmlButton);
            buttonPanel.Controls.Add(browseModButton);

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
            mainPanel.Controls.Add(pathPanel);
            mainPanel.Controls.Add(dropPanel);

            this.Controls.Add(mainPanel);

            // Set default tModLoader path if it exists
            var defaultTmlPath = @"D:\User_Directories\Documents\My Games\Terraria\tModLoader-1.4.4";
            if (Directory.Exists(defaultTmlPath))
            {
                tmlPathTextBox.Text = defaultTmlPath;
            }
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
                        modPathTextBox.Text = path;
                        UpdateAnalyzeButton();
                    }
                    else if (File.Exists(path))
                    {
                        modPathTextBox.Text = Path.GetDirectoryName(path);
                        UpdateAnalyzeButton();
                    }
                }
            }
        }

        private void BrowseModButton_Click(object sender, EventArgs e)
        {
            using (var dialog = new WinForms.FolderBrowserDialog())
            {
                dialog.Description = "Select mod source folder";
                object dialogResult = dialog.ShowDialog();
                if (DialogResultHelper.IsOk(dialogResult))
                {
                    modPathTextBox.Text = dialog.SelectedPath;
                    UpdateAnalyzeButton();
                }
            }
        }

        private void BrowseTmlButton_Click(object sender, EventArgs e)
        {
            using (WinForms.FolderBrowserDialog dialog = new WinForms.FolderBrowserDialog())
            {
                dialog.Description = "Select tModLoader source folder";
                object dialogResult = dialog.ShowDialog();
                if (DialogResultHelper.IsOk(dialogResult))
                {
                    tmlPathTextBox.Text = dialog.SelectedPath;
                    UpdateAnalyzeButton();
                }
            }
        }

        private void UpdateAnalyzeButton()
        {
            analyzeButton.Enabled = !string.IsNullOrEmpty(modPathTextBox.Text) && 
                                   !string.IsNullOrEmpty(tmlPathTextBox.Text) &&
                                   Directory.Exists(modPathTextBox.Text) &&
                                   Directory.Exists(tmlPathTextBox.Text);
        }

        private void AnalyzeButton_Click(object sender, EventArgs e)
        {
            if (!Directory.Exists(modPathTextBox.Text) || !Directory.Exists(tmlPathTextBox.Text))
            {
                outputTextBox.AppendText("ERROR: Please select valid folders for both mod source and tModLoader source.\n");
                return;
            }

            analyzeButton.Enabled = false;
            outputTextBox.Clear();
            outputTextBox.AppendText($"Simulating mod loading...\n");
            outputTextBox.AppendText($"Mod: {modPathTextBox.Text}\n");
            outputTextBox.AppendText($"tModLoader: {tmlPathTextBox.Text}\n");
            outputTextBox.AppendText("=".PadRight(80, '=') + "\n\n");

            try
            {
                var simulator = new Error142Simulator(modPathTextBox.Text, tmlPathTextBox.Text);
                
                var originalOut = Console.Out;
                var writer = new StringWriter();
                Console.SetOut(writer);

                simulator.SimulateLoading();

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
            if (args.Length >= 2)
            {
                var simulator = new Error142Simulator(args[0], args[1]);
                simulator.SimulateLoading();
                return;
            }

            // Otherwise show GUI
            WinForms.Application.Run(new Error142SimulatorGUI());
        }
    }
}
