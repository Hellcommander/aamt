using System.Text.Json;
using XEdit.Clr;

namespace XEdit.Assist;

static class Program
{
    static int Main(string[] args)
    {
        try
        {
            if (args.Length == 0 || args[0] is "-h" or "--help" or "help")
            {
                Console.Error.WriteLine(Help);
                return 0;
            }

            var client = new XEditClient();
            var result = Dispatch(client, args);
            Console.WriteLine(result.ToJson());
            return result.Ok ? 0 : 1;
        }
        catch (Exception ex)
        {
            Console.WriteLine(new XEditResult { Ok = false, Error = ex.Message }.ToJson());
            return 1;
        }
    }

    static XEditResult Dispatch(XEditClient client, string[] args)
    {
        var cmd = args[0].ToLowerInvariant();
        var map = ParseFlags(args.Skip(1).ToArray());

        return cmd switch
        {
            "locate" => client.Locate(Game(map)),
            "fork" => client.ForkInfo(),
            "sync" => client.SyncFork(),
            "defs" => client.Defs(map.GetValueOrDefault("signature") ?? map.GetValueOrDefault("query") ?? Positional(args, 1)),
            "header" => client.Header(Need(map, args, "plugin", 1)),
            "groups" => client.Groups(Need(map, args, "plugin", 1)),
            "records" or "search" => client.Records(
                Need(map, args, "plugin", 1),
                map.GetValueOrDefault("signature"),
                map.GetValueOrDefault("query") ?? Positional(args, 2),
                Int(map, "limit", 200)),
            "job" => client.RunJob(XEditJob.Parse(File.ReadAllText(Need(map, args, "file", 1)))),
            "dump" or "get" or "set" or "apply" or "info" or "copy-override" or "add-record" or "create-plugin" or "check"
                => client.RunJob(JobFromFlags(cmd, map, args)),
            _ when cmd.EndsWith(".json", StringComparison.OrdinalIgnoreCase) =>
                client.RunJob(XEditJob.Parse(File.ReadAllText(cmd))),
            _ => XEditResult.Fail("Unknown command: " + cmd + ". See xedit-assist help.")
        };
    }

    static XEditJob JobFromFlags(string op, Dictionary<string, string> map, string[] args)
    {
        return new XEditJob
        {
            Op = op,
            Game = map.GetValueOrDefault("game") ?? "SF1",
            Plugin = map.GetValueOrDefault("plugin") ?? Positional(args, 1),
            TargetPlugin = map.GetValueOrDefault("target"),
            Signature = map.GetValueOrDefault("signature"),
            EditorId = map.GetValueOrDefault("edid"),
            FormId = map.GetValueOrDefault("formid"),
            Path = map.GetValueOrDefault("path"),
            Value = map.GetValueOrDefault("value"),
            Query = map.GetValueOrDefault("query"),
            Limit = Int(map, "limit", 100),
            MaxDepth = Int(map, "maxdepth", 8),
            Save = Flag(map, "save"),
            EditMasters = Flag(map, "edit-masters")
        };
    }

    static XEditGame Game(Dictionary<string, string> map) =>
        Enum.TryParse<XEditGame>(map.GetValueOrDefault("game") ?? "SF1", true, out var g) ? g : XEditGame.SF1;

    static Dictionary<string, string> ParseFlags(string[] args)
    {
        var d = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var i = 0; i < args.Length; i++)
        {
            var a = args[i];
            if (!a.StartsWith("--") && !a.StartsWith('-'))
                continue;
            var key = a.TrimStart('-');
            var val = "true";
            if (i + 1 < args.Length && !args[i + 1].StartsWith('-'))
            {
                val = args[++i];
            }
            d[key] = val;
        }
        return d;
    }

    static string? Positional(string[] args, int index) =>
        args.Skip(1).Where(a => !a.StartsWith('-')).ElementAtOrDefault(index - 1);

    static string Need(Dictionary<string, string> map, string[] args, string key, int pos)
    {
        var v = map.GetValueOrDefault(key) ?? Positional(args, pos);
        if (string.IsNullOrWhiteSpace(v))
            throw new ArgumentException($"Missing {key}");
        return v;
    }

    static int Int(Dictionary<string, string> map, string key, int fallback) =>
        map.TryGetValue(key, out var s) && int.TryParse(s, out var n) ? n : fallback;

    static bool Flag(Dictionary<string, string> map, string key) =>
        map.TryGetValue(key, out var s) && s is "true" or "1" or "yes";

    const string Help = """
xedit-assist — AI CLR around TES5Edit (github.com/TES5Edit/TES5Edit @ dev-4.1.6)

Fast (no xEdit process):
  locate                         Find SF1Edit/xEdit builds and warn if < 4.1.5q
  fork                           Show pinned TES5Edit source
  sync                           git pull origin dev-4.1.6
  defs [--signature ALCH]        Record catalog from wbDefinitionsSF1.pas
  header <plugin.esm>            TES4 header / masters / Small|Medium|Blueprint flags
  groups <plugin.esm>            Top-level GRUP signatures
  records <plugin.esm> [--signature WEAP] [--query laser]

Decoded / writes (launches xEdit):
  dump --plugin X.esm --edid Foo [--path FULL]
  get  --plugin X.esm --edid Foo --path EDID
  set  --plugin X.esm --edid Foo --path FULL --value "Name"
  copy-override --plugin Starfield.esm --edid Foo --target MyMod.esm
  add-record --plugin MyMod.esm --signature ALCH --edid MyPotion
  create-plugin --plugin MyMod.esm
  job job.json

Starfield: prefer a 4.1.5q+ build in Tools\XEdit\bin. The 4.1.5f copy next to
Starfield.exe cannot edit .esp or small/medium masters.
""";
}
