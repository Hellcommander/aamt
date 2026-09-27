namespace QudLab.Gui;

static class LlmModels
{
    public static readonly string[] Presets =
    {
        "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "Qwen/Qwen2.5-3B-Instruct",
        "Qwen/Qwen2.5-Coder-3B-Instruct",
        "Qwen/Qwen2.5-1.5B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
    };

    public static string SettingsPath =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "QudLab", "gui-llm.txt");

    public static string LoadLast()
    {
        try
        {
            var p = SettingsPath;
            if (File.Exists(p))
            {
                var t = File.ReadAllText(p).Trim();
                if (!string.IsNullOrWhiteSpace(t))
                    return t;
            }
        }
        catch { /* ignore */ }
        return Presets[0];
    }

    public static void SaveLast(string model)
    {
        try
        {
            var p = SettingsPath;
            Directory.CreateDirectory(Path.GetDirectoryName(p)!);
            File.WriteAllText(p, model.Trim());
        }
        catch { /* ignore */ }
    }

    public static IReadOnlyList<string> Catalog()
    {
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var p in Presets)
            set.Add(p);
        var last = LoadLast();
        if (!string.IsNullOrWhiteSpace(last))
            set.Add(last);
        foreach (var cached in ScanHuggingFaceCache())
            set.Add(cached);
        return set.OrderBy(s => s, StringComparer.OrdinalIgnoreCase).ToList();
    }

    public static IEnumerable<string> ScanHuggingFaceCache()
    {
        foreach (var hub in HubRoots())
        {
            string[] dirs;
            try { dirs = Directory.GetDirectories(hub, "models--*"); }
            catch { continue; }
            foreach (var dir in dirs)
            {
                var name = Path.GetFileName(dir);
                if (!name.StartsWith("models--", StringComparison.Ordinal))
                    continue;
                var id = name["models--".Length..].Replace("--", "/", StringComparison.Ordinal);
                if (string.IsNullOrWhiteSpace(id) || !id.Contains('/'))
                    continue;
                if (!LikelyChatModel(id))
                    continue;
                yield return id;
            }
        }
    }

    static bool LikelyChatModel(string id)
    {
        foreach (var p in Presets)
        {
            if (string.Equals(p, id, StringComparison.OrdinalIgnoreCase))
                return true;
        }
        var l = id.ToLowerInvariant();
        if (l.Contains("stable-diffusion") || l.Contains("stable-audio") || l.Contains("trellis")
            || l.Contains("clap") || l.Contains("lora") || l.Contains("sdxl") || l.Contains("controlnet"))
            return false;
        if (l.Contains("qwen") || l.Contains("llama") || l.Contains("mistral") || l.Contains("mixtral")
            || l.Contains("deepseek") || l.Contains("phi-") || l.Contains("gemma") || l.Contains("yi-")
            || l.Contains("codellama") || l.Contains("command-r"))
            return true;
        return l.Contains("instruct") || l.Contains("chat") || l.Contains("coder");
    }

    static IEnumerable<string> HubRoots()
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var candidate in new[]
                 {
                     Environment.GetEnvironmentVariable("HUGGINGFACE_HUB_CACHE"),
                     Environment.GetEnvironmentVariable("HF_HOME") is { } hf
                         ? Path.Combine(hf, "hub")
                         : null,
                     @"D:\hf-cache\hub",
                     @"D:\hf-cache",
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                         ".cache", "huggingface", "hub"),
                 })
        {
            if (string.IsNullOrWhiteSpace(candidate))
                continue;
            var path = candidate;
            if (!Directory.Exists(path))
                continue;
            if (!Path.GetFileName(path).Equals("hub", StringComparison.OrdinalIgnoreCase))
            {
                var nested = Path.Combine(path, "hub");
                if (Directory.Exists(nested))
                    path = nested;
            }
            var full = Path.GetFullPath(path);
            if (seen.Add(full))
                yield return full;
        }
    }
}
