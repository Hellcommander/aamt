using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Terraria.ModLoader.Core;

namespace WorldGenSimulator
{
    /// <summary>
    /// Reads .tmod files (tModLoader mod archives) to extract source code and metadata
    /// Uses tModLoader's actual TmodFile class for proper reading
    /// </summary>
    public class TmodFileReader
    {
        /// <summary>
        /// Reads a .tmod file and extracts all available information using tModLoader's TmodFile
        /// </summary>
        public static TmodFileInfo ReadTmodFile(string tmodPath)
        {
            var info = new TmodFileInfo
            {
                FilePath = tmodPath,
                ModName = Path.GetFileNameWithoutExtension(tmodPath)
            };

            try
            {
                // TmodFile constructor is internal, use reflection to create instance
                var tmodFileType = typeof(TmodFile);
                var constructor = tmodFileType.GetConstructor(
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance,
                    null,
                    new[] { typeof(string), typeof(string), typeof(Version) },
                    null);
                
                if (constructor == null)
                {
                    info.ErrorMessage = "Could not access TmodFile constructor";
                    return info;
                }
                
                var tmodFile = (TmodFile)constructor.Invoke(new object?[] { tmodPath, null, null });
                using (var stream = tmodFile.Open())
                {
                    // Verify stream opened
                    if (stream == null)
                    {
                        info.ErrorMessage = "TmodFile.Open() returned null";
                        return info;
                    }
                    
                    // Get mod metadata
                    info.ModName = tmodFile.Name ?? info.ModName;
                    info.Version = tmodFile.Version?.ToString() ?? "";

                    // Get all file names using the proper tModLoader API
                    var fileNames = tmodFile.GetFileNames();
                    
                    if (fileNames == null)
                    {
                        info.ErrorMessage = "GetFileNames() returned null";
                        return info;
                    }
                    
                    if (fileNames.Count == 0)
                    {
                        info.ErrorMessage = "GetFileNames() returned empty list";
                        return info;
                    }

                    // Use tModLoader's convention: {ModName}.dll
                    string expectedDllName = $"{tmodFile.Name}.dll";
                    
                    if (fileNames.Contains(expectedDllName))
                    {
                        info.HasDll = true;
                        info.DllFileName = expectedDllName;
                    }
                    else
                    {
                        // Fallback: look for any .dll file
                        foreach (var fileName in fileNames)
                        {
                            var entryName = fileName.ToLowerInvariant();
                            
                            if (entryName.EndsWith(".dll"))
                            {
                                // Skip lib DLLs
                                if (entryName.StartsWith("lib/") || entryName.Contains("/lib/"))
                                    continue;
                                
                                // Skip framework DLLs
                                if (entryName.Contains("terraria.dll") || 
                                    entryName.Contains("tmodloader.dll") ||
                                    entryName.Contains("fna.dll") ||
                                    entryName.Contains("system.") ||
                                    entryName.Contains("microsoft."))
                                    continue;
                                
                                // Found a mod DLL
                                info.HasDll = true;
                                info.DllFileName = fileName;
                                break;
                            }
                        }
                    }
                    
                    // Extract the DLL if found
                    if (info.HasDll && !string.IsNullOrEmpty(info.DllFileName))
                    {
                        try
                        {
                            var bytes = tmodFile.GetBytes(info.DllFileName);
                            if (bytes != null && bytes.Length > 0)
                            {
                                var tempDllPath = Path.Combine(Path.GetTempPath(), $"tmod_{Guid.NewGuid():N}.dll");
                                File.WriteAllBytes(tempDllPath, bytes);
                                if (File.Exists(tempDllPath) && new FileInfo(tempDllPath).Length > 0)
                                {
                                    info.TempDllPath = tempDllPath;
                                }
                                else
                                {
                                    info.ErrorMessage = $"DLL file write failed ({tempDllPath})";
                                }
                            }
                            else
                            {
                                info.ErrorMessage = $"DLL bytes null/empty for {info.DllFileName}";
                            }
                        }
                        catch (Exception ex)
                        {
                            info.ErrorMessage = $"DLL extraction error: {ex.Message}";
                        }
                    }
                    else if (!info.HasDll && string.IsNullOrEmpty(info.ErrorMessage))
                    {
                        // For debugging: log what files ARE in the .tmod
                        var fileList = string.Join(", ", fileNames.Take(5));
                        info.ErrorMessage = $"No DLL in .tmod. {fileNames.Count} files found (first 5: {fileList})";
                    }
                    
                    // Continue processing other files
                    foreach (var fileName in fileNames)
                    {
                        var entryName = fileName.ToLowerInvariant();

                        // Check for PDB (debug symbols)
                        if (entryName.EndsWith(".pdb"))
                        {
                            info.HasPdb = true;
                        }

                        // Check for info file (contains mod metadata)
                        if (entryName == "info" || fileName.ToLowerInvariant() == "info")
                        {
                            try
                            {
                                var bytes = tmodFile.GetBytes(fileName);
                                if (bytes != null)
                                {
                                    info.InfoContent = Encoding.UTF8.GetString(bytes);
                                }
                            }
                            catch
                            {
                                // Ignore info file read errors
                            }
                        }

                        // Check for source files
                        if (entryName.EndsWith(".cs"))
                        {
                            info.HasSourceFiles = true;
                            info.SourceFileCount++;
                            
                            // Extract source file content
                            try
                            {
                                var bytes = tmodFile.GetBytes(fileName);
                                if (bytes != null)
                                {
                                    var content = Encoding.UTF8.GetString(bytes);
                                    info.SourceFiles.Add(new SourceFileInfo
                                    {
                                        Path = fileName,
                                        Content = content
                                    });
                                }
                            }
                            catch
                            {
                                // Ignore source file read errors
                            }
                        }
                    }

                    // Parse info file if available
                    if (!string.IsNullOrEmpty(info.InfoContent))
                    {
                        ParseInfoFile(info);
                    }
                }
            }
            catch (Exception ex)
            {
                info.ErrorMessage = $"TmodFileReader exception: {ex.GetType().Name}: {ex.Message}";
            }

            return info;
        }

        private static void ParseInfoFile(TmodFileInfo info)
        {
            // Info file format is typically key=value pairs
            var lines = info.InfoContent.Split('\n');
            foreach (var line in lines)
            {
                var trimmed = line.Trim();
                if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#"))
                    continue;

                var parts = trimmed.Split(new[] { '=' }, 2);
                if (parts.Length == 2)
                {
                    var key = parts[0].Trim().ToLowerInvariant();
                    var value = parts[1].Trim();

                    switch (key)
                    {
                        case "name":
                            info.ModName = value;
                            break;
                        case "version":
                            info.Version = value;
                            break;
                        case "author":
                            info.Author = value;
                            break;
                        case "modreferences":
                            info.ModReferences = value.Split(',').Select(r => r.Trim()).ToList();
                            break;
                        case "weakreferences":
                            info.WeakReferences = value.Split(',').Select(r => r.Trim()).ToList();
                            break;
                    }
                }
            }
        }

        /// <summary>
        /// Extracts all source files from .tmod to a directory using tModLoader's TmodFile
        /// </summary>
        public static string? ExtractSourceFiles(string tmodPath, string extractDir)
        {
            try
            {
                Directory.CreateDirectory(extractDir);

                // TmodFile constructor is internal, use reflection to create instance
                var tmodFileType = typeof(TmodFile);
                var constructor = tmodFileType.GetConstructor(
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance,
                    null,
                    new[] { typeof(string), typeof(string), typeof(Version) },
                    null);
                
                if (constructor == null)
                {
                    return null;
                }
                
                var tmodFile = (TmodFile)constructor.Invoke(new object?[] { tmodPath, null, null });
                using (tmodFile.Open())
                {
                    bool hasSource = false;
                    var fileNames = tmodFile.GetFileNames();

                    foreach (var fileName in fileNames)
                    {
                        if (fileName.EndsWith(".cs", StringComparison.OrdinalIgnoreCase))
                        {
                            hasSource = true;
                            var entryPath = Path.Combine(extractDir, fileName.Replace('/', Path.DirectorySeparatorChar));
                            var entryDir = Path.GetDirectoryName(entryPath);
                            if (!string.IsNullOrEmpty(entryDir))
                            {
                                Directory.CreateDirectory(entryDir);
                            }

                            var bytes = tmodFile.GetBytes(fileName);
                            if (bytes != null)
                            {
                                File.WriteAllBytes(entryPath, bytes);
                            }
                        }
                    }

                    return hasSource ? extractDir : null;
                }
            }
            catch
            {
                return null;
            }
        }
    }

    public class TmodFileInfo
    {
        public string FilePath { get; set; } = "";
        public string ModName { get; set; } = "";
        public string Version { get; set; } = "";
        public string Author { get; set; } = "";
        public bool HasDll { get; set; }
        public bool HasPdb { get; set; }
        public bool HasSourceFiles { get; set; }
        public int SourceFileCount { get; set; }
        public string DllFileName { get; set; } = "";
        public string? TempDllPath { get; set; }
        public string InfoContent { get; set; } = "";
        public List<string> ModReferences { get; set; } = new List<string>();
        public List<string> WeakReferences { get; set; } = new List<string>();
        public List<SourceFileInfo> SourceFiles { get; set; } = new List<SourceFileInfo>();
        public string? ErrorMessage { get; set; }
    }

    public class SourceFileInfo
    {
        public string Path { get; set; } = "";
        public string Content { get; set; } = "";
    }
}

