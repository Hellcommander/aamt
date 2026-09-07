using System;
using System.IO;
using System.Linq;
using System.Reflection;
using Terraria.ModLoader.Core;

class TestTmodFile
{
    static void Main(string[] args)
    {
        // Test a specific .tmod file
        string tmodPath = @"E:\SteamLibrary\steamapps\workshop\content\1281930\2562968836\2022.9\AdvancedWorldGen.tmod";
        
        if (!File.Exists(tmodPath))
        {
            Console.WriteLine($"File not found: {tmodPath}");
            return;
        }
        
        Console.WriteLine($"Testing: {tmodPath}");
        Console.WriteLine();
        
        try
        {
            var tmodFileType = typeof(TmodFile);
            var constructor = tmodFileType.GetConstructor(
                BindingFlags.NonPublic | BindingFlags.Instance,
                null,
                new[] { typeof(string), typeof(string), typeof(Version) },
                null);
            
            if (constructor == null)
            {
                Console.WriteLine("ERROR: Could not access TmodFile constructor");
                return;
            }
            
            var tmodFile = (TmodFile)constructor.Invoke(new object?[] { tmodPath, null, null });
            
            Console.WriteLine($"TmodFile created successfully");
            
            using (var stream = tmodFile.Open())
            {
                Console.WriteLine($"TmodFile.Open() succeeded");
                Console.WriteLine($"Stream: {stream}");
                Console.WriteLine();
                
                Console.WriteLine($"Mod Name: {tmodFile.Name}");
                Console.WriteLine($"Mod Version: {tmodFile.Version}");
                Console.WriteLine();
                
                var fileNames = tmodFile.GetFileNames();
                Console.WriteLine($"GetFileNames() returned: {fileNames?.Count ?? -1} files");
                
                if (fileNames != null && fileNames.Count > 0)
                {
                    Console.WriteLine();
                    Console.WriteLine("Files in .tmod:");
                    foreach (var file in fileNames.Take(20))
                    {
                        Console.WriteLine($"  - {file}");
                    }
                    if (fileNames.Count > 20)
                    {
                        Console.WriteLine($"  ... and {fileNames.Count - 20} more");
                    }
                    
                    // Look for DLL
                    var dllFiles = fileNames.Where(f => f.ToLowerInvariant().EndsWith(".dll")).ToList();
                    Console.WriteLine();
                    Console.WriteLine($"DLL files found: {dllFiles.Count}");
                    foreach (var dll in dllFiles)
                    {
                        Console.WriteLine($"  - {dll}");
                    }
                }
                else
                {
                    Console.WriteLine("No files found!");
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"ERROR: {ex.GetType().Name}: {ex.Message}");
            Console.WriteLine(ex.StackTrace);
        }
    }
}
