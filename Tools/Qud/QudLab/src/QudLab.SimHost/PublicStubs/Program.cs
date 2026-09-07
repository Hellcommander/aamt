namespace QudLab.SimHost;

/// <summary>MIT stub when Program.cs from the private pack is absent.</summary>
static class Program
{
    static int Main(string[] args)
    {
        _ = args;
        Console.Error.WriteLine(
            "QudLab SimHost is part of the access-gated private pack.");
        Console.Error.WriteLine(
            "Unpack it with Tools/Qud/QudLab/Fetch-PrivatePack.ps1 (see LICENSE-PROPRIETARY.md).");
        return 2;
    }
}
