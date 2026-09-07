using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace ApiMigrator.Core;

/// <summary>
/// Converts legacy CP437 code points in mod source to UTF-16 glyphs, matching
/// <c>ConsoleLib.Console.CP437.FromCP437</c> (post UTF-16 internal-string change).
/// </summary>
public static class Cp437Converter
{
    public sealed class Options
    {
        public List<string> Paths { get; set; } = new();
        public string? ModFilter { get; set; }
        public bool Apply { get; set; }
        public bool Backup { get; set; } = true;
        /// <summary>
        /// When true, also convert ambiguous C# escapes <c>\t</c>/<c>\a</c>/<c>\b</c>/<c>\v</c>/<c>\f</c>
        /// inside strings (game maps these to ○/•/◘/♂/♀). Default skips them and reports for review.
        /// </summary>
        public bool ConvertAmbiguousEscapes { get; set; }
        /// <summary>
        /// Insert or upgrade root <c>Encoding="utf-8"</c> on every scanned XML file
        /// (needed so the game stops defaulting to CP437 / "Found CP437 Characters").
        /// </summary>
        public bool EnsureXmlUtf8Encoding { get; set; } = true;
        /// <summary>
        /// Obsolete alias: Encoding is always stamped when <see cref="EnsureXmlUtf8Encoding"/>
        /// is true (glyph conversion is no longer required). Kept so CLI/GUI flags still bind.
        /// </summary>
        public bool ForceXmlUtf8Encoding { get; set; }
        public List<string> ExcludeDirs { get; set; } = new()
        {
            "_tools", "bin", "obj", ".git", ".vs", "_decompile", "_decompile_il", "scratch",
            "Library", "PackageCache", "_reports", "node_modules",
        };
        public List<string> Extensions { get; set; } = new() { ".cs", ".xml" };
        public string? ReportPath { get; set; }
    }

    public sealed class Hit
    {
        public int Line { get; set; }
        public string Kind { get; set; } = "";
        public string From { get; set; } = "";
        public string To { get; set; } = "";
        public string Context { get; set; } = "";
        public bool AutoFixed { get; set; }
        public bool NeedsReview { get; set; }
    }

    public sealed class FileResult
    {
        public string FilePath { get; set; } = "";
        public bool Changed { get; set; }
        public List<Hit> Hits { get; set; } = new();
        public string? NewContent { get; set; }
        public int AutoFixCount => Hits.Count(h => h.AutoFixed);
        public int ReviewCount => Hits.Count(h => h.NeedsReview);
    }

    public sealed class Report
    {
        public bool Applied { get; set; }
        public DateTime GeneratedAt { get; set; } = DateTime.Now;
        public List<string> ScanRoots { get; set; } = new();
        public string? ModFilter { get; set; }
        public int FilesScanned { get; set; }
        public List<FileResult> FileResults { get; set; } = new();
        public List<string> Notes { get; set; } = new();
        public int TotalAutoFixes => FileResults.Sum(f => f.AutoFixCount);
        public int TotalReviewHits => FileResults.Sum(f => f.ReviewCount);

        public string ToMarkdown()
        {
            var sb = new StringBuilder();
            sb.AppendLine("# CP437 → UTF-16 conversion report");
            sb.AppendLine();
            sb.AppendLine($"Generated: {GeneratedAt:yyyy-MM-dd HH:mm:ss}");
            sb.AppendLine($"Mode: {(Applied ? "APPLY" : "DRY-RUN")}");
            sb.AppendLine($"Files scanned: **{FilesScanned}**");
            sb.AppendLine($"Files with hits: **{FileResults.Count}**");
            sb.AppendLine($"Auto-fixes: **{TotalAutoFixes}**");
            sb.AppendLine($"Needs review: **{TotalReviewHits}**");
            sb.AppendLine();
            sb.AppendLine("Scan roots:");
            foreach (var p in ScanRoots) sb.AppendLine($"- `{p}`");
            if (!string.IsNullOrEmpty(ModFilter))
                sb.AppendLine($"Mod filter: `{ModFilter}`");
            sb.AppendLine();
            sb.AppendLine("Uses `ConsoleLib.Console.CP437.CP437ToUTF16` (plus `\\u000d` → ♪).");
            sb.AppendLine("Prefer `XRL.Language.TextConstants` / `TextConstants.xml` for named symbols when editing by hand.");
            sb.AppendLine();
            if (Notes.Count > 0)
            {
                sb.AppendLine("## Notes");
                foreach (var n in Notes) sb.AppendLine("- " + n);
                sb.AppendLine();
            }

            foreach (var f in FileResults.OrderBy(x => x.FilePath, StringComparer.OrdinalIgnoreCase))
            {
                sb.AppendLine($"## `{f.FilePath}`");
                sb.AppendLine();
                sb.AppendLine($"Changed: {(f.Changed ? "yes" : "no")} · Auto-fixes: {f.AutoFixCount} · Review: {f.ReviewCount}");
                sb.AppendLine();
                sb.AppendLine("| Line | Kind | From | To | Auto | Review | Context |");
                sb.AppendLine("|---:|---|---|---|:---:|:---:|---|");
                foreach (var h in f.Hits)
                {
                    sb.Append('|').Append(h.Line).Append('|')
                        .Append(' ').Append(EscapeMd(h.Kind)).Append(" |")
                        .Append(' ').Append(EscapeMd(h.From)).Append(" |")
                        .Append(' ').Append(EscapeMd(h.To)).Append(" |")
                        .Append(h.AutoFixed ? " ✓ |" : " |")
                        .Append(h.NeedsReview ? " ! |" : " |")
                        .Append(' ').Append(EscapeMd(h.Context)).Append(" |")
                        .AppendLine();
                }
                sb.AppendLine();
            }

            return sb.ToString();
        }

        private static string EscapeMd(string s) =>
            (s ?? "").Replace("|", "\\|").Replace("\r", "\\r").Replace("\n", "\\n");
    }

    // Mirrors ConsoleLib.Console.CP437.CP437ToUTF16 (+ 0x0D → ♪ used by mods / wiki / TextConstants.NOTE_SINGLE).
    private static readonly Dictionary<char, char> Cp437ToUtf16 = BuildMap();

    private static readonly HashSet<char> AmbiguousControls = new()
    {
        '\a', '\b', '\t', '\v', '\f',
    };

    private static Dictionary<char, char> BuildMap()
    {
        var d = new Dictionary<char, char>
        {
            { '\0', ' ' },
            { '\u0001', '☺' },
            { '\u0002', '☻' },
            { '\u0003', '♥' },
            { '\u0004', '♦' },
            { '\u0005', '♣' },
            { '\u0006', '♠' },
            { '\a', '•' },
            { '\b', '◘' },
            { '\t', '○' },
            { '\v', '♂' },
            { '\f', '♀' },
            { '\r', '♪' }, // supplement: game table omits CR; mods use \u000d for note
            { '\u000e', '♫' },
            { '\u000f', '☼' },
            { '\u0010', '▶' },
            { '\u0011', '◀' },
            { '\u0012', '↕' },
            { '\u0013', '‼' },
            { '\u0014', '¶' },
            { '\u0015', '§' },
            { '\u0016', '▂' },
            { '\u0017', '↨' },
            { '\u0018', '↑' },
            { '\u0019', '↓' },
            { '\u001a', '→' },
            { '\u001b', '←' },
            { '\u001c', '∟' },
            { '\u001d', '↔' },
            { '\u001e', '▲' },
            { '\u001f', '▼' },
            { '\u007f', '⌂' },
            { '\u0080', 'Ç' },
            { '\u0081', 'ü' },
            { '\u0082', 'é' },
            { '\u0083', 'â' },
            { '\u0084', 'ä' },
            { '\u0085', 'à' },
            { '\u0086', 'å' },
            { '\u0087', 'ç' },
            { '\u0088', 'ê' },
            { '\u0089', 'ë' },
            { '\u008a', 'è' },
            { '\u008b', 'ï' },
            { '\u008c', 'î' },
            { '\u008d', 'ì' },
            { '\u008e', 'Ä' },
            { '\u008f', 'Å' },
            { '\u0090', 'É' },
            { '\u0091', 'æ' },
            { '\u0092', 'Æ' },
            { '\u0093', 'ô' },
            { '\u0094', 'ö' },
            { '\u0095', 'ò' },
            { '\u0096', 'û' },
            { '\u0097', 'ù' },
            { '\u0098', 'ÿ' },
            { '\u0099', 'Ö' },
            { '\u009a', 'Ü' },
            { '\u009b', '¢' },
            { '\u009c', '£' },
            { '\u009d', '¥' },
            { '\u009e', '₧' },
            { '\u009f', 'ƒ' },
            { '\u00a0', 'á' },
            { '¡', 'í' },
            { '¢', 'ó' },
            { '£', 'ú' },
            { '¤', 'ñ' },
            { '¥', 'Ñ' },
            { '¦', 'ª' },
            { '§', 'º' },
            { '\u00a8', '¿' },
            { '©', '⌐' },
            { 'ª', '¬' },
            { '«', '½' },
            { '¬', '¼' },
            { '\u00ad', '¡' },
            { '®', '«' },
            { '\u00af', '»' },
            { '°', '░' },
            { '±', '▒' },
            { '²', '▓' },
            { '³', '│' },
            { '\u00b4', '┤' },
            { 'µ', '╡' },
            { '¶', '╢' },
            { '·', '╖' },
            { '\u00b8', '╕' },
            { '¹', '╣' },
            { 'º', '║' },
            { '»', '╗' },
            { '¼', '╝' },
            { '½', '╜' },
            { '¾', '╛' },
            { '¿', '┐' },
            { 'À', '└' },
            { 'Á', '┴' },
            { 'Â', '┬' },
            { 'Ã', '├' },
            { 'Ä', '─' },
            { 'Å', '┼' },
            { 'Æ', '╞' },
            { 'Ç', '╟' },
            { 'È', '╚' },
            { 'É', '╔' },
            { 'Ê', '╩' },
            { 'Ë', '╦' },
            { 'Ì', '╠' },
            { 'Í', '═' },
            { 'Î', '╬' },
            { 'Ï', '╧' },
            { 'Ð', '╨' },
            { 'Ñ', '╤' },
            { 'Ò', '╥' },
            { 'Ó', '╙' },
            { 'Ô', '╘' },
            { 'Õ', '╒' },
            { 'Ö', '╓' },
            { '×', '╫' },
            { 'Ø', '╪' },
            { 'Ù', '┘' },
            { 'Ú', '┌' },
            { 'Û', '█' },
            { 'Ü', '▄' },
            { 'Ý', '▌' },
            { 'Þ', '▐' },
            { 'ß', '▀' },
            { 'à', 'α' },
            { 'á', 'ß' },
            { 'â', 'Γ' },
            { 'ã', 'π' },
            { 'ä', 'Σ' },
            { 'å', 'σ' },
            { 'æ', 'µ' },
            { 'ç', 'τ' },
            { 'è', 'Φ' },
            { 'é', 'Θ' },
            { 'ê', 'Ω' },
            { 'ë', 'δ' },
            { 'ì', '∞' },
            { 'í', 'φ' },
            { 'î', 'ε' },
            { 'ï', '∩' },
            { 'ð', '≡' },
            { 'ñ', '±' },
            { 'ò', '≥' },
            { 'ó', '≤' },
            { 'ô', '⌠' },
            { 'õ', '⌡' },
            { 'ö', '÷' },
            { '÷', '≈' },
            { 'ø', '°' },
            { 'ù', '∙' },
            { 'ú', '·' },
            { 'û', '✓' },
            { 'ü', 'ⁿ' },
            { 'ý', '²' },
            { 'þ', '■' },
            { 'ÿ', '\u00a0' },
            { '\u2007', '\u0001' },
            { '\ueea4', '¤' },
            { '\ueea6', '¦' },
            { '\ueea8', '\u00a8' },
            { '\ueea9', '©' },
            { '\ueead', '\u00ad' },
            { '\ueeae', '®' },
            { '\ueeaf', '\u00af' },
            { '\ueeb3', '³' },
            { '\ueeb4', '\u00b4' },
            { '\ueeb8', '\u00b8' },
            { '\ueeb9', '¹' },
            { '\ueebe', '¾' },
            { '\ueec0', 'À' },
            { '\ueec1', 'Á' },
            { '\ueec2', 'Â' },
            { '\ueec3', 'Ã' },
            { '\ueec8', 'È' },
            { '\ueeca', 'Ê' },
            { '\ueecb', 'Ë' },
            { '\ueecc', 'Ì' },
            { '\ueecd', 'Í' },
            { '\ueece', 'Î' },
            { '\ueecf', 'Ï' },
            { '\ueed0', 'Ð' },
            { '\ueed2', 'Ò' },
            { '\ueed3', 'Ó' },
            { '\ueed4', 'Ô' },
            { '\ueed5', 'Õ' },
            { '\ueed7', '×' },
            { '\ueed8', 'Ø' },
            { '\ueed9', 'Ù' },
            { '\ueeda', 'Ú' },
            { '\ueedb', 'Û' },
            { '\ueedd', 'Ý' },
            { '\ueede', 'Þ' },
            { '\ueee3', 'ã' },
            { '\ueef0', 'ð' },
            { '\ueef5', 'õ' },
            { '\ueef8', 'ø' },
            { '\ueefd', 'ý' },
            { '\ueefe', 'þ' },
        };
        return d;
    }

    public static bool TryFromCp437(char c, out char utf16) => Cp437ToUtf16.TryGetValue(c, out utf16);

    public static Report Run(Options options, Action<string>? onLog = null, Action<int, int>? onProgress = null)
    {
        var report = new Report
        {
            Applied = options.Apply,
            ScanRoots = options.Paths.ToList(),
            ModFilter = options.ModFilter,
        };

        var files = FileScanner.GetTargetFiles(options.Paths, options.ExcludeDirs, options.Extensions,
            options.ModFilter, msg => onLog?.Invoke("WARNING: " + msg));
        report.FilesScanned = files.Count;
        onLog?.Invoke($"Found {files.Count} candidate files (.cs / .xml).");

        for (var i = 0; i < files.Count; i++)
        {
            var file = files[i];
            onProgress?.Invoke(i + 1, files.Count);
            if (i == 0 || (i + 1) % 200 == 0 || i + 1 == files.Count)
                onLog?.Invoke($"Scanning {i + 1}/{files.Count}...");

            string original;
            try
            {
                original = File.ReadAllText(file);
            }
            catch (Exception ex)
            {
                onLog?.Invoke($"Could not read {file}: {ex.Message}");
                continue;
            }

            var ext = Path.GetExtension(file).ToLowerInvariant();
            var (working, hits) = ext switch
            {
                ".cs" => ConvertCs(original, options.ConvertAmbiguousEscapes),
                ".xml" => ConvertXml(original, options),
                _ => (original, new List<Hit>()),
            };

            if (hits.Count == 0 && working == original) continue;

            var changed = !string.Equals(working, original, StringComparison.Ordinal);
            var result = new FileResult
            {
                FilePath = file,
                Changed = changed,
                Hits = hits,
                NewContent = changed ? working : null,
            };
            report.FileResults.Add(result);

            if (changed && options.Apply)
            {
                try
                {
                    WorkshopWrite.ClearReadOnly(file);

                    if (options.Backup)
                    {
                        var bak = file + ".bak";
                        if (!File.Exists(bak))
                        {
                            try { File.Copy(file, bak); }
                            catch (UnauthorizedAccessException)
                            {
                                onLog?.Invoke($"WARNING: could not write backup {bak}; applying without .bak");
                            }
                        }
                    }
                    WorkshopWrite.WriteAllText(file, working);
                }
                catch (Exception ex)
                {
                    onLog?.Invoke($"ERROR writing {file}: {ex.Message}");
                    result.Changed = false;
                    result.NewContent = null;
                }
            }
        }

        if (!string.IsNullOrWhiteSpace(options.ReportPath))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(options.ReportPath))!);
            File.WriteAllText(options.ReportPath, report.ToMarkdown(), new UTF8Encoding(false));
            onLog?.Invoke("Report: " + options.ReportPath);
        }

        onLog?.Invoke($"Done. Auto-fixes={report.TotalAutoFixes} Review={report.TotalReviewHits} Files={report.FileResults.Count}");
        return report;
    }

    // -------------------- C# --------------------

    private static (string Text, List<Hit> Hits) ConvertCs(string source, bool convertAmbiguous)
    {
        var hits = new List<Hit>();
        var sb = new StringBuilder(source.Length);
        var i = 0;
        while (i < source.Length)
        {
            // Line comment
            if (i + 1 < source.Length && source[i] == '/' && source[i + 1] == '/')
            {
                var start = i;
                i += 2;
                while (i < source.Length && source[i] != '\n') i++;
                sb.Append(source, start, i - start);
                continue;
            }
            // Block comment
            if (i + 1 < source.Length && source[i] == '/' && source[i + 1] == '*')
            {
                var start = i;
                i += 2;
                while (i + 1 < source.Length && !(source[i] == '*' && source[i + 1] == '/')) i++;
                if (i + 1 < source.Length) i += 2;
                sb.Append(source, start, i - start);
                continue;
            }
            // Char literal
            if (source[i] == '\'')
            {
                var (chunk, chunkHits) = ConvertCsQuoted(source, ref i, '\'', convertAmbiguous, isChar: true);
                hits.AddRange(chunkHits);
                sb.Append(chunk);
                continue;
            }
            // String (regular / interpolated / verbatim)
            if (source[i] == '"' ||
                (source[i] == '@' && i + 1 < source.Length && source[i + 1] == '"') ||
                (source[i] == '$' && i + 1 < source.Length && (source[i + 1] == '"' || (source[i + 1] == '@' && i + 2 < source.Length && source[i + 2] == '"'))))
            {
                var (chunk, chunkHits) = ConvertCsString(source, ref i, convertAmbiguous);
                hits.AddRange(chunkHits);
                sb.Append(chunk);
                continue;
            }

            sb.Append(source[i]);
            i++;
        }

        return (sb.ToString(), hits);
    }

    private static (string Chunk, List<Hit> Hits) ConvertCsString(string source, ref int i, bool convertAmbiguous)
    {
        var hits = new List<Hit>();
        var start = i;
        var verbatim = false;
        var interpolated = false;

        if (source[i] == '$')
        {
            interpolated = true;
            i++;
        }
        if (i < source.Length && source[i] == '@')
        {
            verbatim = true;
            i++;
        }
        if (i >= source.Length || source[i] != '"')
        {
            // malformed; emit what we saw
            i = start + 1;
            return (source[start].ToString(), hits);
        }

        var prefixLen = i - start + 1; // include opening quote
        i++; // past opening "

        var body = new StringBuilder();
        var bodyStartIndex = i;

        if (verbatim)
        {
            while (i < source.Length)
            {
                if (source[i] == '"' && i + 1 < source.Length && source[i + 1] == '"')
                {
                    body.Append("\"\"");
                    i += 2;
                    continue;
                }
                if (source[i] == '"')
                {
                    i++; // closing
                    break;
                }
                if (interpolated && source[i] == '{')
                {
                    // keep holes intact; still convert raw CP437 chars outside holes
                    body.Append('{');
                    i++;
                    if (i < source.Length && source[i] == '{') { body.Append('{'); i++; continue; }
                    var depth = 1;
                    while (i < source.Length && depth > 0)
                    {
                        if (source[i] == '{') depth++;
                        else if (source[i] == '}') depth--;
                        body.Append(source[i]);
                        i++;
                    }
                    continue;
                }

                var ch = source[i];
                if (TryFromCp437(ch, out var utf) && ch != utf)
                {
                    // Skip converting real newlines inside verbatim strings
                    if (ch is '\n' or '\r')
                    {
                        body.Append(ch);
                        i++;
                        continue;
                    }
                    var line = LineAt(source, i);
                    hits.Add(new Hit
                    {
                        Line = line,
                        Kind = "cs-raw",
                        From = DescribeChar(ch),
                        To = DescribeChar(utf),
                        Context = Snippet(source, i),
                        AutoFixed = true,
                    });
                    body.Append(FormatCsChar(utf, forCharLiteral: false, preferEscape: false));
                    i++;
                    continue;
                }
                body.Append(ch);
                i++;
            }
        }
        else
        {
            while (i < source.Length)
            {
                if (source[i] == '\\')
                {
                    var (repl, hit) = ConvertCsEscape(source, ref i, convertAmbiguous, forCharLiteral: false);
                    if (hit != null) hits.Add(hit);
                    body.Append(repl);
                    continue;
                }
                if (source[i] == '"')
                {
                    i++;
                    break;
                }
                if (interpolated && source[i] == '{')
                {
                    body.Append('{');
                    i++;
                    if (i < source.Length && source[i] == '{') { body.Append('{'); i++; continue; }
                    var depth = 1;
                    while (i < source.Length && depth > 0)
                    {
                        if (source[i] == '{') depth++;
                        else if (source[i] == '}') depth--;
                        body.Append(source[i]);
                        i++;
                    }
                    continue;
                }

                var ch = source[i];
                if (TryFromCp437(ch, out var utf) && ch != utf && ch is not ('\n' or '\r'))
                {
                    hits.Add(new Hit
                    {
                        Line = LineAt(source, i),
                        Kind = "cs-raw",
                        From = DescribeChar(ch),
                        To = DescribeChar(utf),
                        Context = Snippet(source, i),
                        AutoFixed = true,
                    });
                    body.Append(FormatCsChar(utf, forCharLiteral: false, preferEscape: false));
                    i++;
                    continue;
                }
                body.Append(ch);
                i++;
            }
        }

        var prefix = source.Substring(start, prefixLen);
        _ = bodyStartIndex; // retained for clarity / future diagnostics
        return (prefix + body + "\"", hits);
    }

    private static (string Chunk, List<Hit> Hits) ConvertCsQuoted(string source, ref int i, char quote, bool convertAmbiguous, bool isChar)
    {
        var hits = new List<Hit>();
        var start = i;
        i++; // opening '
        var body = new StringBuilder();
        while (i < source.Length)
        {
            if (source[i] == '\\')
            {
                var (repl, hit) = ConvertCsEscape(source, ref i, convertAmbiguous, forCharLiteral: isChar);
                if (hit != null) hits.Add(hit);
                body.Append(repl);
                continue;
            }
            if (source[i] == quote)
            {
                i++;
                break;
            }
            var ch = source[i];
            if (TryFromCp437(ch, out var utf) && ch != utf)
            {
                hits.Add(new Hit
                {
                    Line = LineAt(source, i),
                    Kind = "cs-char-raw",
                    From = DescribeChar(ch),
                    To = DescribeChar(utf),
                    Context = Snippet(source, i),
                    AutoFixed = true,
                });
                body.Append(FormatCsChar(utf, forCharLiteral: true, preferEscape: false));
                i++;
                continue;
            }
            body.Append(ch);
            i++;
        }
        return (source[start] + body.ToString() + quote, hits);
    }

    private static (string Replacement, Hit? Hit) ConvertCsEscape(string source, ref int i, bool convertAmbiguous, bool forCharLiteral)
    {
        var escStart = i;
        i++; // backslash
        if (i >= source.Length)
            return ("\\", null);

        char c = source[i];
        // Named escapes that may be ambiguous CP437 glyphs
        if (c is 'a' or 'b' or 't' or 'v' or 'f')
        {
            var named = c switch { 'a' => '\a', 'b' => '\b', 't' => '\t', 'v' => '\v', _ => '\f' };
            i++;
            if (TryFromCp437(named, out var utf) && named != utf)
            {
                var hit = new Hit
                {
                    Line = LineAt(source, escStart),
                    Kind = "cs-named-escape",
                    From = "\\" + c,
                    To = DescribeChar(utf),
                    Context = Snippet(source, escStart),
                    AutoFixed = convertAmbiguous,
                    NeedsReview = !convertAmbiguous,
                };
                if (convertAmbiguous)
                    return (FormatCsChar(utf, forCharLiteral, preferEscape: false), hit);
                return ("\\" + c, hit);
            }
            return ("\\" + c, null);
        }

        if (c is 'x')
        {
            i++;
            var hex = ReadHex(source, ref i, 1, 2);
            if (hex.Length == 0) return ("\\x", null);
            var value = (char)int.Parse(hex, NumberStyles.HexNumber);
            if (TryFromCp437(value, out var utf) && value != utf)
            {
                var hit = new Hit
                {
                    Line = LineAt(source, escStart),
                    Kind = "cs-hex-escape",
                    From = "\\x" + hex,
                    To = DescribeChar(utf),
                    Context = Snippet(source, escStart),
                    AutoFixed = true,
                };
                return (FormatCsChar(utf, forCharLiteral, preferEscape: NeedsEscape(utf)), hit);
            }
            return ("\\x" + hex, null);
        }

        if (c is 'u')
        {
            i++;
            var hex = ReadHex(source, ref i, 4, 4);
            if (hex.Length != 4) return ("\\u" + hex, null);
            var value = (char)int.Parse(hex, NumberStyles.HexNumber);
            if (TryFromCp437(value, out var utf) && value != utf)
            {
                var hit = new Hit
                {
                    Line = LineAt(source, escStart),
                    Kind = "cs-unicode-escape",
                    From = "\\u" + hex,
                    To = DescribeChar(utf),
                    Context = Snippet(source, escStart),
                    AutoFixed = true,
                };
                return (FormatCsChar(utf, forCharLiteral, preferEscape: NeedsEscape(utf)), hit);
            }
            return ("\\u" + hex, null);
        }

        if (c is 'U')
        {
            i++;
            var hex = ReadHex(source, ref i, 8, 8);
            if (hex.Length != 8) return ("\\U" + hex, null);
            var code = int.Parse(hex, NumberStyles.HexNumber);
            if (code <= 0xFFFF)
            {
                var value = (char)code;
                if (TryFromCp437(value, out var utf) && value != utf)
                {
                    var hit = new Hit
                    {
                        Line = LineAt(source, escStart),
                        Kind = "cs-unicode-escape",
                        From = "\\U" + hex,
                        To = DescribeChar(utf),
                        Context = Snippet(source, escStart),
                        AutoFixed = true,
                    };
                    return (FormatCsChar(utf, forCharLiteral, preferEscape: NeedsEscape(utf)), hit);
                }
            }
            return ("\\U" + hex, null);
        }

        // Other escapes (\n \r \\ \" \' etc.) — leave alone
        i++;
        return ("\\" + c, null);
    }

    private static string ReadHex(string source, ref int i, int min, int max)
    {
        var start = i;
        var n = 0;
        while (i < source.Length && n < max && Uri.IsHexDigit(source[i]))
        {
            i++;
            n++;
        }
        if (n < min)
        {
            i = start;
            return "";
        }
        return source.Substring(start, n);
    }

    private static bool NeedsEscape(char c) =>
        char.IsControl(c) || c is '"' or '\'' or '\\' || c == '\u00a0';

    private static string FormatCsChar(char c, bool forCharLiteral, bool preferEscape)
    {
        if (preferEscape || NeedsEscape(c) || (forCharLiteral && c is '\'' or '\\'))
            return "\\u" + ((int)c).ToString("x4");
        return c.ToString();
    }

    // -------------------- XML --------------------

    private static readonly Regex XmlEntityRx = new(
        @"&#x([0-9A-Fa-f]{1,6});|&#([0-9]{1,7});",
        RegexOptions.Compiled);

    private static (string Text, List<Hit> Hits) ConvertXml(string source, Options options)
    {
        var hits = new List<Hit>();
        var sb = new StringBuilder(source.Length);
        var i = 0;

        while (i < source.Length)
        {
            // Comments — leave as-is
            if (i + 3 < source.Length && source.AsSpan(i).StartsWith("<!--"))
            {
                var end = source.IndexOf("-->", i + 4, StringComparison.Ordinal);
                if (end < 0) { sb.Append(source, i, source.Length - i); i = source.Length; break; }
                end += 3;
                sb.Append(source, i, end - i);
                i = end;
                continue;
            }
            // CDATA
            if (i + 8 < source.Length && source.AsSpan(i).StartsWith("<![CDATA["))
            {
                var end = source.IndexOf("]]>", i + 9, StringComparison.Ordinal);
                if (end < 0) { sb.Append(source, i, source.Length - i); i = source.Length; break; }
                var cdataInnerStart = i + 9;
                var inner = source.Substring(cdataInnerStart, end - cdataInnerStart);
                var (newInner, innerHits) = ConvertXmlTextRun(inner, cdataInnerStart, source);
                hits.AddRange(innerHits);
                sb.Append("<![CDATA[").Append(newInner).Append("]]>");
                i = end + 3;
                continue;
            }

            if (source[i] == '&')
            {
                var m = XmlEntityRx.Match(source, i);
                if (m.Success && m.Index == i)
                {
                    char? value = null;
                    if (m.Groups[1].Success)
                        value = (char)int.Parse(m.Groups[1].Value, NumberStyles.HexNumber);
                    else if (m.Groups[2].Success)
                    {
                        var n = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
                        if (n >= 0 && n <= 0xFFFF) value = (char)n;
                    }

                    if (value is { } v && TryFromCp437(v, out var utf) && v != utf)
                    {
                        hits.Add(new Hit
                        {
                            Line = LineAt(source, i),
                            Kind = "xml-entity",
                            From = m.Value,
                            To = DescribeChar(utf),
                            Context = Snippet(source, i),
                            AutoFixed = true,
                        });
                        sb.Append(FormatXmlChar(utf));
                        i += m.Length;
                        continue;
                    }

                    sb.Append(m.Value);
                    i += m.Length;
                    continue;
                }

                // Lone '&' (not a numeric entity) — copy and advance or the text-run loop never moves.
                sb.Append('&');
                i++;
                continue;
            }

            // Inside tags: still convert attribute values' raw CP437 + entities (entities handled above)
            if (source[i] == '<')
            {
                var tagEnd = source.IndexOf('>', i + 1);
                if (tagEnd < 0) { sb.Append(source, i, source.Length - i); break; }
                var tag = source.Substring(i, tagEnd - i + 1);
                var (newTag, tagHits) = ConvertXmlTag(tag, i, source);
                hits.AddRange(tagHits);
                sb.Append(newTag);
                i = tagEnd + 1;
                continue;
            }

            // Text node run until next < or &
            var runStart = i;
            while (i < source.Length && source[i] is not ('<' or '&')) i++;
            var run = source.Substring(runStart, i - runStart);
            var (newRun, runHits) = ConvertXmlTextRun(run, runStart, source);
            hits.AddRange(runHits);
            sb.Append(newRun);
        }

        var text = sb.ToString();
        // Always stamp Encoding when enabled — most "Found CP437 Characters" / defaulting
        // warnings are clean UTF-8 files missing the root attribute (no glyphs to convert).
        if (options.EnsureXmlUtf8Encoding)
        {
            var (withEnc, encChanged, encFrom) = XmlUtf8EncodingFixer.TryEnsure(text);
            if (encChanged)
            {
                hits.Add(new Hit
                {
                    Line = 1,
                    Kind = "xml-encoding",
                    From = encFrom ?? "(missing)",
                    To = "Encoding=\"utf-8\"",
                    Context = Snippet(withEnc, 0),
                    AutoFixed = true,
                });
                text = withEnc;
            }
        }

        return (text, hits);
    }

    private static (string Text, List<Hit> Hits) ConvertXmlTag(string tag, int absoluteStart, string fullSource)
    {
        var hits = new List<Hit>();
        var sb = new StringBuilder(tag.Length);
        var i = 0;
        while (i < tag.Length)
        {
            if (tag[i] is '"' or '\'')
            {
                var q = tag[i];
                sb.Append(q);
                i++;
                while (i < tag.Length && tag[i] != q)
                {
                    if (tag[i] == '&')
                    {
                        var m = XmlEntityRx.Match(tag, i);
                        if (m.Success && m.Index == i)
                        {
                            char? value = null;
                            if (m.Groups[1].Success)
                                value = (char)int.Parse(m.Groups[1].Value, NumberStyles.HexNumber);
                            else if (m.Groups[2].Success)
                            {
                                var n = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
                                if (n >= 0 && n <= 0xFFFF) value = (char)n;
                            }
                            if (value is { } v && TryFromCp437(v, out var utf) && v != utf)
                            {
                                hits.Add(new Hit
                                {
                                    Line = LineAt(fullSource, absoluteStart + i),
                                    Kind = "xml-attr-entity",
                                    From = m.Value,
                                    To = DescribeChar(utf),
                                    Context = Snippet(fullSource, absoluteStart + i),
                                    AutoFixed = true,
                                });
                                sb.Append(FormatXmlChar(utf));
                                i += m.Length;
                                continue;
                            }
                            sb.Append(m.Value);
                            i += m.Length;
                            continue;
                        }
                        sb.Append('&');
                        i++;
                        continue;
                    }

                    var ch = tag[i];
                    if (TryFromCp437(ch, out var u) && ch != u && ch is not ('\n' or '\r' or '\t'))
                    {
                        hits.Add(new Hit
                        {
                            Line = LineAt(fullSource, absoluteStart + i),
                            Kind = "xml-attr-raw",
                            From = DescribeChar(ch),
                            To = DescribeChar(u),
                            Context = Snippet(fullSource, absoluteStart + i),
                            AutoFixed = true,
                        });
                        sb.Append(FormatXmlChar(u));
                        i++;
                        continue;
                    }
                    sb.Append(ch);
                    i++;
                }
                if (i < tag.Length) { sb.Append(tag[i]); i++; }
                continue;
            }
            sb.Append(tag[i]);
            i++;
        }
        return (sb.ToString(), hits);
    }

    private static (string Text, List<Hit> Hits) ConvertXmlTextRun(string run, int absoluteStart, string fullSource)
    {
        var hits = new List<Hit>();
        var sb = new StringBuilder(run.Length);
        for (var i = 0; i < run.Length; i++)
        {
            var ch = run[i];
            if (TryFromCp437(ch, out var utf) && ch != utf && ch is not ('\n' or '\r' or '\t'))
            {
                hits.Add(new Hit
                {
                    Line = LineAt(fullSource, absoluteStart + i),
                    Kind = "xml-text",
                    From = DescribeChar(ch),
                    To = DescribeChar(utf),
                    Context = Snippet(fullSource, absoluteStart + i),
                    AutoFixed = true,
                });
                sb.Append(FormatXmlChar(utf));
            }
            else sb.Append(ch);
        }
        return (sb.ToString(), hits);
    }

    private static string FormatXmlChar(char c)
    {
        if (c is '<' or '>' or '&' or '"' or '\'')
            return $"&#x{(int)c:X};";
        if (char.IsControl(c) && c is not ('\t' or '\n' or '\r'))
            return $"&#x{(int)c:X};";
        return c.ToString();
    }

    // -------------------- helpers --------------------

    private static int LineAt(string text, int index)
    {
        var line = 1;
        var n = Math.Min(index, text.Length);
        for (var i = 0; i < n; i++)
            if (text[i] == '\n') line++;
        return line;
    }

    private static string Snippet(string text, int index, int radius = 36)
    {
        var start = Math.Max(0, index - radius);
        var end = Math.Min(text.Length, index + radius);
        var s = text[start..end].Replace("\r", "\\r").Replace("\n", "\\n");
        return s;
    }

    private static string DescribeChar(char c)
    {
        if (c is >= ' ' and <= '~' && c is not ('\\' or '\'' or '"'))
            return $"'{c}' (U+{(int)c:X4})";
        return $"U+{(int)c:X4} '{c}'";
    }
}
