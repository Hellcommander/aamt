using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Safety net between "a rule produced new text" and "the file on disk is replaced".
///
/// Added 2026-11-12 after a real run over local mods showed three kinds of harm that the per-rule tests had
/// not caught: message text silently changed (a <c>?</c> deleted inside string literals, which still
/// compiled), code that no longer compiled (<c>Version?</c> on the game's struct stripped to
/// <c>Version</c>; <c>…ToString()Single</c>), and a float turned into text (<c>px[i].a</c>).
/// Each cause is fixed in its rule; this class is there for the next one nobody has seen yet.
///
/// Two independent checks:
/// <list type="bullet">
/// <item><see cref="CheckRewrite"/>: no compiler needed, per file. A rewrite must keep brackets balanced
/// and must keep every piece of string-literal text the file had. Rules move text into templates and add
/// tokens around it; none of them has a reason to drop or alter the words themselves.</item>
/// <item><see cref="CompileGuard"/>: per mod. The mod is compiled before the first write and again after
/// the last; if the second compile has an error the first did not, every file written to that mod is put
/// back.</item>
/// </list>
/// </summary>
public static class ApplyGuard
{
    /// <summary>Text pieces shorter than this many letters or digits are not tracked (" ", "!", "the").</summary>
    public const int MinTrackedLetters = 4;

    /// <summary>
    /// Reasons the rewrite must not be written; empty when it passes. <paramref name="original"/> and
    /// <paramref name="rewritten"/> are whole C# files. <paramref name="movedTo"/> holds other files written
    /// in the same run (XML sidecars): a rule that moves a string out of the C# file and into one of those
    /// has not dropped it.
    /// </summary>
    public static List<string> CheckRewrite(string original, string rewritten, IEnumerable<string>? movedTo = null)
    {
        var reasons = new List<string>();
        if (ReferenceEquals(original, rewritten) || original == rewritten)
            return reasons;

        var before = Scan(original);
        var after = Scan(rewritten);

        for (var i = 0; i < 3; i++)
        {
            if (before.Depth[i] == 0 && after.Depth[i] != 0)
                reasons.Add($"brackets {"({["[i]}{")}]"[i]} no longer balance after the rewrite ({after.Depth[i]:+0;-0})");
        }

        var lost = 0;
        foreach (var piece in before.Text)
        {
            if (piece.Count(char.IsLetterOrDigit) < MinTrackedLetters) continue;
            if (rewritten.Contains(piece, StringComparison.Ordinal)) continue;
            if (movedTo != null && movedTo.Any(other => other.Contains(piece, StringComparison.Ordinal))) continue;
            if (lost++ < 3)
                reasons.Add("string text changed or dropped: \"" + (piece.Length > 80 ? piece[..80] + "…" : piece) + "\"");
        }
        if (lost > 3)
            reasons.Add($"…and {lost - 3} more changed string(s)");
        return reasons;
    }

    internal sealed class ScanResult
    {
        /// <summary>Raw source text of every string literal, interpolated strings split at their holes.</summary>
        public List<string> Text { get; } = new();
        /// <summary>Open minus close for (), {} and [] in code (outside strings, chars and comments).</summary>
        public int[] Depth { get; } = new int[3];
    }

    /// <summary>
    /// A small C# lexer: enough to tell code from comments, char literals and the string forms mods use
    /// (regular, verbatim, interpolated, raw). It does not need to be a parser; it only has to agree with
    /// itself on the original and the rewritten file.
    /// </summary>
    internal static ScanResult Scan(string s)
    {
        var r = new ScanResult();
        var n = s.Length;
        var i = 0;
        while (i < n)
        {
            var c = s[i];
            if (c == '/' && i + 1 < n && s[i + 1] == '/')
            {
                while (i < n && s[i] != '\n') i++;
                continue;
            }
            if (c == '/' && i + 1 < n && s[i + 1] == '*')
            {
                var end = s.IndexOf("*/", i + 2, StringComparison.Ordinal);
                i = end < 0 ? n : end + 2;
                continue;
            }
            if (c == '\'')
            {
                // 'x', '\n', 'A': skip to the closing quote, never far.
                var j = i + 1;
                if (j < n && s[j] == '\\') j += 2; else j++;
                while (j < n && j < i + 10 && s[j] != '\'') j++;
                i = j < n && s[j] == '\'' ? j + 1 : i + 1;
                continue;
            }
            if (c == '"' || ((c == '$' || c == '@') && IsStringPrefix(s, i)))
            {
                var start = i;
                var verbatim = false;
                var interpolated = false;
                while (i < n && (s[i] == '$' || s[i] == '@'))
                {
                    if (s[i] == '@') verbatim = true; else interpolated = true;
                    i++;
                }
                // Raw string: three or more quotes open it and the same run closes it.
                var quotes = 0;
                while (i + quotes < n && s[i + quotes] == '"') quotes++;
                string content;
                if (quotes >= 3)
                {
                    var fence = new string('"', quotes);
                    var bodyStart = i + quotes;
                    var end = s.IndexOf(fence, bodyStart, StringComparison.Ordinal);
                    if (end < 0) end = n;
                    content = s[bodyStart..end];
                    i = Math.Min(n, end + quotes);
                }
                else
                {
                    var bodyStart = ++i;
                    while (i < n)
                    {
                        if (verbatim)
                        {
                            if (s[i] == '"')
                            {
                                if (i + 1 < n && s[i + 1] == '"') { i += 2; continue; }
                                break;
                            }
                            i++;
                        }
                        else
                        {
                            if (s[i] == '\\') { i += 2; continue; }
                            if (s[i] == '"' || s[i] == '\n') break;
                            i++;
                        }
                    }
                    i = Math.Min(i, n);
                    content = s[bodyStart..i];
                    if (i < n && s[i] == '"') i++;
                }
                if (i <= start) i = start + 1;
                if (interpolated) AddOutsideHoles(content, r.Text);
                else r.Text.Add(content);
                continue;
            }

            switch (c)
            {
                case '(': r.Depth[0]++; break;
                case ')': r.Depth[0]--; break;
                case '{': r.Depth[1]++; break;
                case '}': r.Depth[1]--; break;
                case '[': r.Depth[2]++; break;
                case ']': r.Depth[2]--; break;
            }
            i++;
        }
        return r;
    }

    /// <summary>True when the run of $ and @ at <paramref name="i"/> ends in a quote (not @identifier).</summary>
    static bool IsStringPrefix(string s, int i)
    {
        while (i < s.Length && (s[i] == '$' || s[i] == '@')) i++;
        return i < s.Length && s[i] == '"';
    }

    /// <summary>The literal text of an interpolated string: everything outside its {holes}.</summary>
    static void AddOutsideHoles(string content, List<string> pieces)
    {
        var sb = new System.Text.StringBuilder();
        var depth = 0;
        for (var i = 0; i < content.Length; i++)
        {
            var c = content[i];
            if (depth == 0 && c == '{' && i + 1 < content.Length && content[i + 1] == '{') { sb.Append("{{"); i++; continue; }
            if (depth == 0 && c == '}' && i + 1 < content.Length && content[i + 1] == '}') { sb.Append("}}"); i++; continue; }
            if (c == '{')
            {
                if (depth == 0 && sb.Length > 0) { pieces.Add(sb.ToString()); sb.Clear(); }
                depth++;
                continue;
            }
            if (c == '}' && depth > 0) { depth--; continue; }
            if (depth == 0) sb.Append(c);
        }
        if (sb.Length > 0) pieces.Add(sb.ToString());
    }
}

/// <summary>
/// Compiles a mod before the first write and after the last, and restores every written file when the
/// second compile has an error the first did not. One instance per apply run; mods are found by walking up
/// from each file to the folder that holds <c>manifest.json</c>.
/// </summary>
public sealed class CompileGuard
{
    sealed class ModState
    {
        public Dictionary<string, int>? Baseline;
        public readonly Dictionary<string, string> Originals = new(StringComparer.OrdinalIgnoreCase);
    }

    public sealed class Outcome
    {
        public string ModFolder { get; init; } = "";
        public bool Reverted { get; init; }
        public List<string> RevertedFiles { get; init; } = new();
        public List<string> NewErrors { get; init; } = new();
        public string? Note { get; init; }
    }

    static readonly Regex ErrorLine = new(
        @"(?<file>[^\\/\r\n(]+\.cs)\(\d+,\d+\):\s*error\s+(?<code>[A-Z]+\d+):\s*(?<msg>[^\r\n\[]*)",
        RegexOptions.Compiled);

    readonly string _managedDir;
    readonly Action<string>? _log;
    readonly Dictionary<string, ModState> _mods = new(StringComparer.OrdinalIgnoreCase);

    public CompileGuard(string managedDir, Action<string>? log = null)
    {
        _managedDir = managedDir;
        _log = log;
    }

    /// <summary>The mod folder a file belongs to: the nearest ancestor with a manifest.json, else null.</summary>
    public static string? ModRootOf(string file)
    {
        var dir = Path.GetDirectoryName(Path.GetFullPath(file));
        while (!string.IsNullOrEmpty(dir))
        {
            if (File.Exists(Path.Combine(dir, "manifest.json"))) return dir;
            dir = Path.GetDirectoryName(dir);
        }
        return null;
    }

    /// <summary>
    /// Call right before a .cs file is overwritten, with the content it has now. The first call for a mod
    /// compiles that mod as it stands. Returns false when the write must not happen (no compile possible).
    /// </summary>
    public bool BeforeWrite(string file, string original)
    {
        var root = ModRootOf(file);
        if (root is null) return true; // not inside a mod folder: nothing to compile as a unit
        if (!_mods.TryGetValue(root, out var state))
        {
            state = new ModState();
            _mods[root] = state;
            _log?.Invoke($"Compile guard: compiling {Path.GetFileName(root)} before any change...");
            state.Baseline = Errors(root);
            if (state.Baseline is null)
                _log?.Invoke($"Compile guard: could not compile {Path.GetFileName(root)}; its files are left untouched.");
        }
        if (state.Baseline is null) return false;
        var full = Path.GetFullPath(file);
        if (!state.Originals.ContainsKey(full))
            state.Originals[full] = original;
        return true;
    }

    /// <summary>Compiles every mod that was written to and puts the originals back where new errors appeared.</summary>
    public List<Outcome> Finish()
    {
        var outcomes = new List<Outcome>();
        foreach (var (root, state) in _mods)
        {
            if (state.Baseline is null || state.Originals.Count == 0) continue;
            var after = Errors(root);
            var fresh = after is null ? new List<string> { "the mod could not be compiled after the change" } : NewErrors(state.Baseline, after);
            if (fresh.Count == 0)
            {
                outcomes.Add(new Outcome { ModFolder = root });
                continue;
            }
            var reverted = new List<string>();
            foreach (var (file, original) in state.Originals)
            {
                try
                {
                    WorkshopWrite.WriteAllText(file, original);
                    reverted.Add(file);
                }
                catch (Exception ex)
                {
                    _log?.Invoke($"Compile guard: ERROR restoring {file}: {ex.Message}");
                }
            }
            _log?.Invoke($"Compile guard: {Path.GetFileName(root)} had {fresh.Count} new compile error(s) after the rewrite; restored {reverted.Count} file(s).");
            foreach (var e in fresh.Take(5)) _log?.Invoke("    " + e);
            outcomes.Add(new Outcome { ModFolder = root, Reverted = true, RevertedFiles = reverted, NewErrors = fresh });
        }
        return outcomes;
    }

    /// <summary>Compile errors of a mod as "File.cs CSxxxx: message" → count; null when the compiler did not run.</summary>
    Dictionary<string, int>? Errors(string modFolder)
    {
        ModCompiler.CompileResult result;
        try
        {
            result = ModCompiler.CompileAgainstManaged(modFolder, _managedDir, null, null, OtherModAssemblies(modFolder));
        }
        catch (Exception ex)
        {
            _log?.Invoke("Compile guard: " + ex.Message);
            return null;
        }
        if (result.ExitCode == -1 || string.IsNullOrWhiteSpace(result.Output))
            return null;
        var errors = new Dictionary<string, int>(StringComparer.Ordinal);
        // MSBuild prints each diagnostic twice (as it happens and in the summary); the doubling is the same
        // before and after, so the counts still compare.
        foreach (Match m in ErrorLine.Matches(result.Output))
        {
            var key = m.Groups["file"].Value + " " + m.Groups["code"].Value + ": " + m.Groups["msg"].Value.Trim();
            errors[key] = errors.TryGetValue(key, out var count) ? count + 1 : 1;
        }
        // A failed build with no parsable error line (bad project, missing SDK) tells us nothing.
        if (result.ExitCode != 0 && errors.Count == 0)
            return null;
        return errors;
    }

    static List<string> NewErrors(Dictionary<string, int> before, Dictionary<string, int> after)
    {
        var fresh = new List<string>();
        foreach (var (key, count) in after)
        {
            before.TryGetValue(key, out var had);
            if (count > had) fresh.Add(key);
        }
        return fresh;
    }

    /// <summary>Other mods' compiled assemblies (from the last game boot), so a mod with dependencies compiles.</summary>
    public static IEnumerable<string> OtherModAssemblies(string modFolder)
    {
        var dir = Path.Combine(CoqPaths.LocalLowCoqRoot, "ModAssemblies");
        if (!Directory.Exists(dir)) return Array.Empty<string>();
        // Not the mod's own assembly from the last boot: its types would shadow nothing, but they add a
        // duplicate-type warning for every class.
        string? ownId = null;
        try
        {
            var m = Regex.Match(File.ReadAllText(Path.Combine(modFolder, "manifest.json")), @"""id""\s*:\s*""([^""]+)""", RegexOptions.IgnoreCase);
            if (m.Success) ownId = m.Groups[1].Value;
        }
        catch
        {
            // no manifest: reference everything
        }
        return Directory.EnumerateFiles(dir, "*.dll")
            .Where(f => ownId is null || !Path.GetFileNameWithoutExtension(f).Equals(ownId, StringComparison.OrdinalIgnoreCase))
            .ToList();
    }
}
