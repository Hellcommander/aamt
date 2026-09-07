using System.Globalization;
using System.Text.RegularExpressions;

namespace XEdit.Clr;

/// <summary>
/// xEdit versions are lettered (4.1.5f, 4.1.5q) then numeric (4.1.6).
/// Starfield .esp / small-medium masters require at least 4.1.5q (dev-4.1.6 tree).
/// </summary>
public readonly record struct XEditVersion(int Major, int Minor, int Patch, int Letter) : IComparable<XEditVersion>
{
    public static readonly XEditVersion MinStarfieldCurrent = Parse("4.1.5q");
    public static readonly XEditVersion Release415f = Parse("4.1.5f");

    public bool IsUnknown => Major == 0 && Minor == 0 && Patch == 0 && Letter == 0;

    public static XEditVersion Parse(string? text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return default;

        var m = Regex.Match(text.Trim(), @"(\d+)\.(\d+)\.(\d+)\s*([a-zA-Z])?");
        if (!m.Success)
            return default;

        var letter = 0;
        if (m.Groups[4].Success)
            letter = char.ToLowerInvariant(m.Groups[4].Value[0]) - 'a' + 1;

        return new XEditVersion(
            int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture),
            int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture),
            int.Parse(m.Groups[3].Value, CultureInfo.InvariantCulture),
            letter);
    }

    public int CompareTo(XEditVersion other)
    {
        var c = Major.CompareTo(other.Major);
        if (c != 0) return c;
        c = Minor.CompareTo(other.Minor);
        if (c != 0) return c;
        c = Patch.CompareTo(other.Patch);
        if (c != 0) return c;
        return Letter.CompareTo(other.Letter);
    }

    public static bool operator <(XEditVersion a, XEditVersion b) => a.CompareTo(b) < 0;
    public static bool operator >(XEditVersion a, XEditVersion b) => a.CompareTo(b) > 0;
    public static bool operator <=(XEditVersion a, XEditVersion b) => a.CompareTo(b) <= 0;
    public static bool operator >=(XEditVersion a, XEditVersion b) => a.CompareTo(b) >= 0;

    public override string ToString()
    {
        if (IsUnknown) return "unknown";
        var s = $"{Major}.{Minor}.{Patch}";
        if (Letter > 0)
            s += (char)('a' + Letter - 1);
        return s;
    }
}
